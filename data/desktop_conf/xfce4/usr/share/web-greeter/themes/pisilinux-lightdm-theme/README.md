# Pisi Linux Web Greeter

Pisi Linux için modern ve kullanıcı dostu bir web greeter teması.

## Özellikler

- **Modern Arayüz**: Temiz ve minimalist tasarım
- **Kullanıcı Yönetimi**: Çoklu kullanıcı desteği
- **Oturum Seçimi**: Farklı masaüstü ortamları desteği
- **Sanal Klavye**: Dokunmatik ekranlar için klavye desteği
- **Çok Dilli Destek**: Türkçe ve İngilizce dil seçeneği
- **Responsive Tasarım**: Farklı ekran çözünürlüklerine uyum

## Kurulum

1. Pisi Linux'ta lightdm ve nody-greeter'i yükleyin:
   ```bash
   sudo pisi it lightdm
   sudo pisi it nody-greeter
   ```

2. Tema dosyalarını LightDM teması dizinine kopyalayın:
   ```bash
   sudo cp -r /path/to/pisi-theme /usr/share/web-greeter/themes/pisi
   ```

3. LightDM yapılandırma dosyasında temayı seçin:
   ```bash
   sudo nano /etc/lightdm/lightdm.conf
   ```
   
   Aşağıdaki satırları ekleyin/kontrol edin:
   ```
   [Seat:*]
   greeter-session=nody-greeter
   greeter-theme=pisi
   ```

4. LightDM'i yeniden başlatın:
   ```bash
   sudo systemctl restart lightdm
   ```

## Dosya Yapısı

```
pisi/
├── index.html              # Ana giriş sayfası
├── assets/
│   ├── css/
│   │   ├── main.css           # Ana stil dosyası
│   │   └── simple-keyboard.css # Sanal klavye stilleri
│   ├── js/
│   │   ├── main.js            # Ana JavaScript mantığı
│   │   └── simple-keyboard.js # Sanal klavye kütüphanesi
│   └── media/
│       ├── icons/             # Sistem ikonları
│       └── pisi-logo-magenta.png # Pisi logosu
└── README.md               # Bu dosya
```

## Teknik Özellikler

### LightDM Entegrasyonu
- `lightdm.authenticate()` ile kullanıcı doğrulaması
- `lightdm.respond()` ile şifre gönderimi
- `lightdm.login()` ile oturum başlatma
- `lightdm.start_session()` ile oturum yönetimi
- Callback fonksiyonları: `show_prompt`, `authentication_complete`

### JavaScript Kütüphaneleri
- **jQuery 3.7.1**: DOM manipülasyonu ve olay yönetimi
- **Simple Keyboard**: Sanal klavye desteği

### Tarayıcı Uyumluluğu
- Modern tarayıcılar (Chrome, Firefox, Edge, Safari)
- CSS Grid ve Flexbox desteği
- ES6+ JavaScript özellikleri

## Kullanım

1. **Giriş Yapma**:
   - Kullanıcı listesinden kullanıcı seçin
   - Şifre alanına parolanızı girin
   - Giriş Yap butonuna tıklayın veya Enter tuşuna basın

2. **Oturum Seçimi**:
   - Üst kısımdaki oturum dropdown'ından masaüstü ortamını seçin

3. **Dil Değiştirme**:
   - Sağ üst kısımdaki TR/EN butonları ile arayüz dilini değiştirin

4. **Sanal Klavye**:
   - Klavye ikonuna tıklayarak sanal klavyeyi açın/kapatın

## Özelleştirme

### Renkler ve Tema
CSS değişkenleri `main.css` dosyasında özelleştirilebilir:
- Ana renk paleti
- Buton stilleri
- Arka plan görselleri

### Logo Değiştirme
`assets/media/pisi-logo-magenta.png` dosyasını değiştirerek logo özelleştirilebilir.

### İkonlar
`assets/media/icons/` dizinindeki SVG dosyaları değiştirilebilir:
- `shutdown.svg` - Kapatma ikonu
- `restart.svg` - Yeniden başlatma ikonu
- `suspend.svg` - Uyku ikonu
- `keyboard.svg` - Sanal klavye ikonu

## Hata Ayıklama

Konsolda şu log mesajları kullanılır:
- `Lightdm objesi:` - LightDM nesnesi durumu
- `Kullanıcılar:` - Kullanıcı listesi
- `show_prompt çağrıldı:` - Şifre isteği durumu
- `authentication_complete çağrıldı:` - Giriş doğrulama durumu

## Geliştirme

### Test Ortamı
Tarayıcıda test için mock API kullanılabilir:
```javascript
// Konsolda çalıştırın
window.testAuth(); // Manuel şifre beklemesi başlatır
window.testDifferentAuth(); // Farklı authentication denemeleri
```

### Katkıda Bulunma
1. Bu depoyu fork'layın
2. Yeni özellik branch'ı oluşturun
3. Değişiklikleri gönderin
4. Pull request oluşturun

## Lisans

MIT Lisansı - detaylar için LICENSE dosyasına bakın.

## Sürüm Bilgisi

- **Sürüm**: 1.0.0
- **LightDM Uyumluluğu**: Web Greeter
- **Minimum Sistem**: Pisi Linux 2.0+
- **Tarayıcı**: Modern tarayıcılar

## İletişim

Sorunlar ve öneriler için:
- GitHub Issues: Proje deposunda issue oluşturun
- Pisi Forumları: Resmi Pisi destek kanalları

---

*Pisi Linux Web Greeter - Modern ve Güvenli Giriş Deneyimi*
