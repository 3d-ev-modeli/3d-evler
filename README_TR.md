# 3D Ev Turu – Güncelleme paketi

Bu paket, mevcut `index.html` dosyasını temel alır. Var olan GLB görüntüleyicisini korur ve aşağıdaki eklemeleri getirir:

- REF etiketi tek satırda, kırmızı zeminli.
- Portföye özel başlık, kapak görseli yolu ve WhatsApp paylaşım sayfası ayarı.
- Müzik düğmesi. Tarayıcıların otomatik ses kısıtlaması nedeniyle müzik kendiliğinden başlamaz; müşteri düğmeye dokunarak başlatır.
- Equirectangular 360° fotoğrafları gösterme ve istenirse model içinde konumlandırılmış 360 işaretleri.
- Villa kat sırası: Bodrum → Zemin → 1. Kat → 2. Kat. İlk açılış, Zemin katı bulursa Zemin'den başlar.
- Zemin kat haricindeki villa katlarında çok açık pastel yansıma rengi.
- Kırmızı giriş oku ve yeşil merdiven okları için portföy/kat bazlı koordinat ayarı.

## GitHub'a yükleme

1. GitHub deposunda `3d-evler` ana klasörünü açın.
2. ZIP dosyasını bilgisayarınızda açın. İçindeki `3d-evler-yeni` klasörüne girin; klasörün kendisini değil, içindeki dosya ve alt klasörleri seçin.
3. GitHub'da `Add file → Upload files` bölümünü açın. Seçtiğiniz dosya ve klasörleri depo ana dizinine sürükleyin. Mevcut `index.html` için GitHub bir çakışma uyarısı verirse durun ve ekran görüntüsü gönderin; silme yapmayın.
4. `config`, `share`, `covers`, `audio` ve `360` klasör yapısının depo ana dizininde oluştuğunu kontrol edin.
5. Commit öncesinde daha önce indirdiğiniz eski `index.html` yedeği bilgisayarınızda kalsın.
6. Commit ettikten sonra önce ana sayfayı, sonra Ref 007 paylaşım bağlantısını test edin.

## Ref 007 kapak görseli ve WhatsApp önizlemesi

- `covers/007.jpg` dosyasını ekleyin. Önerilen görsel: 1200×630 piksel, JPG, yatay.
- WhatsApp'a gönderilecek bağlantı: `https://3d-ev-modeli.github.io/3d-evler/share/ref-007.html`
- Paylaşım sayfasındaki Open Graph bilgileri sabittir. WhatsApp, `index.html` içindeki JavaScript'i çalıştırmadan önce bu statik meta etiketlerini okur; bu nedenle her portföy için ayrı `share/*.html` sayfası gerekir.
- Yeni portföylerde `share/template.html` dosyasını kopyalayıp yeni REF adıyla kaydedin; içindeki başlık, açıklama, kapak URL'si ve görüntüleyici URL'sini o portföye göre değiştirin. Ardından aynı `sharePath` değerini `config/portfolios.json` içine yazın.

## Müzik

Kullanma hakkınız olan MP3 dosyasını `audio/background.mp3` adıyla yükleyin. Ardından `config/portfolios.json` içinde genel `musicUrl` alanını `"./audio/background.mp3"` yapın (veya yalnızca ilgili portföyün `musicUrl` alanını değiştirin). Ses, kullanıcı düğmeye basmadan başlamaz.

## 360° fotoğraflar

- Fotoğraflar equirectangular 2:1 panoramik JPG olmalıdır (ör. 6000×3000).
- En güvenilir yöntem, dosyaları `360/007/` gibi ilgili klasöre koyup JSON'da `"url": "./360/007/salon.jpg"` kullanmaktır.
- Google Drive kullanmak isterseniz dosya paylaşımını “Bağlantıya sahip herkes – Görüntüleyici” yapıp doğrudan görsel URL'sini `url` alanına girin. Ancak Drive yönlendirmeleri WebGL/Three.js için CORS engeline takılabilir; bağlantı tarayıcıda açılıyor olsa bile 360 küresine yüklenmeyebilir. Böyle olursa görseli GitHub'daki `360/` klasöründe barındırmak gerekir.
- `position` alanı fotoğrafın 3D modeldeki konumudur: `[x, y, z]`. Bu değerleri her portföy ve oda için bir kez kalibre etmek gerekir. Paket bilinmeyen koordinatları uydurmaz.
- `initialYaw` ve `initialPitch` panoramanın ilk bakış yönünü derece cinsinden ayarlar.

Örnek:

```json
"panoramas": [
  {
    "title": "Salon",
    "url": "./360/007/salon.jpg",
    "position": [0.8, 1.2, -1.4],
    "initialYaw": 90,
    "initialPitch": 0
  }
]
```

`position` değerleri örnektir; gerçek modelinize göre ayarlanmadan kullanılmamalıdır. `position` satırını kaldırırsanız fotoğraf, 360° düğmesiyle açılır ama model içinde işaretçi görünmez.

## Giriş ve merdiven okları

Koordinatlar, ortalanmış modelin merkezine göre `[x, y, z]` biçimindedir; zemin seviyesi yaklaşık `y=0` kabul edilir. Yön vektörü yatay olmalıdır. Kırmızı giriş oku yalnızca zemin kat ayarında `entranceArrow` ile; yeşil merdiven okları ilgili katın `stairArrows` listesiyle tanımlanır.

Örnek (koordinatlar temsili; gerçek modele göre ayarlanmalıdır):

```json
"entranceArrow": {
  "position": [0, 0.08, 1.2],
  "direction": [0, 0, -1],
  "moveAmount": 0.08
},
"stairArrows": [
  {
    "position": [1.1, 0.08, -0.7],
    "direction": [1, 0, 0],
    "moveAmount": 0.06
  }
]
```

Ekran görüntüsünde görünen villa klasörü `test villa` olduğu için örnek ayar bu adla başlatıldı. Depodaki klasör adı farklıysa JSON'daki anahtarı birebir değiştirin. Kat dosyası adlarını da `floors` altında GitHub'daki gerçek GLB dosya adlarıyla birebir eşleştirin.

## Önemli sınırlar

- Paket, model dosyalarına dokunmaz; GLB'leri yeniden üretmez.
- Giriş/merdiven oklarının ve 360 işaretlerinin gerçek konumları her modelde farklıdır; bunlar için koordinat kalibrasyonu gerekir.
- 360 fotoğraf ve müzik dosyaları bu pakette yer almaz; sizin yükleyeceğiniz dosyalara göre ayarlanır.
- WhatsApp önizleme görselinin görünmesi için `covers/007.jpg` dosyasının yüklenmiş olması gerekir. WhatsApp önbelleği nedeniyle eski görsel bir süre görünebilir.
