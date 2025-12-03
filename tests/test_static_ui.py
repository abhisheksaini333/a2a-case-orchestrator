import tempfile, threading, unittest, urllib.request, urllib.error
from pathlib import Path
from supplier_case.transport import server


class UI(unittest.TestCase):
    def test_only_built_assets_are_served_and_paths_cannot_escape(self):
        with tempfile.TemporaryDirectory() as folder:
            Path(folder, "index.html").write_text("<title>Supplier desk</title>")
            Path(folder, "main.js").write_text('console.log("ui")')
            http = server(
                type("Service", (), {"name": "coordinator"})(), {}, ui_dir=folder
            )
            thread = threading.Thread(target=http.serve_forever, daemon=True)
            thread.start()
            try:
                base = "http://127.0.0.1:" + str(http.server_port)
                with urllib.request.urlopen(base + "/") as r:
                    self.assertIn("Supplier desk", r.read().decode())
                with self.assertRaises(urllib.error.HTTPError):
                    urllib.request.urlopen(base + "/assets/../index.html")
            finally:
                http.shutdown()
                http.server_close()
                thread.join()
