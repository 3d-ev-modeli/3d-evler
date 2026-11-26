import copy
import importlib.util
import io
import json
from pathlib import Path
import struct
import tempfile
import unittest

from PIL import Image

spec = importlib.util.spec_from_file_location("drive_import", Path(__file__).parents[1] / "tools/drive_import.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
FONT = "C:/Windows/Fonts/arialbd.ttf" if Path("C:/Windows/Fonts/arialbd.ttf").exists() else "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def image(width, height):
    out = io.BytesIO()
    Image.new("RGB", (width, height), "#85adcd").save(out, "PNG")
    return out.getvalue()


def glb():
    data = json.dumps({"asset": {"version": "2.0"}}).encode()
    data += b" " * (-len(data) % 4)
    return struct.pack("<4sIIII", b"glTF", 2, len(data) + 20, len(data), 0x4E4F534A) + data


def file(fid, name, mime="application/octet-stream"):
    return {"id": fid, "name": name, "mimeType": mime}


class FakeDrive:
    def __init__(self):
        self.resource_keys = {}
        self.root = file("folder000000", "057-Gürpınar 6+1 Villa", module.FOLDER)
        self.items = {
            "folder000000": [file("glbfolder000", "057-villa - glb", module.FOLDER), file("photofolder0", "057-villa - foto", module.FOLDER), file("cover000000", "kapak.png"), file("music000000", "muzik.mp3")],
            "glbfolder000": [file("model000000", "zemin.glb")],
            "photofolder0": [file("floor000000", "zemin kat", module.FOLDER)],
            "floor000000": [file("pano0000000", "salon.jpg")],
        }
        self.data = {"model000000": glb(), "cover000000": image(1448, 1086), "music000000": b"ID3" + b"test music", "pano0000000": image(200, 100)}

    def metadata(self, fid):
        return self.root

    def children(self, fid):
        return copy.deepcopy(self.items[fid])

    def download(self, item, limit):
        return self.data[item["id"]]


class ImportTests(unittest.TestCase):
    def setUp(self):
        self.drive = FakeDrive()
        self.config = {"musicUrl": "", "models": {}, "villas": {"ref-999": {"ref": "999", "musicUrl": "./audio/old.mp3"}}}

    def prepare(self, **kwargs):
        return module.prepare(self.drive, "https://drive.google.com/drive/folders/folder000000", self.config, base_url="https://example.test/site", font_path=FONT, **kwargs)

    def test_complete_import_and_unplaced_markers(self):
        pending, result = self.prepare()
        cfg = json.loads(pending["program/config/portfolios.json"])
        record = cfg["villas"]["ref-057v"]
        self.assertEqual(cfg["villas"]["ref-999"], self.config["villas"]["ref-999"])
        self.assertEqual(result["models"], 1)
        self.assertEqual(result["photos360"], 1)
        self.assertEqual(result["unplaced"], 1)
        self.assertEqual(record["floors"]["zemin.glb"]["panoramas"], [])
        self.assertIn("program/ref-057v/zemin.glb", pending)
        self.assertIn("<iframe", pending["program/share/ref-057v.html"].decode())
        self.assertNotIn("location.replace", pending["program/share/ref-057v.html"].decode())

    def test_idempotent_and_preserve_coordinates(self):
        pending, _ = self.prepare()
        self.config = json.loads(pending["program/config/portfolios.json"])
        floor = self.config["villas"]["ref-057v"]["floors"]["zemin.glb"]
        floor["panoramas"] = [{"driveFileId": "pano0000000", "position": [1, 2, 3], "initialYaw": 90}]
        floor["entranceArrow"] = {"position": [4, 5, 6], "direction": [0, 0, 1]}
        new, result = self.prepare()
        cfg = json.loads(new["program/config/portfolios.json"])
        floor = cfg["villas"]["ref-057v"]["floors"]["zemin.glb"]
        self.assertEqual(floor["panoramas"][0]["position"], [1, 2, 3])
        self.assertEqual(floor["panoramas"][0]["initialYaw"], 90)
        self.assertEqual(floor["entranceArrow"]["position"], [4, 5, 6])
        self.assertEqual(result["unplaced"], 0)
        self.config = cfg
        again, _ = self.prepare()
        self.assertEqual(new, again)
        with tempfile.TemporaryDirectory() as directory:
            module.apply_plan(directory, new)
            self.assertEqual(module.apply_plan(directory, again), [])

    def test_same_name_replacement_keeps_marker(self):
        pending, _ = self.prepare()
        self.config = json.loads(pending["program/config/portfolios.json"])
        self.config["villas"]["ref-057v"]["floors"]["zemin.glb"]["panoramas"] = [{"driveFileId": "pano0000000", "position": [1, 2, 3]}]
        self.drive.items["floor000000"][0]["id"] = "panoNEW0000"
        self.drive.data["panoNEW0000"] = image(200, 100)
        pending, _ = self.prepare()
        marker = json.loads(pending["program/config/portfolios.json"])["villas"]["ref-057v"]["floors"]["zemin.glb"]["panoramas"][0]
        self.assertEqual(marker["driveFileId"], "panoNEW0000")
        self.assertEqual(marker["position"], [1, 2, 3])

    def test_exported_marker_file(self):
        self.drive.items["folder000000"].append(file("mapping0000", "isaretler.json"))
        self.drive.data["mapping0000"] = json.dumps({"villa": "ref-057v", "floors": {"zemin.glb": {"panoramas": [{"driveFileId": "pano0000000", "position": [0, 1, 2], "url": "https://untrusted.test/image"}]}}}).encode()
        pending, result = self.prepare()
        marker = json.loads(pending["program/config/portfolios.json"])["villas"]["ref-057v"]["floors"]["zemin.glb"]["panoramas"][0]
        self.assertTrue(marker["url"].startswith("./360/057v/"))
        self.assertEqual(result["unplaced"], 0)

    def test_no_write_on_bad_glb(self):
        original = copy.deepcopy(self.config)
        self.drive.data["model000000"] = b"not a model"
        with self.assertRaises(module.ImportError_):
            self.prepare()
        self.assertEqual(self.config, original)

    def test_single_floor_apartment_with_root_model_and_photos(self):
        self.drive.root["name"] = "007-Beylikdüzü 3+1 Daire"
        self.drive.items["folder000000"] = [item for item in self.drive.items["folder000000"] if item["id"] != "glbfolder000"]
        self.drive.items["folder000000"].append(file("model000000", "daire.glb"))
        self.drive.items["photofolder0"] = [file("pano0000000", "salon.jpg")]
        pending, result = self.prepare(location="Beylikdüzü", details="3+1 Daire")
        record = json.loads(pending["program/config/portfolios.json"])["villas"]["ref-007d"]
        self.assertEqual(result["models"], 1)
        self.assertEqual(result["photos360"], 1)
        self.assertEqual(list(record["floors"]), ["daire.glb"])
        self.assertEqual(record["details"], "3+1 Daire")
        self.assertIn("program/ref-007d/daire.glb", pending)

    def test_bad_music(self):
        self.drive.data["music000000"] = b"<html>not an mp3</html>"
        with self.assertRaises(module.ImportError_):
            self.prepare()

    def test_same_number_villa_and_apartment_are_distinct(self):
        pending, _ = self.prepare(ref="057V")
        cfg = json.loads(pending["program/config/portfolios.json"])
        self.drive.root["name"] = "057-Daire"
        self.drive.items["apartment000"] = self.drive.items["folder000000"]
        pending, result = module.prepare(self.drive, "apartment000", cfg, ref="057d", base_url="https://example.test", font_path=FONT)
        updated = json.loads(pending["program/config/portfolios.json"])
        self.assertEqual(updated["villas"]["ref-057v"]["ref"], "057v")
        self.assertEqual(updated["villas"]["ref-057d"]["ref"], "057d")
        self.assertTrue(result["viewer"].endswith("ref-057d"))

    def test_legacy_marker_export_is_accepted_for_migrated_portfolio(self):
        self.config["villas"]["ref-057v"] = {"ref": "057v", "legacyFolders": ["ref-057"]}
        self.drive.items["folder000000"].append(file("mapping0000", "isaretler.json"))
        self.drive.data["mapping0000"] = json.dumps({"villa": "ref-057", "floors": {"zemin.glb": {"panoramas": [{"driveFileId": "pano0000000", "position": [0, 1, 2]}]}}}).encode()
        pending, result = self.prepare()
        self.assertEqual(result["unplaced"], 0)
        self.assertIn("program/share/ref-057.html", pending)

    def test_ambiguous_type_needs_suffix(self):
        self.drive.root["name"] = "057-Portföy"
        with self.assertRaisesRegex(module.ImportError_, "Tür belirlenemedi"):
            self.prepare()

    def test_normal_photo_not_a_fake_marker(self):
        self.drive.data["pano0000000"] = image(200, 150)
        pending, result = self.prepare()
        self.assertEqual(result["photos360"], 0)
        self.assertEqual(len(result["warnings"]), 1)

    def test_ambiguous_cover(self):
        self.drive.items["folder000000"] += [file("cover222222", "kapak.jpg")]
        with self.assertRaises(module.ImportError_):
            self.prepare()

    def test_wrong_source_cannot_overwrite_ref(self):
        self.config["villas"]["ref-057v"] = {"ref": "057", "driveFolderId": "differentFolder"}
        with self.assertRaises(module.ImportError_):
            self.prepare()

    def test_reject_unknown_floor_mapping(self):
        self.drive.items["folder000000"].append(file("mapping0000", "isaretler.json"))
        self.drive.data["mapping0000"] = json.dumps({"villa": "ref-057v", "floors": {"../index.html": {}}}).encode()
        with self.assertRaises(module.ImportError_):
            self.prepare()

    def test_cover_preserves_full_photo_and_sizes(self):
        data, size = module.cover(Image.new("RGB", (1448, 1086), "green"), "057", "Villa", FONT)
        self.assertEqual(size, (1200, 1004))
        self.assertLess(len(data), 300_000)
        im = Image.open(io.BytesIO(data))
        self.assertGreater(im.getpixel((600, 880))[1], 60)

    def test_path_guard_and_url_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(module.ImportError_):
                module.apply_plan(directory, {"program/../../index.html": b"bad"})
            self.assertEqual(list(Path(directory).iterdir()), [])
        for url in ("https://evil.test/drive/folders/folder000000", "file:///tmp/file", "../folder"):
            with self.assertRaises(module.ImportError_):
                module.folder_id(url)

    def test_missing_key_is_actionable(self):
        with self.assertRaisesRegex(module.ImportError_, "GOOGLE_DRIVE_API_KEY"):
            module.Drive("")

    def test_html_escape(self):
        page = module.share_page("https://example.test", "057", '<script>"', "https://example.test/a.jpg", (1200, 630), "abc")
        self.assertNotIn('<script>"', page)
        self.assertIn("&lt;script&gt;&quot;", page)


if __name__ == "__main__":
    unittest.main()
