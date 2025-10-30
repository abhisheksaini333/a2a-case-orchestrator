"""Application orchestration; approval and effects stay outside agent authority."""
import os
from .model import extract, extract_rules
from .domain import DomainError, proposal, digest
from .security import verify_artifact, require_role
from .protocol import agent_card, RPCError

class Coordinator:
    name = 'coordinator'
    def __init__(self, store, document, catalog, keys):
        self.store, self.document, self.catalog, self.keys = store, document, catalog, keys
    def card(self):
        return agent_card(self.name, '/a2a', 'supplier-onboarding')

    def run(self, case_id):
        row = self.store.get_case(case_id)
        if row['state'] in {'approved', 'completed', 'canceled', 'review'}:
            return row
        revision, data = row['revision'], row['input']
        self.store.update_case(case_id, revision, state='working')
        try:
            self.document.discover()
            self.catalog.discover()
            previous = [e for e in self.store.events(case_id) if e['kind'] == 'document-task']
            prior_id = previous[-1]['detail']['task_id'] if previous else None
            result = self.document.send(data, case_id, f'{case_id}-document-{revision}', prior_id)
            self.store.event(case_id, 'document', 'document-task', {'task_id': result['id'], 'state': result['status']['state']})
            if result['status']['state'] == 'input-required':
                self.store.update_case(case_id, revision, state='input-required')
                self.store.event(case_id, 'document', 'input-required', result['status'].get('message', {}))
                return self.store.get_case(case_id)
            if result['status']['state'] != 'completed' or len(result.get('artifacts', [])) != 1:
                raise DomainError('document_failed', 'Document agent did not return verified evidence')
            checked = verify_artifact(result['artifacts'][0], 'document', result['id'], case_id, self.keys)
            self.store.event(case_id, 'document', 'artifact', result['artifacts'][0])
            match = self.catalog.send(data, case_id, f'{case_id}-catalog-{revision}')
            if match['status']['state'] != 'completed' or len(match.get('artifacts', [])) != 1:
                raise DomainError('catalog_failed', 'Catalog agent did not return match evidence')
            catalog = verify_artifact(match['artifacts'][0], 'catalog', match['id'], case_id, self.keys)
            self.store.event(case_id, 'catalog', 'artifact', match['artifacts'][0])
            record = proposal(checked, catalog)
            self.store.update_case(case_id, revision, state='review', proposal=record, proposal_digest=digest(record))
            self.store.event(case_id, 'coordinator', 'ready-for-review', {'digest': digest(record)})
        except DomainError as exc:
            try:
                self.store.update_case(case_id, revision, state='failed')
                self.store.event(case_id, 'coordinator', 'failed', {'code': exc.code, 'message': str(exc)})
            except DomainError:
                pass  # A concurrent cancellation or resume owns the newer revision.
            raise
        return self.store.get_case(case_id)

    def resume(self, case_id, patch):
        self.store.resume_case(case_id, patch)
        return self.run(case_id)

    def cancel(self, case_id, actor):
        self.store.cancel_case(case_id, actor)
        previous = [e for e in self.store.events(case_id) if e['kind'] == 'document-task']
        if previous and previous[-1]['detail']['state'] == 'input-required':
            try:
                self.document.rpc('tasks/cancel', {'id': previous[-1]['detail']['task_id']})
                self.store.event(case_id, 'document', 'canceled', {})
            except DomainError as exc:
                self.store.event(case_id, 'coordinator', 'cancel-delivery-pending', {'code': exc.code})
        return self.store.get_case(case_id)

    def api(self, method, path, payload, principal):
        require_role(principal, {'operator', 'reviewer'})
        if method == 'GET' and path == '/api/session':
            return {'principal': principal}
        if method == 'POST' and path == '/api/extract':
            if payload.get('mode') == 'rules':
                return extract_rules(payload.get('text', ''))
            if payload.get('mode') == 'local-model':
                return extract(payload.get('text'), os.environ.get('MODEL_ENDPOINT', ''), os.environ.get('MODEL_NAME', 'default_model'))
            raise DomainError('invalid_mode', 'Choose rules or local-model extraction')
        parts = path.strip('/').split('/')
        if method == 'GET' and path == '/api/cases':
            return {'cases': self.store.list_cases(), 'pending': self.store.pending_count()}
        if method == 'GET' and path == '/api/suppliers':
            return {'suppliers': self.store.suppliers()}
        if method == 'GET' and len(parts) == 3 and parts[:2] == ['api', 'cases']:
            return {'case': self.store.get_case(parts[2]), 'events': self.store.events(parts[2])}
        if method == 'POST' and path == '/api/cases':
            row = self.store.create_case(payload.get('supplier'), principal, payload.get('request_key'))
            return self.run(row['id'])
        if method == 'POST' and len(parts) == 4 and parts[:2] == ['api', 'cases']:
            case_id, action = parts[2], parts[3]
            if action == 'run':
                return self.run(case_id)
            if action == 'resume':
                return self.resume(case_id, payload)
            if action == 'cancel':
                return self.cancel(case_id, principal)
            if action == 'approve':
                self.store.approve(case_id, payload.get('digest'), principal)
                self.store.deliver()
                return self.store.get_case(case_id)
        raise DomainError('not_found', 'Operation not found')

    def recover(self):
        results = []
        self.store.deliver()
        for case_id in self.store.recoverable_cases():
            try:
                results.append(self.run(case_id)['id'])
            except DomainError:
                continue  # The durable case event holds the operator-visible failure.
        return results
