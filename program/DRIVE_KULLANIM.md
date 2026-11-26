# Drive'dan portföy aktarımı

Bu sistem, GitHub Actions ekranından verdiğiniz komutla tek bir Drive portföy klasörünü alır. Sürekli klasör izlemesi yapmaz.

## Bir defalık kurulum

1. Google Cloud Console'da bir proje seçin veya oluşturun. Google Drive API'yi etkinleştirin.
2. Bu proje için bir API anahtarı oluşturun. Anahtarın API kısıtlamasını yalnızca Google Drive API olarak ayarlayın. Anahtarı paylaşım sayfasına, dosyaya veya sohbete yazmayın.
3. GitHub deposunda Settings → Secrets and variables → Actions → New repository secret açın. Ad: GOOGLE_DRIVE_API_KEY. Değer: Google'da oluşturduğunuz anahtar.
4. GitHub Settings → Pages → Build and deployment → Source değerini GitHub Actions yapın.
5. Portföy klasörü ve kullanılacak alt dosyalar Drive'da “Bağlantıya sahip herkes – Görüntüleyici” erişimine açık olmalıdır. API anahtarı özel Drive dosyalarınıza erişim vermez.

## Dosyaları yerleştirme

```text
057-Gürpınar 6+1 Müstakil Villa/
  glb/
    bodrum.glb
    zemin.glb
    1-kat.glb
  foto/
    bodrum/
      salon.jpg
    zemin/
      salon.jpg
    1-kat/
      oda.jpg
  kapak.jpg
  muzik.mp3
  isaretler.json  (ilk işaret yerleştirmesinden sonra)
```

“057-... - glb” ve “057-... - foto” gibi uzun klasör adları da desteklenir. Kat adlarında “bodrum kat”, “zemin kat”, “1. kat” kullanılabilir. Birden fazla dosya aynı kata karşılık gelmemelidir.

Kapağı kapak.jpg, kapak.png veya cover.jpg olarak adlandırın. Ana klasörde tek bir fotoğraf varsa mevcut adı da kabul edilir. Müzikte de muzik.mp3/music.mp3 tercih edilir; yalnızca bir MP3 varsa adı değişmeden kullanılabilir. Birden fazla aday varsa işlem seçim yapmadan durur.

GLB dosyaları tüm dokularını içinde barındırmalıdır. Her model en fazla 90 MB, MP3 60 MB, kapak 30 MB, 360 kaynak fotoğrafı 40 MB; toplam aktarım en fazla 400 MB olabilir. Normal fotoğraflar bu aşamada galeriye alınmaz. 360 fotoğrafları equirectangular 2:1 olmalıdır; diğer oranlar uyarıyla atlanır.

## Aktarımı başlatma

1. GitHub → Actions → Portföyü Drive'dan aktar → Run workflow.
2. Branch: main.
3. Drive klasör bağlantısını yapıştırın. Örnek: https://drive.google.com/drive/folders/...
4. Ref isteğe bağlıdır; verilmezse klasör adının başındaki 057 alınır. Baştaki sıfır korunur.
5. Konum/başlık ve detay alanlarını doldurabilirsiniz. Boşsa klasör adı kullanılır; mevcut kayıtta önceki başlık korunur.
6. Run workflow düğmesine basın. Yeşil tamamlandı işaretinden sonra iş özetindeki sunum ve paylaşım bağlantılarını kullanın.

Sonuçlar program/ref-057, program/covers, program/audio, program/360 ve program/share altında oluşturulur. Program dosyaları değiştirilmez. Kapak fotoğrafı kesilmez; bahçe ve zemin korunur. Sol üstte kırmızı Ref etiketi, altta büyük portföy adı bulunur. Müzik portföye özeldir ve sunuma ilk dokunuşta başlar.

## 360 fotoğrafı işarete bağlama

Yeni bir fotoğrafın oda içindeki konumu dosyadan tahmin edilmez. İlk aktarımda fotoğraflar işaret düzenleyicisinin listesine alınır. Görüntüleyicide sadece gerçek konumu tanımlanmış fotoğrafların işaretleri görünür.

1. Aktarım özetindeki “İşaretleri düzenle” bağlantısını açın.
2. Katı ve fotoğrafı seçip model üzerinde gerçek yerini işaretleyin. Gerekiyorsa okları da düzenleyin.
3. Konumları JSON olarak indirin.
4. İndirilen dosyayı Drive portföy ana klasörüne isaretler.json adıyla koyun.
5. Aynı aktarımı yeniden çalıştırın. Fotoğraflar işaretlerine bağlanır.

Mevcut Drive dosyasını “Yeni sürüm yükle” ile değiştirmek dosya kimliğini korur. Aynı kat içinde aynı dosya adıyla değiştirmek de önceki işaret konumunu korur. Hem adı hem dosya kimliği değişirse yeni fotoğraf sayılır ve tekrar eşleştirilir.

## Güncelleme ve hata davranışı

- Aynı klasörü yeniden aktarabilirsiniz. Değişmeyen dosyalar tekrar kaydedilmez.
- Yeni kaynak kimliği aynı Ref'i sessizce devralamaz; işlem durur.
- Eksik klasör/bozuk dosya durumunda siteye yeni commit yayınlanmaz.
- Drive'dan silinen dosyalar ve önceki sürümler GitHub'dan otomatik silinmez. Silme ayrı bir işlemdir.
- Bir fotoğraf yalnızca normal fotoğraf olduğu için kendiliğinden 360 işaretine dönüşmez.
- Paylaşım sayfası adresi sunum açılırken değişmez. WhatsApp önizlemesinin oluşturulması ayrıca WhatsApp'ın bağlantıyı yüklemesine bağlıdır.
- Google Drive anahtarı veya Pages ayarı eksikse kurulum tamamlanmış sayılmaz. Bir gerçek klasör aktarımı ve yayın başarıyla sonuçlanmadan sistemi çalışır kabul etmeyin.

## Portföyü silme

GitHub → Actions → Portföyü sil → Run workflow açın. Branch olarak main seçin. Silinecek Ref numarasını hem reference hem confirmation alanına aynı şekilde, baştaki sıfırlarla yazın (ör. 057). İşlem seçilen portföyün kaydını, modellerini, kapaklarını, müziklerini, 360 dosyalarını ve paylaşım sayfalarını siteden kaldırır ve siteyi yeniden yayınlar. Başka bir portföy aynı varlığı kullanıyorsa inceleme için durur. Drive dosyaları ve program kodu silinmez. Önceki dosyalar Git geçmişinde kalır. Bu işlem için Google API anahtarı gerekmez.

## Kaynaklar

- Google'ın açık klasörleri API anahtarıyla listeleme belgesi: https://developers.google.com/workspace/drive/api/guides/search-files
- GitHub Pages özel iş akışları: https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages
