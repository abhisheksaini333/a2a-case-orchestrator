"""Launch one service per process; credentials are injected by the operator."""
import argparse
import os
import signal
import threading
from pathlib import Path
from .store import Store
from .document import DocumentAgent
from .client import Client
from .coordinator import Coordinator
from .transport import server

def required(name):
    value = os.environ.get(name, '')
    if len(value) < 32:
        raise SystemExit(name + ' must contain at least 32 characters')
    return value

def main():
    parser = argparse.ArgumentParser(description='Supplier onboarding agent service')
    parser.add_argument('command', choices=['serve', 'recover'])
    parser.add_argument('service', choices=['document', 'coordinator'])
    parser.add_argument('--port', type=int, default=18130)
    parser.add_argument('--host', default='127.0.0.1')
    args = parser.parse_args()
    store = Store(os.environ['DATABASE_URL'])
    store.migrate()
    coordinator_token = required('COORDINATOR_TOKEN')
    if args.service == 'document':
        service = DocumentAgent(store, required('DOCUMENT_KEY'), f'http://{args.host}:{args.port}/a2a')
        tokens = {'coordinator': coordinator_token}
    else:
        service = Coordinator(store,
                Client(os.environ.get('DOCUMENT_URL', 'http://127.0.0.1:18131'), coordinator_token, 'document', 'document-check'),
                Client(os.environ.get('CATALOG_URL', 'http://127.0.0.1:18132'), coordinator_token, 'catalog', 'catalog-match'),
                {'document': required('DOCUMENT_KEY'), 'catalog': required('CATALOG_KEY')})
        tokens = {'operator': required('OPERATOR_TOKEN'), 'reviewer': required('REVIEWER_TOKEN'), 'case-client': coordinator_token}
        if len(set(tokens.values())) != len(tokens):
            raise SystemExit('Operator and reviewer credentials must differ')
        if args.command == 'recover':
            service.recover()
            return
        service.recover()
    http = server(service, tokens, args.host, args.port, Path(__file__).resolve().parents[1] / 'frontend' / 'dist' if args.service == 'coordinator' else None)
    def shutdown(*_):
        threading.Thread(target=http.shutdown, daemon=True).start()
    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    try:
        http.serve_forever()
    finally:
        http.server_close()

if __name__ == '__main__':
    main()
