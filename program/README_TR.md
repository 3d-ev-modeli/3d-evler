# 3D Ev Turu

Tüm uygulama dosyaları bu program/ klasöründedir. Depo kökündeki index.html yalnızca burayı açar. Yeni model ve portföy klasörlerini program/ içinde oluşturun. Ana site: https://3d-ev-modeli.github.io/3d-evler/ .

Program, yeni portföylerin eklenmesi için temiz durumdadır. Deneme portföyleri ve onlara ait model, kapak, müzik ve paylaşım sayfaları kaldırılmıştır.

## Program dosyaları

- index.html: 3D görüntüleyici, kat seçimi, 360 fotoğraf işaretleri ve ilk ekran etkileşiminde müzik başlatma.
- arrow-editor.html: model üzerindeki işaret ve ok konumlarını düzenleme aracı.
- config/portfolios.json: portföy ayarları; şu anda boş.
- share/template.html: yeni portföy paylaşım sayfaları için şablon.
- preview.png: genel program önizlemesi.
- index-orijinal-yedek-referans.html: programın önceki referans yedeği.

## Yeni portföy

1. Model dosyalarını (.glb) ekleyin. Çok katlı portföylerde her katı portföy klasörüne koyun.
2. Gerçek model/klasör adını config/portfolios.json içindeki models veya villas alanına ekleyin.
3. Kapak görselini covers, müziği audio, 360 fotoğrafları 360 altında ilgili portföye ayırın.
4. Portföye özel musicUrl, coverImage ve sharePath değerlerini tanımlayın.
5. 360 fotoğrafları ilgili katın panoramas listesine ekleyin. Model üzerindeki işaretler için gerçek position koordinatları gerekir.
6. Yeni paylaşım sayfasını hazırlayıp WhatsApp önizlemesini test edin.

Müzik ilk kullanıcı etkileşiminde başlamayı dener ve döngüde çalar.
Program internet üzerinden kullanılan Three.js ve GitHub dosya listesine ihtiyaç duyar; dosyaya çift tıklamak yerine yayımlanan siteyi kullanın.

## Drive'dan komutla aktarım

GitHub Actions içinde “Portföyü Drive'dan aktar” işlemi eklenmiştir. Drive klasör bağlantısı girilerek kapak, müzik, kat modelleri ve 360 fotoğraflar alınabilir.

Bir defalık GOOGLE_DRIVE_API_KEY ayarı tamamlanmalıdır. Kullanım ve 360 işaret eşleştirmesi için [DRIVE_KULLANIM.md](DRIVE_KULLANIM.md) dosyasını okuyun. İşlem kendiliğinden klasör izlemez; her güncellemede GitHub'dan komut verilmelidir.

Yeni 360 fotoğrafların model üzerindeki yeri ilk seferde düzenleyicide belirlenip isaretler.json ile aktarılır. Dosya kimliği veya aynı kat içindeki dosya adı korunduğunda mevcut konum korunur.

Temizlik Drive dosyalarını veya Git geçmişini silmez.
