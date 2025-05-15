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
