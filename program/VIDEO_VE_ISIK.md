# Video, Detay ve ışık karşılaştırması

Kaynak portfoyler.xlsx dosyasıdır. Villalar (veya Villa) sayfası v, Daireler (veya Daire) sayfası d ile eşleşir. Villalar sayfasındaki Foto (villa64 gibi), Daireler sayfasındaki No sütunu kullanılır. Yalnızca Video ve Detay sütunları okunur; Foto Video sütunu kullanılmaz. 064v ve 64v aynı kayıttır; 064d ayrı kayıttır.

Video veya Detay hücresi boşsa ilgili düğme gizlenir. Kaynak Excel'e yazılmaz. GitHub'a tüm çalışma kitabı kopyalanmaz; yalnızca yayındaki portföylerin Ref ve Video/Detay bağlantıları aktarılır. Aynı tür ve numara için farklı bağlantılar varsa aktarım durur.

## Drive kaynağı

program/config/catalog-source.json dosyasında driveFileId alanı kaynak XLSX dosyasının Drive kimliğini tutar. Gerekiyorsa resourceKey alanı da doldurulur. Kaynağa mevcut Drive API bağlantısının okuma erişimi olmalıdır. Kaynak kimliği boşken otomatik Excel okuma kapalıdır; kayıtlı video-links.json kullanılmaya devam eder.

Kaynak ayarlandıktan sonra her Portföyü Drive'dan aktar işleminde Excel yeniden okunur. Yeni veya silinen Video/Detay hücreleri program/config/video-links.json içinde güncellenir. Dosya okunamazsa veya eşleşme belirsizse yeni değişiklikler kaydedilmez.

Bu, sürekli arka plan izlemesi değildir. Excel'de değişiklikten sonra Drive kopyasının güncellendiğinden emin olun ve aktarımı çalıştırın. Masaüstü dosyasını değiştirmek Drive'daki eski kopyayı kendiliğinden değiştirmez.

## Yerel eşitleme

Drive kaynağı hazır değilse Python ile yalnızca gerekli bağlantıları eşitleyebilirsiniz:

```
python program/tools/video_links.py "C:\Users\msi\Desktop\portfoy katalog\portfoyler.xlsx" --portfolio-config program/config/portfolios.json --output program/config/video-links.json
```

Oluşan JSON'u GitHub'da aynı konuma yüklemek yayını günceller. Tam Excel'i GitHub'a yüklemeyin.

## Düğmeler

Detay yeşil, Video kırmızıdır. Video açılırken arka plan müziği durur. Google Drive ve YouTube bağlantıları oynatıcıda, MP4/WebM/OGV bağlantıları video öğesinde açılır. Diğer HTTPS bağlantılarında kaynak sayfasına bağlantı gösterilir. Drive videosunun izleyiciler tarafından açılabilmesi gerekir.

Video kapanınca makete yeniden dokunulduğunda müzik devam edebilir. Detay bağlantısı yeni sekmede açılır ve müzik durur. Herhangi bir bağlantı yoksa o düğme görünmez.

## Işık karşılaştırması

Sunum adresine compareLight=1 parametresi eklenince Mevcut ve Nötr düğmeleri görünür. Varsayılan Mevcut kalır. Karşılaştırmada otomatik kamera hareketi kapalıdır; maketi elle döndürebilirsiniz.

Mevcut önceki ek ışıkları aynen kullanır. Nötr ek yönlü ışıkları kapatır. Modelde gömülü ışık varsa onu kullanır; yoksa modeli karartmamak için tek nötr ortam ışığı kullanır. Zemin yansıması, kamera ve malzemeler iki seçenekte de korunur. Bu, Blender render motorunun birebir kopyası değildir.

Normal paylaşım bağlantıları aynı aydınlatmayla çalışır. compareLight=1 kaldırıldığında eski görünüm ve kamera hareketi geri gelir.
