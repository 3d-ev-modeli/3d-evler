"""Import one public Drive portfolio. Only explicit supported assets are written."""
from __future__ import annotations

import argparse
import copy
import hashlib
import html
import io
import json
import math
import os
from pathlib import Path
import re
import struct
import sys
import unicodedata
import urllib.error
import urllib.parse
import urllib.request

from PIL import Image, ImageDraw, ImageFont, ImageOps

FOLDER = "application/vnd.google-apps.folder"
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp"}
BASE = "https://www.googleapis.com/drive/v3/files"


class ImportError_(ValueError):
    pass


def normalize(value):
    value = value.translate(str.maketrans("ıİşŞğĞüÜöÖçÇ", "iIsSgGuUoOcC"))
    return re.sub(r"[^a-z0-9]+", "-", unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower()).strip("-")


def floor_key(name):
    value = normalize(Path(name).stem)
    if "bodrum" in value or "basement" in value:
        return "bodrum"
    if "zemin" in value or "ground" in value:
        return "zemin"
    match = re.search(r"(?:^|-)([1-9][0-9]*)(?:-kat|$)", value)
    return match.group(1) if match else value


def folder_id(value):
    if re.fullmatch(r"[A-Za-z0-9_-]{10,200}", value):
        return value, ""
    url = urllib.parse.urlparse(value)
    match = re.fullmatch(r"/drive/(?:u/\d+/)?folders/([A-Za-z0-9_-]{10,200})/?", url.path)
    if url.scheme != "https" or url.hostname != "drive.google.com" or not match:
        raise ImportError_("Drive klasör bağlantısı geçersiz. drive.google.com/drive/folders/... kullanın.")
    return match.group(1), urllib.parse.parse_qs(url.query).get("resourcekey", [""])[0]


class Drive:
    def __init__(self, api_key):
        if not api_key:
            raise ImportError_("Bir defalık kurulum eksik: GitHub Secrets içine GOOGLE_DRIVE_API_KEY ekleyin.")
        self.key = api_key
        self.resource_keys = {}

    def request(self, path="", params=None, limit=1024 * 1024, resource_id=None):
        url = BASE + path + "?" + urllib.parse.urlencode(params or {})
        headers = {"X-Goog-Api-Key": self.key}
        keys = [f"{fid}/{key}" for fid, key in self.resource_keys.items() if key]
        if keys:
            headers["X-Goog-Drive-Resource-Keys"] = ",".join(keys)
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=90) as response:
                data = response.read(limit + 1)
        except urllib.error.HTTPError as error:
            raise ImportError_(f"Drive okunamadı (HTTP {error.code}). Drive API anahtarını ve klasörün bağlantıya açık paylaşımını kontrol edin.") from None
        except (urllib.error.URLError, TimeoutError):
            raise ImportError_("Drive bağlantısı kurulamadı. Daha sonra yeniden çalıştırın.") from None
        if len(data) > limit:
            raise ImportError_("Dosya izin verilen boyutu aşıyor.")
        return data

    def metadata(self, fid):
        data = json.loads(self.request("/" + fid, {"fields": "id,name,mimeType,resourceKey"}))
        self.resource_keys[fid] = data.get("resourceKey", "")
        return data

    def children(self, fid):
        result, token = [], None
        while True:
            params = {"q": f"'{fid}' in parents and trashed = false", "pageSize": 1000,
                      "fields": "nextPageToken,files(id,name,mimeType,size,md5Checksum,resourceKey)"}
            if token:
                params["pageToken"] = token
            data = json.loads(self.request(params=params, limit=4 * 1024 * 1024))
            for item in data.get("files", []):
                self.resource_keys[item["id"]] = item.get("resourceKey", "")
                result.append(item)
            if len(result) > 2000:
                raise ImportError_("Klasör çok büyük; tek portföy klasörü seçin.")
            token = data.get("nextPageToken")
            if not token:
                return result

    def download(self, item, limit):
        if int(item.get("size", 0)) > limit:
            raise ImportError_(f"Dosya çok büyük: {item['name']}")
        data = self.request("/" + item["id"], {"alt": "media"}, limit=limit)
        if item.get("size") and len(data) != int(item["size"]):
            raise ImportError_(f"Eksik indirme: {item['name']}")
        if item.get("md5Checksum") and hashlib.md5(data).hexdigest() != item["md5Checksum"]:
            raise ImportError_(f"Dosya doğrulanamadı: {item['name']}")
        return data


def choose(items, predicate, label):
    found = [item for item in items if predicate(item)]
    if len(found) > 1:
        raise ImportError_(f"Birden fazla {label} var. Dosyaları tekilleştirin.")
    return found[0] if found else None


def image_bytes(data):
    try:
        image = Image.open(io.BytesIO(data))
        image.load()
        return ImageOps.exif_transpose(image).convert("RGB")
    except (OSError, ValueError, Image.DecompressionBombError):
        raise ImportError_("Fotoğraf açılamadı veya bozuk.") from None


def validate_glb(data):
    if len(data) < 20 or data[:4] != b"glTF":
        raise ImportError_("GLB dosyasının başlığı geçersiz.")
    _, version, length = struct.unpack_from("<4sII", data)
    if version != 2 or length != len(data):
        raise ImportError_("GLB sürümü veya dosya boyutu geçersiz.")
    chunk_length, chunk_type = struct.unpack_from("<II", data, 12)
    if chunk_type != 0x4E4F534A or 20 + chunk_length > len(data):
        raise ImportError_("GLB model bilgisi okunamadı.")
    try:
        model = json.loads(data[20:20 + chunk_length])
    except (ValueError, UnicodeError):
        raise ImportError_("GLB model bilgisi bozuk.") from None
    for record in model.get("buffers", []) + model.get("images", []):
        if "uri" in record and not record["uri"].startswith("data:"):
            raise ImportError_("GLB tüm dokuları içinde barındırmalı; dış dosya bağlantısı var.")


def vector(value, label):
    if not isinstance(value, list) or len(value) != 3 or not all(type(v) in (int, float) and math.isfinite(v) for v in value):
        raise ImportError_(f"Geçersiz {label}; üç sayısal koordinat gerekli.")
    return value


def cover(image, ref, title, font_path, price=""):
    # Fit without cropping: preserve the villa, garden and foreground.
    image.thumbnail((1200, 1200), Image.Resampling.LANCZOS)
    width, height = image.size
    scale = width / 1200
    band = max(72, round(104 * scale))
    result = Image.new("RGB", (width, height + band), "#ffe800")
    result.paste(image, (0, 0))
    draw = ImageDraw.Draw(result)
    caption_font_path = font_path.replace("-Bold.ttf", ".ttf")
    badge_font = ImageFont.truetype(caption_font_path, max(24, round(44 * scale)))
    title_size = max(24, round(34 * scale))
    title_font = ImageFont.truetype(caption_font_path, title_size)
    while draw.textlength(title, font=title_font) > width - 48 and title_size > 16:
        title_size -= 1
        title_font = ImageFont.truetype(caption_font_path, title_size)
    badge = f"Ref: {ref}"
    badge_width = draw.textlength(badge, font=badge_font) + 42 * scale
    x, y = max(14, round(28 * scale)), max(14, round(28 * scale))
    badge_height = max(52, round(78 * scale))
    draw.rounded_rectangle((x, y, x + badge_width, y + badge_height), radius=9, fill="#c51b24")
    draw.text((x + badge_width / 2, y + badge_height / 2 + 4 * scale), badge, font=badge_font, anchor="mm", fill="white")
    tag_font = badge_font
    tag_width = draw.textlength("3D", font=tag_font) + 38 * scale
    tag_height = badge_height
    tag_x = width - x - tag_width
    draw.rounded_rectangle((tag_x, y, width - x, y + tag_height), radius=9, fill="#ff4f1f")
    draw.text((tag_x + tag_width / 2, y + tag_height / 2), "3D", font=tag_font, anchor="mm", fill="white")
    logo_font = ImageFont.truetype(caption_font_path, max(18, round(28 * scale)))
    logo_width = max(tag_width, draw.textlength("360°", font=logo_font) + 24 * scale)
    logo_height = max(36, round(54 * scale))
    logo_right = width - x
    logo_top = y + tag_height + 12 * scale
    draw.rounded_rectangle((logo_right - logo_width, logo_top, logo_right, logo_top + logo_height),
                           radius=round(logo_height / 2), fill="#078fa9", outline="white", width=max(1, round(2 * scale)))
    draw.text((logo_right - logo_width / 2, logo_top + logo_height / 2), "360°",
              font=logo_font, anchor="mm", fill="white")
    if price:
        price = price.removeprefix("₺").strip() + " TL" if price.startswith("₺") else price
        price_font_path = os.environ.get("PORTFOLIO_PRICE_FONT")
        if not price_font_path or not Path(price_font_path).is_file():
            raise ImportError_("Poppins ExtraBold fiyat fontu bulunamadı.")
        price_size = max(25, round(68 * scale))
        price_font = ImageFont.truetype(price_font_path, price_size)
        while draw.textlength(price, font=price_font) > width - 2*x and price_size > 16:
            price_size -= 1
            price_font = ImageFont.truetype(price_font_path, price_size)
        from PIL import ImageFilter
        shadow = Image.new("RGBA", result.size)
        ImageDraw.Draw(shadow).text((x + max(2, round(3*scale)), height - x + max(2, round(3*scale))), price, font=price_font, anchor="ls", fill=(0,0,0,240), stroke_width=max(2,round(3*scale)), stroke_fill=(0,0,0,220))
        result.paste(shadow.filter(ImageFilter.GaussianBlur(max(1,round(2*scale)))), (0,0), shadow.filter(ImageFilter.GaussianBlur(max(1,round(2*scale)))).getchannel("A"))
        draw = ImageDraw.Draw(result)
        draw.text((x, height - x), price, font=price_font, anchor="ls", fill="#ffffff")
    draw.text((x, height + band / 2), title, font=title_font, anchor="lm", fill="#292929")
    output = io.BytesIO()
    for quality in (82, 74, 65, 55):
        output.seek(0)
        output.truncate()
        result.save(output, "JPEG", quality=quality, optimize=True)
        if output.tell() <= 300_000:
            break
    return output.getvalue(), result.size


def share_page(base_url, ref, title, image_url, dimensions, revision):
    esc = lambda value: html.escape(str(value), quote=True)
    share_url = f"{base_url}/program/share/ref-{ref}.html?v={revision}"
    description = "3D ve 360° interaktif gayrimenkul sunumu"
    return f'''<!doctype html>
<html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Ref: {esc(ref)} | {esc(title)}</title>
<link rel="canonical" href="{esc(share_url)}">
<meta name="description" content="{esc(description)}">
<meta property="og:type" content="website"><meta property="og:url" content="{esc(share_url)}">
<meta property="og:title" content="Ref: {esc(ref)} | {esc(title)}">
<meta property="og:description" content="{esc(description)}">
<meta property="og:image" content="{esc(image_url)}"><meta property="og:image:secure_url" content="{esc(image_url)}">
<meta property="og:image:type" content="image/jpeg"><meta property="og:image:width" content="{dimensions[0]}"><meta property="og:image:height" content="{dimensions[1]}">
<meta property="og:image:alt" content="{esc(title)}">
<meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="Ref: {esc(ref)} | {esc(title)}"><meta name="twitter:image" content="{esc(image_url)}">
</head><body style="margin:0;overflow:hidden"><iframe title="{esc(title)} · 3D sunum" src="../?villa=ref-{esc(ref)}&amp;ui=c710b1b" allow="autoplay; fullscreen" allowfullscreen style="display:block;width:100%;height:100vh;height:100dvh;border:0"></iframe></body></html>
'''


def prepare(drive, folder, config, ref="", location="", details="", base_url="", font_path="", prices=None):
    """Return an in-memory plan; callers write nothing until every file validates."""
    fid, key = folder_id(folder)
    if hasattr(drive, "resource_keys"):
        drive.resource_keys[fid] = key
    root = drive.metadata(fid)
    if root.get("mimeType") != FOLDER:
        raise ImportError_("Bağlantı bir Drive klasörüne ait olmalı.")
    match = re.match(r"^(\d{1,10}[vd]?)\s*[-_ ]+(.+)$", root["name"], re.I)
    ref = (ref.strip() or (match.group(1) if match else "")).lower()
    if not re.fullmatch(r"\d{1,10}[vd]?", ref):
        raise ImportError_("Ref 057v (villa) veya 057d (daire) biçiminde olmalı.")
    if ref[-1:].isdigit():
        words = normalize(root["name"] + " " + location + " " + details).split("-")
        kinds = set()
        if "villa" in words:
            kinds.add("v")
        if "daire" in words:
            kinds.add("d")
        if len(kinds) != 1:
            raise ImportError_("Tür belirlenemedi. Ref alanına villa için 057v, daire için 057d gibi açık bir değer yazın.")
        ref += kinds.pop()
    folder_name = f"ref-{ref}"
    config = copy.deepcopy(config)
    config.setdefault("models", {})
    villas = config.setdefault("villas", {})
    for name, spec in list(villas.items()) + list(config["models"].items()):
        if str(spec.get("ref", "")) == ref and name != folder_name:
            raise ImportError_("Bu Ref başka bir kayıt tarafından kullanılıyor.")
    previous = villas.get(folder_name, {})
    if previous.get("driveFolderId") not in (None, fid):
        raise ImportError_("Bu Ref farklı bir Drive klasörüne bağlı; kaynak eşleşmesini kontrol edin.")
    title = location.strip() or previous.get("location") or (match.group(2) if match else root["name"])
    details = details.strip() or previous.get("details", "")
    display = title + (" · " + details if details else "")
    record = copy.deepcopy(previous)
    record.update(ref=ref, location=title, details=details, driveFolderId=fid)
    floors = record.setdefault("floors", {})
    pending, warnings = {}, []
    children = drive.children(fid)
    glb_folder = choose(children, lambda f: f["mimeType"] == FOLDER and normalize(f["name"]).split("-")[-1] == "glb", "GLB klasörü")
    models = [f for f in (drive.children(glb_folder["id"]) if glb_folder else children) if Path(f["name"]).suffix.lower() == ".glb"]
    if not models:
        raise ImportError_("GLB modeli bulunamadı. glb/ klasörüne kat modellerini ekleyin.")
    if len(models) > 50:
        raise ImportError_("Tek portföy için en fazla 50 model destekleniyor.")
    model_names, keys = {}, {}
    for item in models:
        name = normalize(Path(item["name"]).stem) + ".glb"
        if name in model_names.values() or floor_key(name) in keys:
            raise ImportError_("Aynı kata karşılık gelen birden fazla GLB var.")
        data = drive.download(item, 90 * 1024 * 1024)
        validate_glb(data)
        pending[f"program/{folder_name}/{name}"] = data
        model_names[item["id"]] = name
        keys[floor_key(name)] = name
        floors.setdefault(name, {})["driveModelId"] = item["id"]
    cover_item = choose(children, lambda f: normalize(Path(f["name"]).stem) in ("kapak", "cover") and Path(f["name"]).suffix.lower() in IMAGE_EXT, "kapak fotoğrafı")
    if not cover_item:
        cover_item = choose(children, lambda f: Path(f["name"]).suffix.lower() in IMAGE_EXT, "kapak fotoğrafı")
    if cover_item:
        from video_links import typed_ref, format_price
        price = format_price((prices or {}).get(typed_ref(ref, ref[-1]), ""))
        cover_data, dimensions = cover(image_bytes(drive.download(cover_item, 30 * 1024 * 1024)), ref, display, font_path, price)
        digest = hashlib.sha256(cover_data).hexdigest()[:12]
        image_path = f"covers/{ref}-{digest}.jpg"
        pending["program/" + image_path] = cover_data
        record["coverImage"] = "./" + image_path
        record["sharePath"] = f"./share/ref-{ref}.html?v={digest}"
        pending[f"program/share/ref-{ref}.html"] = share_page(base_url, ref, display, base_url + "/program/" + image_path, dimensions, digest).encode()
        for alias in record.get("legacyFolders", []):
            if re.fullmatch(r"ref-\d{1,10}[vd]?", alias):
                pending[f"program/share/{alias}.html"] = pending[f"program/share/ref-{ref}.html"]
    elif not record.get("coverImage"):
        warnings.append("Kapak fotoğrafı yok; WhatsApp kapağı hazırlanmadı.")
    music = choose(children, lambda f: normalize(Path(f["name"]).stem) in ("muzik", "music") and Path(f["name"]).suffix.lower() == ".mp3", "müzik dosyası")
    if not music:
        music = choose(children, lambda f: Path(f["name"]).suffix.lower() == ".mp3", "müzik dosyası")
    if music:
        data = drive.download(music, 60 * 1024 * 1024)
        if not (data.startswith(b"ID3") or (len(data) > 1 and data[0] == 255 and data[1] & 224 == 224)):
            raise ImportError_("MP3 dosyası doğrulanamadı.")
        digest = hashlib.sha256(data).hexdigest()[:12]
        path = f"audio/{ref}-{digest}.mp3"
        pending["program/" + path] = data
        record["musicUrl"] = "./" + path
    photo_root = choose(children, lambda f: f["mimeType"] == FOLDER and normalize(f["name"]).split("-")[-1] in ("foto", "360", "fotograflar"), "fotoğraf klasörü")
    groups = []
    if photo_root:
        photos = drive.children(photo_root["id"])
        direct = [f for f in photos if Path(f["name"]).suffix.lower() in IMAGE_EXT]
        if direct:
            if len(models) != 1:
                raise ImportError_("Fotoğrafları foto/bodrum, foto/zemin, foto/1-kat gibi katlara ayırın.")
            groups.append((next(iter(model_names.values())), direct))
        seen_floors = set()
        for sub in photos:
            if sub["mimeType"] != FOLDER:
                continue
            name = keys.get(floor_key(sub["name"]))
            if not name:
                warnings.append(f"Kat modeliyle eşleşmeyen fotoğraf klasörü atlandı: {sub['name']}")
                continue
            if name in seen_floors:
                raise ImportError_("Aynı kat için birden fazla fotoğraf klasörü var.")
            seen_floors.add(name)
            groups.append((name, drive.children(sub["id"])))
    imported_photos = 0
    for name, items in groups:
        floor = floors[name]
        photos = copy.deepcopy(floor.get("panoramaPhotos", []))
        panos = copy.deepcopy(floor.get("panoramas", []))
        seen_names = set()
        for item in items:
            if Path(item["name"]).suffix.lower() not in IMAGE_EXT:
                continue
            source_name = item["name"].casefold()
            if source_name in seen_names:
                raise ImportError_("Aynı kat klasöründe aynı adlı fotoğraflar var.")
            seen_names.add(source_name)
            image = image_bytes(drive.download(item, 40 * 1024 * 1024))
            if abs(image.width / image.height - 2) > 0.04:
                warnings.append(f"360 oranında olmayan normal fotoğraf atlandı: {item['name']}")
                continue
            image.thumbnail((4096, 2048), Image.Resampling.LANCZOS)
            out = io.BytesIO()
            image.save(out, "JPEG", quality=88, optimize=True)
            data = out.getvalue()
            digest = hashlib.sha256(data).hexdigest()[:12]
            path = f"360/{ref}/{normalize(Path(name).stem)}/{item['id']}-{digest}.jpg"
            pending["program/" + path] = data
            old = next((p for p in photos if p.get("id") == item["id"] or p.get("sourceName", "").casefold() == source_name), None)
            old_id = old.get("id") if old else item["id"]
            photo = {"id": item["id"], "sourceName": item["name"], "title": Path(item["name"]).stem, "url": "./" + path, "thumbnailUrl": "./" + path}
            photos = [p for p in photos if p is not old]
            photos.append(photo)
            for pano in panos:
                if pano.get("driveFileId") in (item["id"], old_id):
                    pano.update(driveFileId=item["id"], url=photo["url"], thumbnailUrl=photo["url"], title=photo["title"])
            imported_photos += 1
        floor["panoramaPhotos"], floor["panoramas"] = photos, panos
    mapping = choose(children, lambda f: f["name"].lower() == "isaretler.json" or f["name"].lower().endswith("-ok-ve-360-konumlari.json"), "işaret konumu dosyası")
    if mapping:
        try:
            positions = json.loads(drive.download(mapping, 2 * 1024 * 1024))
        except (ValueError, UnicodeError):
            raise ImportError_("İşaret dosyası geçerli JSON değil.") from None
        if positions.get("villa") not in [folder_name, *record.get("legacyFolders", [])]:
            raise ImportError_(f"İşaret dosyası bu portföy için olmalı: {folder_name}")
        for floor_name, specs in positions.get("floors", {}).items():
            if floor_name not in floors:
                raise ImportError_(f"İşaret dosyasında bilinmeyen kat: {floor_name}")
            floor = floors[floor_name]
            available = {p["id"]: p for p in floor.get("panoramaPhotos", [])}
            markers = []
            for spec in specs.get("panoramas", []):
                photo = available.get(spec.get("driveFileId"))
                if not photo:
                    raise ImportError_("İşaretin bağlı olduğu 360 fotoğraf bulunamadı.")
                marker = {"driveFileId": photo["id"], "title": photo["title"], "url": photo["url"], "thumbnailUrl": photo["thumbnailUrl"], "position": vector(spec.get("position"), "360 konumu")}
                for field in ("initialYaw", "initialPitch"):
                    if field in spec:
                        if type(spec[field]) not in (int, float) or not math.isfinite(spec[field]):
                            raise ImportError_("360 bakış açısı geçersiz.")
                        marker[field] = spec[field]
                markers.append(marker)
            floor["panoramas"] = markers
            for field in ("entranceArrow", "stairArrows"):
                if field not in specs:
                    continue
                arrows = specs[field] if field == "stairArrows" else ([specs[field]] if specs[field] else [])
                clean = []
                for arrow in arrows:
                    result = {"position": vector(arrow.get("position"), "ok konumu"), "direction": vector(arrow.get("direction"), "ok yönü")}
                    for prop in ("length", "moveAmount"):
                        if prop in arrow:
                            value = arrow[prop]
                            if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
                                raise ImportError_("Ok boyutu geçersiz.")
                            result[prop] = value
                    clean.append(result)
                floor[field] = clean if field == "stairArrows" else (clean[0] if clean else None)
    unplaced = sum(len({p["id"] for p in f.get("panoramaPhotos", [])} - {p.get("driveFileId") for p in f.get("panoramas", [])}) for f in floors.values())
    villas[folder_name] = record
    pending["program/config/portfolios.json"] = (json.dumps(config, ensure_ascii=False, indent=2) + "\n").encode()
    summary = {"ref": ref, "models": len(models), "photos360": imported_photos, "unplaced": unplaced, "warnings": warnings,
               "viewer": base_url + "/program/?villa=" + folder_name,
               "share": base_url + "/program/" + record.get("sharePath", "./").removeprefix("./"),
               "editor": base_url + "/program/arrow-editor.html?villa=" + folder_name}
    if sum(map(len, pending.values())) > 400 * 1024 * 1024:
        raise ImportError_("Tek aktarım için 400 MB sınırı aşıldı.")
    return pending, summary


def refresh_other_covers(drive, root, pending, catalog, imported_ref, base_url, font_path):
    """Refresh changed prices on existing Drive-backed portfolios without reimporting models."""
    from video_links import typed_ref, format_price
    root = Path(root)
    config = json.loads(pending["program/config/portfolios.json"])
    previous_path = root / "program/config/video-links.json"
    previous = json.loads(previous_path.read_text(encoding="utf-8")).get("prices", {}) if previous_path.exists() else {}
    prices = catalog.get("prices", {})
    for record in config.get("villas", {}).values():
        ref = str(record.get("ref", ""))
        if ref == imported_ref or not re.fullmatch(r"\d+[vd]", ref) or not record.get("driveFolderId"):
            continue
        key = typed_ref(ref, ref[-1])
        price = format_price(prices.get(key, ""))
        if price == format_price(previous.get(key, "")):
            continue
        children = drive.children(record["driveFolderId"])
        item = choose(children, lambda f: normalize(Path(f["name"]).stem) in ("kapak", "cover") and Path(f["name"]).suffix.lower() in IMAGE_EXT, "kapak fotoğrafı")
        if not item:
            item = choose(children, lambda f: Path(f["name"]).suffix.lower() in IMAGE_EXT, "kapak fotoğrafı")
        if not item:
            if record.get("coverImage"):
                raise ImportError_("Fiyatı değişen portföyün kaynak kapağı bulunamadı: " + ref)
            continue
        title = record.get("location", "") + (" · " + record["details"] if record.get("details") else "")
        data, dimensions = cover(image_bytes(drive.download(item, 30 * 1024 * 1024)), ref, title, font_path, price)
        digest = hashlib.sha256(data).hexdigest()[:12]
        path = f"covers/{ref}-{digest}.jpg"
        pending["program/" + path] = data
        record["coverImage"] = "./" + path
        record["sharePath"] = f"./share/ref-{ref}.html?v={digest}"
        page = share_page(base_url, ref, title, base_url + "/program/" + path, dimensions, digest).encode()
        pending[f"program/share/ref-{ref}.html"] = page
        for alias in record.get("legacyFolders", []):
            if re.fullmatch(r"ref-\d{1,10}[vd]?", alias):
                pending[f"program/share/{alias}.html"] = page
    pending["program/config/portfolios.json"] = (json.dumps(config, ensure_ascii=False, indent=2) + "\n").encode()


def apply_plan(root, pending):
    root = Path(root).resolve()
    for relative in pending:
        target = (root / relative).resolve()
        if not target.is_relative_to(root / "program") or ".." in Path(relative).parts:
            raise ImportError_("Güvenli olmayan dosya yolu.")
    changed = []
    for relative, data in pending.items():
        target = root / relative
        if target.exists() and target.read_bytes() == data:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        changed.append(relative)
    return changed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--folder", required=True)
    parser.add_argument("--ref", default="")
    parser.add_argument("--location", default="")
    parser.add_argument("--details", default="")
    parser.add_argument("--root", default=".")
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--font", default="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
    args = parser.parse_args()
    try:
        config = json.loads((Path(args.root) / "program/config/portfolios.json").read_text(encoding="utf-8"))
        from video_links import sync_drive_catalog, read_drive_catalog
        drive = Drive(os.environ.get("GOOGLE_DRIVE_API_KEY", ""))
        catalog = read_drive_catalog(drive, args.root)
        pending, result = prepare(drive, args.folder, config,
                                  args.ref, args.location, args.details, args.base_url.rstrip("/"), args.font, prices=(catalog or {}).get("prices", {}))
        if catalog:
            refresh_other_covers(drive, args.root, pending, catalog, result["ref"], args.base_url.rstrip("/"), args.font)
        result["catalogSynced"] = sync_drive_catalog(drive, args.root, pending, catalog=catalog)
        result["changed"] = len(apply_plan(args.root, pending))
        Path("import-result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Ref {result['ref']}: {result['models']} model, {result['photos360']} adet 360 fotoğraf; {result['unplaced']} fotoğraf konum bekliyor.")
        for warning in result["warnings"]:
            print("UYARI: " + warning)
    except (ImportError_, KeyError, TypeError, OSError, ValueError) as error:
        # Never echo a URL containing credentials or an authenticated provider response.
        print("AKTARIM DURDU: " + str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

