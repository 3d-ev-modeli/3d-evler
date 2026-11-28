"""Make a Pages artifact without exposing tests, tools, backups or git internals."""
from pathlib import Path
import shutil

root = Path.cwd()
site = root / "_site"
site.mkdir(exist_ok=True)
shutil.copy2(root / "index.html", site / "index.html")
shutil.copytree(root / "program", site / "program", dirs_exist_ok=True,
                ignore=shutil.ignore_patterns("tools", "tests", "__pycache__", "index-orijinal-yedek-referans.html", "*.pyc"))
(site / ".nojekyll").touch()

# Generate a fresh isolated share URL with its own cover image.
share = site / "program" / "share"
template = share / "test-064v-tl.html"
cover = share / "test-064v-3kat.jpg"
if template.is_file() and cover.is_file():
    name = "test-064v-kapak-4"
    shutil.copy2(cover, share / (name + ".jpg"))
    html = template.read_text(encoding="utf-8")
    html = html.replace("test-064v-tl.html", name + ".html")
    html = html.replace("test-064v-3kat.jpg", name + ".jpg")
    html = html.replace("player=3", "player=4")
    (share / (name + ".html")).write_text(html, encoding="utf-8")
