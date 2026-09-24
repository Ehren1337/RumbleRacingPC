"""Synthetic safety/reproduction tests; no game data or builds required."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location("port", Path(__file__).resolve().parents[1] / "port.py")
port = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(port)


class PortTests(unittest.TestCase):
    def test_lock_and_metadata(self):
        lock = port.load_lock()
        self.assertEqual(lock["generated_files"], 2144)
        self.assertEqual(len(lock["elf_sha256"]), 64)

    def test_live_process_probe_is_read_only(self):
        self.assertTrue(port.process_alive(os.getpid()))

    @unittest.skipUnless(os.name == "nt", "Windows Git path handling")
    def test_child_git_long_paths_preserve_inherited_config(self):
        original = {"Path": "example", "GIT_CONFIG_COUNT": "1",
                    "GIT_CONFIG_KEY_0": "example.setting", "GIT_CONFIG_VALUE_0": "keep"}
        env = port.command_environment(original)
        self.assertEqual(original["GIT_CONFIG_COUNT"], "1")
        self.assertEqual(env["PATH"], "example")
        self.assertEqual(env["GIT_CONFIG_COUNT"], "2")
        self.assertEqual(env["GIT_CONFIG_VALUE_0"], "keep")
        self.assertEqual(env["GIT_CONFIG_KEY_1"], "core.longpaths")
        self.assertEqual(env["GIT_CONFIG_VALUE_1"], "true")

    def test_digest_normalizes_only_line_endings(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "synthetic.cpp"
            p.write_bytes(b"example\r\n")
            a = port.generated_digest([p])
            p.write_bytes(b"example\n")
            self.assertEqual(a, port.generated_digest([p]))
            p.write_bytes(b"changed\n")
            self.assertNotEqual(a, port.generated_digest([p]))

    def test_edited_file_prevents_entire_staging_update(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runtime = root / "ps2xRuntime/src/runner"
            runtime.mkdir(parents=True)
            output = root / "generated"
            output.mkdir()
            fresh = output / "fresh.cpp"
            edited = output / "edited.cpp"
            fresh.write_text("new")
            edited.write_text("generated")
            (runtime / edited.name).write_text("hand edit")
            with self.assertRaisesRegex(ValueError, "independently edited"):
                port.stage_generated(root, [fresh, edited], {})
            self.assertFalse((runtime / fresh.name).exists())
            self.assertEqual((runtime / edited.name).read_text(), "hand edit")

    def test_owned_generation_updates_and_removes_only_owned_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runtime = root / "ps2xRuntime/src/runner"
            runtime.mkdir(parents=True)
            output = root / "generated"
            output.mkdir()
            dest = runtime / "sample.cpp"
            dest.write_text("old")
            obsolete = runtime / "obsolete.cpp"
            obsolete.write_text("old obsolete")
            unrelated = runtime / "handwritten.cpp"
            unrelated.write_text("keep")
            old = {dest.name: port.sha(dest), obsolete.name: port.sha(obsolete)}
            candidate = output / dest.name
            candidate.write_text("new")
            manifest, writes, removes = port.stage_generated(root, [candidate], old)
            self.assertEqual((writes, removes), (1, 1))
            self.assertEqual(manifest[dest.name], port.sha(dest))
            self.assertFalse(obsolete.exists())
            self.assertEqual(unrelated.read_text(), "keep")
            for bad in ("../escape.cpp", "nested/sample.cpp", "sample.txt"):
                with self.assertRaises(ValueError):
                    port.runtime_target(root, bad)

    def test_pose_identity_and_orientation_guards(self):
        identity = "a" * 64
        record = {"schema_version": 1, "elf_sha256": identity, "track_id": 10,
                  "matrix": [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 3, 4, 5, 1],
                  "position": [3, 4, 5]}
        self.assertTrue(port.benchmark_pose(record, identity).startswith("10 "))
        with self.assertRaises(ValueError):
            port.benchmark_pose(record, "b" * 64)
        record["matrix"][0] = -1
        with self.assertRaises(ValueError):
            port.benchmark_pose(record, identity)


if __name__ == "__main__":
    unittest.main()
