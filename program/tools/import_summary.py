import html
import json
import os
from pathlib import Path

data = json.loads(Path("import-result.json").read_text(encoding="utf-8"))
esc = lambda text: html.escape(str(text))
lines = [f"## Ref {esc(data['ref'])} aktarıldı", "",
         f"- Model: {data['models']}", f"- 360 fotoğraf: {data['photos360']}",
         f"- Konum bekleyen 360 fotoğraf: {data['unplaced']}",
         f"- Değişen dosya: {data['changed']}", "",
         f"[3D sunumu aç]({data['viewer']})", "",
         f"[Paylaşım bağlantısı]({data['share']})", "",
         f"[İşaretleri düzenle]({data['editor']})", "",
         "İşareti bulunmayan yeni 360 fotoğraflar, modelde konumları seçilene kadar görüntüleyicide görünmez.", "",
         "Yeni işaretleri düzenleyicide yerleştirip konum dosyasını indirin. Drive portföy ana klasörüne isaretler.json olarak koyun ve aktarımı yeniden çalıştırın."]
lines += ["", "### Uyarılar"] + ["- " + esc(warning) for warning in data["warnings"]] if data["warnings"] else []
with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as stream:
    stream.write("\n".join(lines) + "\n")
