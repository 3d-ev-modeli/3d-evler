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
