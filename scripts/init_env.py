"""Generate local credentials without printing them or replacing existing keys."""

import os, secrets
from pathlib import Path

path = Path(".env")
values = [
    "POSTGRES_PASSWORD",
    "COORDINATOR_TOKEN",
    "OPERATOR_TOKEN",
    "REVIEWER_TOKEN",
    "DOCUMENT_KEY",
    "CATALOG_KEY",
]
try:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
except FileExistsError:
    raise SystemExit(".env already exists; it was not changed")
with os.fdopen(descriptor, "w") as target:
    target.write(
        "\n".join(name + "=" + secrets.token_hex(24) for name in values) + "\n"
    )
print(
    "Created .env with private local credentials. Keep it with the durable state backup."
)
