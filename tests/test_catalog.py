import json, os, subprocess, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(os.getenv("DOTNET"), "requires .NET SDK")
class Catalog(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dotnet = os.environ["DOTNET"]
        result = subprocess.run(
            [cls.dotnet, "build", "catalog", "-o", "catalog/bin/test", "--nologo"],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        if result.returncode:
            raise AssertionError(result.stdout + result.stderr)

    def evaluate(self, description):
        result = subprocess.run(
            [self.dotnet, str(ROOT / "catalog/bin/test/Catalog.dll"), "evaluate"],
            input=json.dumps({"description": description}),
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_category_and_risk_are_bounded_business_rules(self):
        self.assertEqual(
            self.evaluate("Laptop and server repair"),
            {"category": "technology", "risk": "low"},
        )
        self.assertEqual(
            self.evaluate("Paper and pens"), {"category": "office", "risk": "low"}
        )
        self.assertEqual(
            self.evaluate("industrial machine bearings"),
            {"category": "industrial", "risk": "low"},
        )
        self.assertEqual(
            self.evaluate("sanctioned weapons supplier")["risk"], "blocked"
        )
