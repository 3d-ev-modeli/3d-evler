"""Extract only typed portfolio references, Video and Detay URLs from XLSX."""
from __future__ import annotations
import argparse
import io
import json
from pathlib import Path, PurePosixPath
import re
import unicodedata
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET
import zipfile

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"

def normalized(value):
    return "".join(c for c in unicodedata.normalize("NFKD", str(value).replace("ı", "i")) if not unicodedata.combining(c)).strip().lower()

def typed_ref(value, kind):
    text = str(value).strip().lower()
    match = re.fullmatch(r"(?:villa|daire|ref\s*:?\s*)?\s*0*(\d+)(?:\.0+)?\s*([vd]?)", text)
    if not match or (match[2] and match[2] != kind):
        return None
    return str(int(match[1])) + kind

def safe_video_url(value):
    value = str(value or "").strip()
    if not value:
        return ""
    url = urlsplit(value)
    if url.scheme != "https" or not url.hostname or url.username or url.password:
        raise ValueError("Video bağlantısı geçerli bir HTTPS bağlantısı olmalı.")
    return value

def extract_video_links(path):
    result, detail_result, found_kinds = {}, {}, set()
    with zipfile.ZipFile(path) as archive:
        if sum(i.file_size for i in archive.infolist()) > 100 * 1024 * 1024:
            raise ValueError("Excel dosyası çok büyük.")
        strings = []
        if "xl/sharedStrings.xml" in archive.namelist():
            strings = ["".join(si.itertext()) for si in ET.fromstring(archive.read("xl/sharedStrings.xml")).findall("m:si", NS)]
        relationships = {r.attrib["Id"]: r.attrib["Target"] for r in ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))}
        sheets = ET.fromstring(archive.read("xl/workbook.xml")).findall("m:sheets/m:sheet", NS)
        for sheet in sheets:
            name = normalized(sheet.attrib["name"])
            kind = "v" if name in ("villa", "villalar") else "d" if name in ("daire", "daireler") else None
            if not kind:
                continue
            if kind in found_kinds:
                raise ValueError("Aynı tür için birden fazla Excel sayfası var.")
            found_kinds.add(kind)
            target = relationships[sheet.attrib[REL]]
            sheet_path = target.lstrip("/") if target.startswith("/") else "xl/" + target
            xml = ET.fromstring(archive.read(sheet_path))
            links = {}
            rel_path = str(PurePosixPath(sheet_path).parent / "_rels" / (PurePosixPath(sheet_path).name + ".rels"))
            if rel_path in archive.namelist():
                targets = {r.attrib["Id"]: r.attrib["Target"] for r in ET.fromstring(archive.read(rel_path))}
                links = {h.attrib["ref"]: targets.get(h.attrib.get(REL), "") for h in xml.findall("m:hyperlinks/m:hyperlink", NS)}
            rows = []
            for row in xml.findall("m:sheetData/m:row", NS):
                cells = {}
                for cell in row.findall("m:c", NS):
                    value = cell.findtext("m:v", default="", namespaces=NS)
                    if cell.attrib.get("t") == "s":
                        value = strings[int(value)]
                    elif cell.attrib.get("t") == "inlineStr":
                        value = "".join(cell.find("m:is", NS).itertext())
                    cells[re.sub(r"\d", "", cell.attrib["r"])] = (value, cell.attrib["r"], cell.findtext("m:f", default="", namespaces=NS))
                rows.append(cells)
            header_index = next((i for i, row in enumerate(rows[:20]) if any(normalized(c[0]) == "video" for c in row.values())), None)
            if header_index is None:
                raise ValueError(sheet.attrib["name"] + " sayfasında Video sütunu bulunamadı.")
            header = rows[header_index]
            video_columns = [col for col, c in header.items() if normalized(c[0]) == "video"]
            detail_columns = [col for col, c in header.items() if normalized(c[0]) == "detay"]
            ref_columns = [col for col, c in header.items() if normalized(c[0]) in ("ref", "no", "numara", "portfoy no", "portfoy", "foto")]
            if len(video_columns) != 1 or len(ref_columns) != 1:
                raise ValueError("Video veya portföy numarası sütunu belirsiz.")
            if len(detail_columns) > 1:
                raise ValueError("Detay sütunu belirsiz.")
            for row in rows[header_index + 1:]:
                key = typed_ref(row.get(ref_columns[0], ("",))[0], kind)
                if not key:
                    continue
                for columns, output in ((video_columns, result), (detail_columns, detail_result)):
                    value, address, formula = row.get(columns[0], ("", "", "")) if columns else ("", "", "")
                    formula_link = re.match(r'\s*(?:_xlfn\.)?HYPERLINK\s*\(\s*"((?:[^"\n]|"")*)"', formula, re.I)
                    url = safe_video_url(links.get(address) or (formula_link[1].replace('""', '"') if formula_link else value))
                    if key in output and output[key] != url:
                        raise ValueError("Aynı portföy için farklı bağlantı kayıtları var: " + key)
                    output[key] = url
    if found_kinds != {"v", "d"}:
        raise ValueError("Villalar ve Daireler sayfalarının ikisi de gerekli.")
    return {"version": 1, "videos": result, "details": detail_result}

def published_links(payload, config):
    keys = {typed_ref(record.get("ref", ""), kind)
            for collection in (config.get("villas", {}), config.get("models", {}))
            for record in collection.values() for kind in ("v", "d")}
    return {"version": 1, **{field: {key: payload.get(field, {}).get(key, "")
            for key in sorted(keys - {None})} for field in ("videos", "details")}}

def sync_drive_catalog(drive, root, pending):
    source_path = Path(root) / "program/config/catalog-source.json"
    if not source_path.exists():
        return False
    source = json.loads(source_path.read_text(encoding="utf-8"))
    file_id = source.get("driveFileId", "")
    if not file_id:
        return False
    if not re.fullmatch(r"[A-Za-z0-9_-]{10,200}", file_id):
        raise ValueError("Excel kaynak dosyasının Drive kimliği geçersiz.")
    drive.resource_keys[file_id] = source.get("resourceKey", "")
    item = drive.metadata(file_id)
    if not item["name"].lower().endswith(".xlsx"):
        raise ValueError("Video/Detay kaynağı portfoyler.xlsx biçiminde olmalı.")
    catalog = extract_video_links(io.BytesIO(drive.download(item, 20 * 1024 * 1024)))
    config = json.loads(pending["program/config/portfolios.json"])
    payload = published_links(catalog, config)
    pending["program/config/video-links.json"] = (json.dumps(payload, ensure_ascii=True, indent=2) + "\n").encode("utf-8")
    return True

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workbook")
    parser.add_argument("--output", required=True)
    parser.add_argument("--portfolio-config", required=True, help="Publish links only for configured portfolios.")
    args = parser.parse_args()
    payload = extract_video_links(args.workbook)
    config = json.loads(Path(args.portfolio_config).read_text(encoding="utf-8"))
    payload = published_links(payload, config)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    print("Video links extracted:", sum(bool(v) for v in payload["videos"].values()))

if __name__ == "__main__":
    main()
