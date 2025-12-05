"""Start three isolated services and exercise the actual React operator flow."""

import os
import subprocess
from pathlib import Path
from tests.test_processes import Processes

harness = Processes()
Processes.setUpClass()
try:
    harness.setUp()
    environment = {
        **os.environ,
        "APP_URL": harness.base,
        "OPERATOR_TOKEN": harness.env["OPERATOR_TOKEN"],
        "REVIEWER_TOKEN": harness.env["REVIEWER_TOKEN"],
    }
    subprocess.run(
        ["node", "smoke.mjs"],
        cwd=Path(__file__).resolve().parents[1] / "frontend",
        env=environment,
        check=True,
    )
finally:
    harness.tearDown()
    Processes.tearDownClass()
