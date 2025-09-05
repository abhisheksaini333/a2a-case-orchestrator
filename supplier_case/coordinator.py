"""Application orchestration; approval and effects stay outside agent authority."""
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
