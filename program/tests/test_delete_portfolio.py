import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("delete_portfolio", Path(__file__).parents[1] / "tools/delete_portfolio.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class DeleteTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.config = {"villas": {"ref-057": {"ref": "057"}, "ref-0570": {"ref": "0570"}}, "models": {}}
        for name in ("program/index.html", "program/ref-057/zemin.glb", "program/ref-0570/zemin.glb", "program/covers/057-test.jpg", "program/covers/0570-test.jpg", "program/audio/057-test.mp3", "program/share/ref-057.html", "program/360/057/pano.jpg"):
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"fixture")

    def tearDown(self):
        self.temp.cleanup()

    def test_only_exact_portfolio_selected(self):
        cfg, paths = module.deletion_plan(self.root, self.config, "057", "057")
        self.assertNotIn("ref-057", cfg["villas"])
        self.assertIn("ref-0570", cfg["villas"])
        relative = [p.relative_to(self.root).as_posix() for p in paths]
        self.assertIn("program/ref-057", relative)
        self.assertIn("program/covers/057-test.jpg", relative)
        self.assertNotIn("program/index.html", relative)
        self.assertFalse(any("0570" in p for p in relative))
        self.assertIn("ref-057", self.config["villas"])

    def test_mismatch_unknown_and_path_rejected(self):
        for ref, confirm in (("057", "57"), ("999", "999"), ("../057", "../057")):
            with self.assertRaises(ValueError):
                module.deletion_plan(self.root, self.config, ref, confirm)
        self.assertTrue((self.root / "program/ref-057/zemin.glb").exists())

    def test_shared_asset_blocks_deletion(self):
        self.config["villas"]["ref-0570"]["coverImage"] = "./covers/057-test.jpg"
        with self.assertRaisesRegex(ValueError, "başka kayıt"):
            module.deletion_plan(self.root, self.config, "057", "057")


if __name__ == "__main__":
    unittest.main()
