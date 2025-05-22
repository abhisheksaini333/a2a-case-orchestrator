"""PostgreSQL state, transactional approval and outbox delivery."""
import json
import uuid
import psycopg2
from psycopg2.extras import Json, RealDictCursor
from .domain import DomainError, case_input, digest, authorize_approval

class Store:
    def __init__(self, url):
        self.url = url
    def connection(self):
        return psycopg2.connect(self.url, connect_timeout=5)

    def migrate(self):
        with self.connection() as c, c.cursor() as q:
            q.execute("""
            CREATE TABLE IF NOT EXISTS cases (
              id text PRIMARY KEY, creator text NOT NULL, request_key text UNIQUE NOT NULL,
              input jsonb NOT NULL, input_digest text NOT NULL, state text NOT NULL DEFAULT 'submitted',
              revision integer NOT NULL DEFAULT 1, proposal jsonb, proposal_digest text,
              approved_by text, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now());
            CREATE TABLE IF NOT EXISTS events (
              id bigserial PRIMARY KEY, case_id text NOT NULL REFERENCES cases(id), actor text NOT NULL,
              kind text NOT NULL, detail jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now());
            CREATE TABLE IF NOT EXISTS agent_tasks (
              id text PRIMARY KEY, agent text NOT NULL, owner text NOT NULL, context_id text NOT NULL,
              message_id text NOT NULL, input_digest text NOT NULL, data jsonb NOT NULL,
              UNIQUE(agent, owner, message_id));
            CREATE TABLE IF NOT EXISTS outbox (
              case_id text PRIMARY KEY REFERENCES cases(id), payload jsonb NOT NULL,
              delivered boolean NOT NULL DEFAULT false, created_at timestamptz NOT NULL DEFAULT now());
            CREATE TABLE IF NOT EXISTS suppliers (
              id text PRIMARY KEY, case_id text UNIQUE NOT NULL REFERENCES cases(id),
              tax_id text UNIQUE NOT NULL, record jsonb NOT NULL, approved_by text NOT NULL,
              created_at timestamptz NOT NULL DEFAULT now());
            """)

    def create_case(self, data, creator, request_key):
        data = case_input(data)
        if not isinstance(request_key, str) or not 8 <= len(request_key) <= 100:
            raise DomainError('invalid_request_key', 'Use an idempotency key of 8 to 100 characters')
        with self.connection() as c, c.cursor(cursor_factory=RealDictCursor) as q:
            q.execute('INSERT INTO cases(id,creator,request_key,input,input_digest) VALUES(%s,%s,%s,%s,%s) ON CONFLICT(request_key) DO NOTHING RETURNING *',
                      (uuid.uuid4().hex, creator, request_key, Json(data), digest(data)))
            result = q.fetchone()
            if result is None:
                q.execute('SELECT * FROM cases WHERE request_key=%s', (request_key,))
                result = q.fetchone()
                if result['creator'] != creator or result['input_digest'] != digest(data):
                    raise DomainError('idempotency_conflict', 'Submission key was already used for different content')
            return dict(result)

    def get_case(self, case_id):
        with self.connection() as c, c.cursor(cursor_factory=RealDictCursor) as q:
            q.execute('SELECT * FROM cases WHERE id=%s', (case_id,))
            result = q.fetchone()
            if not result:
                raise DomainError('not_found', 'Case does not exist')
            return dict(result)

    def list_cases(self):
        with self.connection() as c, c.cursor(cursor_factory=RealDictCursor) as q:
            q.execute('SELECT * FROM cases ORDER BY created_at DESC LIMIT 200')
            return [dict(x) for x in q.fetchall()]

    def event(self, case_id, actor, kind, detail):
        with self.connection() as c, c.cursor() as q:
            q.execute('INSERT INTO events(case_id,actor,kind,detail) VALUES(%s,%s,%s,%s)', (case_id, actor, kind, Json(detail)))

    def events(self, case_id):
        with self.connection() as c, c.cursor(cursor_factory=RealDictCursor) as q:
            q.execute('SELECT * FROM events WHERE case_id=%s ORDER BY id', (case_id,))
            return [dict(x) for x in q.fetchall()]

    def update_case(self, case_id, revision, **fields):
        allowed = {'state', 'proposal', 'proposal_digest'}
        if not fields or set(fields) - allowed:
            raise DomainError('invalid_update', 'Invalid case update')
        assignments = ', '.join(f'{name}=%s' for name in fields)
        values = [Json(v) if name == 'proposal' and v is not None else v for name, v in fields.items()]
        with self.connection() as c, c.cursor() as q:
            q.execute(f"UPDATE cases SET {assignments},updated_at=now() WHERE id=%s AND revision=%s AND state NOT IN ('approved','completed','canceled')", (*values, case_id, revision))
            if q.rowcount != 1:
                raise DomainError('stale_case', 'Case changed while agent work was in progress')

    def resume_case(self, case_id, patch):
        if set(patch) != {'documents'}:
            raise DomainError('invalid_resume', 'Resume accepts only the requested documents')
        with self.connection() as c, c.cursor(cursor_factory=RealDictCursor) as q:
            q.execute('SELECT * FROM cases WHERE id=%s FOR UPDATE', (case_id,))
            row = q.fetchone()
            if not row or row['state'] != 'input-required':
                raise DomainError('invalid_resume', 'Case is not waiting for documents')
            data = case_input({**row['input'], **patch})
            q.execute("UPDATE cases SET input=%s,revision=revision+1,state='submitted',proposal=NULL,proposal_digest=NULL,updated_at=now() WHERE id=%s RETURNING *", (Json(data), case_id))
            return dict(q.fetchone())

    def approve(self, case_id, supplied_digest, reviewer):
        with self.connection() as c, c.cursor(cursor_factory=RealDictCursor) as q:
            q.execute('SELECT * FROM cases WHERE id=%s FOR UPDATE', (case_id,))
            row = q.fetchone()
            if not row or row['state'] not in {'review', 'approved', 'completed'}:
                raise DomainError('not_approvable', 'Case is not ready for approval')
            authorize_approval(row['proposal'], supplied_digest, reviewer, row['creator'])
            if row['state'] in {'approved', 'completed'}:
                return
            q.execute("UPDATE cases SET state='approved',approved_by=%s,updated_at=now() WHERE id=%s", (reviewer, case_id))
            payload = {'record': row['proposal'], 'approved_by': reviewer, 'digest': supplied_digest}
            q.execute('INSERT INTO outbox(case_id,payload) VALUES(%s,%s)', (case_id, Json(payload)))
            q.execute('INSERT INTO events(case_id,actor,kind,detail) VALUES(%s,%s,%s,%s)',
                      (case_id, reviewer, 'approved', Json({'digest': supplied_digest})))

    def deliver(self, before_commit=None):
        delivered = []
        with self.connection() as c, c.cursor(cursor_factory=RealDictCursor) as q:
            q.execute('SELECT * FROM outbox WHERE NOT delivered ORDER BY created_at FOR UPDATE SKIP LOCKED LIMIT 20')
            for row in q.fetchall():
                payload = row['payload']
                if digest(payload['record']) != payload['digest']:
                    raise DomainError('corrupt_command', 'Approved outbox command failed its digest check')
                q.execute('INSERT INTO suppliers(id,case_id,tax_id,record,approved_by) VALUES(%s,%s,%s,%s,%s) ON CONFLICT(case_id) DO NOTHING',
                          (uuid.uuid4().hex, row['case_id'], payload['record']['tax_id'], Json(payload['record']), payload['approved_by']))
                q.execute('UPDATE outbox SET delivered=true WHERE case_id=%s', (row['case_id'],))
                q.execute("UPDATE cases SET state='completed',updated_at=now() WHERE id=%s", (row['case_id'],))
                delivered.append(row['case_id'])
            if before_commit:
                before_commit()
        return delivered

    def suppliers(self):
        with self.connection() as c, c.cursor(cursor_factory=RealDictCursor) as q:
            q.execute('SELECT * FROM suppliers ORDER BY created_at DESC LIMIT 200')
            return [dict(x) for x in q.fetchall()]
