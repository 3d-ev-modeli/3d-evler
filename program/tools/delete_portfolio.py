"""Remove one imported portfolio; never touch Drive or shared program files."""
import argparse
import copy
import json
import os
from pathlib import Path
import re
import shutil
import sys


def deletion_plan(root, config, reference, confirmation):
    reference, confirmation = reference.lower(), confirmation.lower()
    if not re.fullmatch(r"[0-9]{1,10}[vd]?", reference) or reference != confirmation:
        raise ValueError("Ref ve onay alanına aynı numarayı, baştaki sıfırlarla birlikte yazın.")
    root = Path(root).resolve()
    program = root / "program"
    if program.is_symlink():
        raise ValueError("Program klasörü bağlantı olamaz; işlem durdu.")
    result = copy.deepcopy(config)
    found = []
    for section in ("villas", "models"):
        for key, value in list(result.get(section, {}).items()):
            if str(value.get("ref", "")) == reference:
                if not re.fullmatch(r"ref-[0-9]{1,10}[vd]?", key):
                    raise ValueError("Bu eski kayıt otomatik silme biçiminde değil; dosyalar incelenmeli.")
                found.append(key)
                legacy = value.get("legacyFolders", [])
                del result[section][key]
    if not found:
        raise ValueError("Bu Ref ile kayıtlı portföy bulunamadı; hiçbir dosya silinmedi.")
    if len(found) != 1 or found[0] != "ref-" + reference:
        raise ValueError("Ref ve portföy klasörü eşleşmiyor; hiçbir dosya silinmedi.")
    aliases = [name for name in legacy if re.fullmatch(r"ref-[0-9]{1,10}", name)]
    if any(name[4:] != reference.rstrip("vd") for name in aliases):
        raise ValueError("Eski Ref eşleşmesi geçersiz; işlem durdu.")
    references = [reference] + [name[4:] for name in aliases]
    paths = [program / found[0]] + [program / name for name in aliases]
    paths += [program / "360" / ref for ref in references]
    for directory in ("covers", "audio"):
        base = program / directory
        if base.exists():
            paths += [p for p in base.iterdir() if p.is_file() and any(p.name.startswith(ref + "-") or p.stem == ref for ref in references)]
    paths += [program / "share" / f"{prefix}-{ref}.html" for ref in references for prefix in ("ref", "villa")]
    for path in paths:
        if path.is_symlink() or not path.resolve().is_relative_to(program.resolve()):
            raise ValueError("Güvenli olmayan dosya yolu; işlem durdu.")
    # A different portfolio may deliberately reuse an asset. Keep those files.
    protected = set()
    for section in ("villas", "models"):
        for record in result.get(section, {}).values():
            def visit(value):
                if isinstance(value, dict):
                    for item in value.values():
                        visit(item)
                elif isinstance(value, list):
                    for item in value:
                        visit(item)
                elif isinstance(value, str) and value.startswith("./"):
                    protected.add((program / value[2:].split("?")[0]).resolve())
            visit(record)
    for path in paths:
        if any(other == path.resolve() or other.is_relative_to(path.resolve()) for other in protected):
            raise ValueError("Bu portföyün bir dosyasını başka kayıt da kullanıyor; işlem incelenmeli.")
    return result, [path for path in paths if path.exists()]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ref", required=True)
    parser.add_argument("--confirm", required=True)
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    try:
        root = Path(args.root)
        cfg_path = root / "program/config/portfolios.json"
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        cfg, paths = deletion_plan(root, cfg, args.ref, args.confirm)
        for path in paths:
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
        cfg_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        text = f"Ref {args.ref} siteden kaldırıldı. Program ve Drive dosyaları korunuyor.\n"
        print(text)
        if os.environ.get("GITHUB_STEP_SUMMARY"):
            with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as stream:
                stream.write(text)
    except (ValueError, OSError) as error:
        print("SİLME DURDU: " + str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
