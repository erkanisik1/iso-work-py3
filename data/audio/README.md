# PipeWire ses yığını — ISO entegrasyonu

Bu dizin, ISO'nun `image/` kök dosya sistemine kopyalanacak dosyaları içerir.
Görüntüye enjekte eden kod: `app/repotools/audio_ops.py` → `setup_audio_stack()`.

## Neden gerekli

Bu ISO systemd'siz bir sistem üretir (PID 1 = `init`, yalnızca elogind var).
Dolayısıyla `pipewire.socket` / `pipewire-pulse.socket` systemd unit'ları
yoktur; oturum yönetimi kullanıcı oturumunda bir script ile kurulmak zorundadır.

Sorun üçlüsü:

| # | Adım | Sonuç |
|---|------|-------|
| 1 | `client.conf` içinde `autospawn` açık | libpulse (Plasma dahil) sunucu yokken `pulseaudio --start` çağırır |
| 2 | Gerçek PulseAudio `org.bluez`'e A2DP/HFP profillerini kaydeder | |
| 3 | PipeWire aynı profilleri kaydetmeye çalışır | BlueZ `NotPermitted` döner, WirePlamber cihazı hiç enumerate edemez |

Sonuç: Bluetooth hoparlör sisteme bağlı görünür ama KDE ses ayarlarında
**kaybolur**. Pulse uygulamaları çalışırken native PipeWire istemcileri
(vokoscreenNG dahil) bağlanamaz.

PipeWire'ın kendi uyarısı bu durumu teşhis eder:

```
Multiple sound server instances (PipeWire/Pulseaudio/bluez-alsa) are probably
trying to use Bluetooth audio at the same time.
```

## Dosyalar

```
data/audio/
├── usr/bin/
│   ├── pipewire-session     # oturum yöneticisi (başlat/durdur/reset/durum)
│   └── bt-watch             # BT ses cihazı izleyici
└── etc/xdg/autostart/
    ├── pipewire-session.desktop
    └── bt-watch.desktop
```

## Eklenmesi gerekenler

### 1. Proje XML — wireplamber

**Bu zorunlu.** Proje XML'ine ekleyin:

```xml
<SelectedPackage>wireplumber</SelectedPackage>
<Package>wireplumber</Package>
```

> **Önemli:** kurulum listesini belirleyen `<Package>` listesidir, `<SelectedPackage>` değil.
> `make_repos` ve `install_packages` ikisi de `<Package>` listesini kullanır
> (`app/repotools/image_ops.py` → `project.all_install_image_packages`).
> İkisine de eklemek en güvenlisi.

> Ayrıca **hiçbir paket wireplamber'ı bağımlılık olarak çekmiyor**:
>
> ```
> kwin ─┐
> spectacle ─┼─→ pipewire
> xdg-desktop-portal-kde ─┘
>
> wireplumber ──→ pipewire      (tersi yok)
> ```
>
> Bu yüzden `SelectedPackage`'a elle eklenmesi şart. Eklenmezse ISO'daki
> durum tam olarak "soketi olmayan pipewire" hatasıdır.

### 2. Build kancası — `app/repotools/image_ops.py`

`make_image()` içinde, paketler kurulduktan **sonra** ekleyin:

```python
from app.repotools.audio_ops import setup_audio_stack
setup_audio_stack(project)
```

Önerilen konum: `chroot_comar(image_dir)` çağrısından sonra, `finally:`
blokundaki `umount` satırlarından sonra — yani `finally:` bloğu bittikten
sonra, `finished.txt` yazılmadan.

### 2b. Yeniden build yapmadan uygulamak

Build `make-live` aşamasını bitirmiş, `pack-live` öncesi ise:

```bash
cd /home/erkanisik/iso-work-py3
python3 app/repotools/audio_ops.py \
    /home/erkanisik/newiso/pisilinux-2.4.4-cpio-yalirs2/image
```

`pulseaudio.desktop` korunacaksa:

```bash
python3 app/repotools/audio_ops.py <image_dir> --keep-pa-autostart
```

## X11 ve Wayland

Ses yığını **oturum tipinden bağımsızdır**: `pipewire-session.desktop`
XDG autostart girdisidir ve her iki oturumda da çalışır. Ayrı bir
X11/Wayland ayrımı yoktur.

`setup_audio_stack()` build sırasında her iki oturumun da hazır olduğunu
denetler ve loga yazar:

```
[audio-ops] oturumlar:
[audio-ops]   X11      oturum dosyasi VAR, baslatici VAR
[audio-ops]   Wayland  oturum dosyasi VAR, baslatici VAR
```

### `pulseaudio.desktop` neden kaldırılıyor

Bu dosya `start-pulseaudio-x11` çağırır, o da
`pactl load-module module-x11-publish` ile başlar. PipeWire bu modülü
**sağlamaz**, dolayısıyla:

```
$ DISPLAY=:1 start-pulseaudio-x11
Hata: Hiçbir giriş yok
$ echo $?
1
```

`set -e` yüzünden ilk hatta durur ve `module-x11-cork-request`,
`module-x11-xsmp` hiç yüklenmez. Autostart'ta zararsız ama her oturumda
işini yapamayan bir giriş. Kaldırılıyor.

### Kaybedilenler ve karşılığı

| Modül | Durum | Önemi |
|---|---|---|
| `module-x11-publish` | ❌ yok | `_PULSE_SERVER` X11 kök pencere özelliği. Yalnızca çok eski istemciler kullanır; modern libpulse soket/D-Bus kullanır. |
| `module-x11-cork-request` | ❌ yok | Tam ekran uygulamada otomatik susturma. KDE Plasma 6'da kullanılmaz. |
| `module-x11-xsmp` | ❌ yok | 2000'lerden kalma oturum yönetimi; ölü standart. |
| `module-device-manager` | ✅ pipewire sürümü | Otomatik yüklenir. |
| `libpipewire-module-x11-bell` | ✅ otomatik | X11 zil olayları. `DISPLAY` varsa etkin; ek yapılandırma gerekmez. |

Yani X11 tarafında işlevsel kayıp yok: `module-device-manager` ve X11 zil
pipewire-pulse tarafından zaten sağlanıyor.

**Not:** Bu kayıp pipewire'ın kendi sınırı, bizim değişikliğimiz değil.
Gerçek PulseAudio kurulu olsa bile pipewire öncelikli olduğu anda aynı
durum oluşurdu. GNOME/Ubuntu gibi dağıtımlar da tam olarak böyle çalışır.

`pulseaudio` **paketi** kurulu kalır — `plasma-pa` ve `pulseaudio-qt6`
buna bağımlı olabilir. Sadece otomatik başlatma engellenir
(`autospawn = no`) ve autostart girdisi kaldırılır.

## Davranış

Açılışta `pipewire-session` devreye girer:

1. Gerçek PulseAudio varsa durdurulur
2. Öksürük pipewire süreçleri temizlenir
3. `pipewire` → `wireplumber` → `pipewire-pulse` sırayla başlatılır
4. Her adım doğrulanır (sokete cevap vermesi beklenir)
5. 10 sn boyunca PA'nın geri gelmesi izlenir

Tanılama:

```bash
pipewire-session status     # oturum, tek-ses-sunucusu kuralı, autospawn
bt-watch status             # BT izleyici durumu
cat /run/user/1000/pipewire-session.log
```

## Dikkat: BT otomatik bağlanma

Bu cihazda (DW-CT14+) BlueZ, **bilinen ama kesilmiş** bir cihazı kendisi
geri çağırmaz. `ReconnectIntervals` yalnızca link kopması için geçerlidir,
temiz `disconnect`'i kapsamaz. Ölçülen davranış:

| Senaryo | Sonuç |
|---------|-------|
| Cihaz açılıp menzile girerse | kendiliğinden bağlanıyor |
| Açılışta (menzildeyken) | bağlanmıyor |
| `bluetoothctl disconnect` sonrası | 90 sn bekleniyor, bağlanmıyor |

Bu yüzden `bt-watch` gerekiyor: 15 sn'de bir eşleşmiş + güvenilir + bağlı
olmayan ses cihazlarını bağlıyor. Kesip bırakıldığında ~12 sn'de geri geldi.

## pipewire-session restart uyarısı

`pipewire-session restart` çalıştırmak A2DP bağlantısını düşürür ve cihaz
kendiliğinden geri gelmez. Yeniden bağlamak için:

```bash
bluetoothctl connect <MAC>
```