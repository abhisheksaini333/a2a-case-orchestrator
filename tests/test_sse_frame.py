import unittest
from supplier_case import protocol as p


class Streaming(unittest.TestCase):
    def test_status_and_artifact_frames_are_valid_json_rpc_events(self):
        t = p.task(
            "t1", "c1", "completed", artifacts=[{"artifactId": "a1", "parts": []}]
        )
        frames = p.stream_frames("r1", t)
        self.assertEqual(len(frames), 3)
        import json

        decoded = [json.loads(x.split("data: ", 1)[1]) for x in frames]
        self.assertEqual(decoded[0]["result"]["kind"], "task")
        self.assertEqual(decoded[1]["result"]["kind"], "artifact-update")
        self.assertTrue(decoded[-1]["result"]["final"])
