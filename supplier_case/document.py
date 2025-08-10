"""Independent document agent; it owns tasks and signs only its evidence."""
from .domain import DomainError, document_check, transition, digest
from .security import sign_artifact, owns, require_role
from .protocol import RPCError, message_data, task, agent_card

class DocumentAgent:
    name = 'document'
    def __init__(self, store, key, url):
        self.store, self.key, self.url = store, key, url
    def card(self):
        return agent_card(self.name, self.url, 'document-check')
    def result(self, row):
        data = row['data']
        return task(row['id'], row['context_id'], data['state'], data.get('result'), data.get('artifacts', []))

    def rpc(self, method, params, principal):
        require_role(principal, {'coordinator'})
        if method == 'tasks/get':
            row = self.store.get_task(params.get('id'), self.name)
            owns(row, principal)
            return self.result(row)
        if method not in {'message/send', 'message/stream'}:
            raise RPCError(-32601, 'Method not supported')
        message, data = message_data(params)
        context = message.get('contextId')
        if not isinstance(context, str) or not 1 <= len(context) <= 100:
            raise RPCError(-32602, 'A bounded contextId is required')
        if message.get('taskId'):
            row = self.store.get_task(message['taskId'], self.name)
            owns(row, principal)
            if row['context_id'] != context:
                raise DomainError('context_mismatch', 'Resume context does not match the original task')
            def resume(current):
                if current.get('resume_id') == message['messageId']:
                    if current.get('resume_digest') != digest(data):
                        raise DomainError('idempotency_conflict', 'Resume message changed')
                    return current
                transition(current['state'], 'working')
                checked = document_check(data)
                if checked['name'] != current['input']['name'] or checked['tax_id'] != current['input']['tax_id']:
                    raise DomainError('identity_changed', 'Resume cannot change supplier identity')
                return {**current, 'input': data, 'state': 'input-required' if checked['missing'] else 'completed',
                        'result': checked, 'resume_id': message['messageId'], 'resume_digest': digest(data),
                        'artifacts': [] if checked['missing'] else [sign_artifact(self.name, row['id'], context, checked, self.key)]}
            return self.result(self.store.mutate_task(row['id'], self.name, principal, resume))
        row = self.store.create_task(self.name, principal, message['messageId'], context, data)
        if row['data']['state'] == 'submitted':
            checked = document_check(data)
            state = 'input-required' if checked['missing'] else 'completed'
            artifacts = [] if checked['missing'] else [sign_artifact(self.name, row['id'], context, checked, self.key)]
            row = self.store.mutate_task(row['id'], self.name, principal,
                    lambda current: {**current, 'state': state, 'result': checked, 'artifacts': artifacts})
        return self.result(row)
