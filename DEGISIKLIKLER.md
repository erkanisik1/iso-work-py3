# Değişiklikler

Bu dosya, Pisi Linux 2.4.4 KDE6 canlı ISO üretim aracında (`iso-work-py3`)
yapılan çalışmaların özetini tutar.

Dönem: Ekim 2026

---

## 1. Canlı ISO / Önyükleme

- **EFI/GPT ISO üretimi** (`app/repotools/iso_ops.py`)
  - `make_EFI()` ile EFI imajı üretimi; `grubx64.efi` yalnızca `efi.img` içine konur.
  - `load_grub_params()` ve `_iso_label()` eklendi; ISO etiketi
    `Pisi_Linux_2.4.4_KDE6` olarak `grub.cfg` içindeki `iso_label=` ile eşleşir.
  - `mkinitcpio`'dan önce `depmod` çalıştırılır.
  - `isomounts` üretimi düzenlendi.
  - `xorriso` çağrısına `-isohybrid-mbr`, GPT, `-append_partition 2 0xef` ve
    `-partition_cyl_align all` parametreleri eklendi
    (ISO: "MBR isohybrid cyl-align-all GPT").
- **initramfs**
  - `modules.autoload.d/kernel-6.18` artık **dosya** olarak yazılıyor (dizin değil),
    içeriği `vfat`.
  - `inittab.live` → `etc/inittab` takası yapılıyor.
- **Görüntü yöneticisi servisi**
  - `configure-pending baselayout` sonrası `configure-pending -dv` (+ dbus yeniden
    başlatma denemesi) eklendi; "Etkin servisler:" çıktısı basılır ve
    görüntü yöneticisi yoksa uyarı verilir. Bu, metin modunda ("pisilinux login:")
    takılı kalmayı düzeltti.

## 2. Canlı kullanıcı ve kimlik

- **Yalnızca `pisi` kullanıcısı** (`app/repotools/image_ops.py`)
  - `chroot_comar()` artık ana makinenin `passwd`/`group` dosyalarını **kopyalamıyor**;
    eksik/boşsa `/usr/share/baselayout/{passwd,group,shadow}` şablonlarından üretiliyor.
  - `sanitize_live_users()` eklendi: uid ≥ 1000 olan `pisi`/`nobody` dışındaki tüm
    kullanıcılar `passwd/shadow/group/gshadow` üzerinden silinir, ev dizinleri
    kaldırılır (`.bak` dosyaları korunur).
  - Kullanıcı COMAR `addUser(1000, "pisi", "Pisi Linux", "/home/pisi", "/bin/bash",
    "live", [wheel,users,lp,lpadmin,cdrom,floppy,disk,audio,video,power,dialout], ...)`
    ile oluşturulur; birincil grup `wheel` (gid 10).
  - COMAR başarısız olursa `useradd` + `passwd -d` yedeği, ardından zorunlu
    `chpasswd` ile parola **`live`** olarak ayarlanır.
  - `/home/pisi` sahibi `pisi:wheel`, izin `711`.
- **SDDM autologin / X11**
  - `data/sddm/sddm.conf.d/sddm.conf`: `Session=plasmax11.desktop`,
    `RememberLastSession=false`, `DisplayServer=x11` (`[General]` altında),
    `[Wayland] SessionDir=/usr/share/wayland-sessions`.
  - `config_ops.setup_live_sddm()` `/var/lib/sddm/state.conf` yazar
    (`[Last] Session=plasmax11.desktop`, `User=pisi`, sahip 65:65, mod 0600).
  - SDDM 0.21'de `DefaultSession` anahtarı yoktur; oturum ön seçimi `state.conf`
    üzerinden gelir.

## 3. Yetkilendirme (polkit) — yali-rs parola sorunu

- **Kök neden:** Kurulum aracı `yali-rs`, `pkexec` ile başlatılıyor. Çalışan ISO'da
  bunu sağlayan `/usr/share/polkit-1/rules.d/10-nopasswd.rules` dosyası, refactor
  sırasında düşürülmüştü. Ayrıca `.pkla` dosyaları modern polkit (126) tarafından
  **okunmuyor** ve dizini `0644` (çalıştırma izni yok) oluşturuluyordu.
- **Düzeltme:** `config_ops.setup_live_policykit_conf()`
  - `data/polkit/10-nopasswd.rules` dosyasını
    `/usr/share/polkit-1/rules.d/` altına kopyalar (pisi → tüm eylemler serbest).
  - Eski polkit (< 106) için `.pkla` yedek olarak yazılır; dizin izni `0755` yapılır.

## 4. Ses yığını (PipeWire / Bluetooth)

- `data/audio/` + `app/repotools/audio_ops.py` (`setup_audio_stack`):
  - `pipewire-session`, `bt-watch` betikleri ve XDG autostart `.desktop` dosyaları.
  - `wireplumber` her iki paket listesine eklendi.
- `pulse` istemci ayarında `autospawn = no` açıkça yazılır (aksi halde libpulse
  gerçek PulseAudio'yu başlatıp BlueZ profillerini PipeWire'dan koparıyordu).
- Bluetooth cihazı için `bt-watch` (15 sn yoklama) ile yeniden bağlanma sağlanır.

## 5. Arayüz (GUI)

- **Çift derleme hatası düzeltildi** (`app/gui/main.py`):
  - HEAD'de mevcut olan yinelenen `self.actionMakeImage.triggered.connect(...)`
    kaldırıldı.
  - `_COMMAND_DEBOUNCE = 5.0` ve `_allow_command()` koruması eklendi;
    make/make-repo/make-live/pack-live/make-iso komutlarında çift tıklama artık
    tek komut üretir.
- **Dil seçimi eklendi** (bkz. bölüm 6).

## 6. Dil desteği

- **Yeni:** `app/gui/settings.py`
  - Dil tercihi `~/.config/pisiman/pisiman.conf` (`[General] language = tr_TR`)
    içinde saklanır.
  - `locale/` altında çevirisi (`.mo`/`.qm`) olan diller otomatik bulunur
    (şu an: Türkçe, English).
- `app/gui/__init__.py`
  - Kayıtlı dil, `MainWindow` import edilmeden **önce** `LANGUAGE`/`LANG`
    ortamına yazılır (gettext import anında kurulduğu için sıra önemlidir).
  - Qt çevirileri (`pisiman_ui.qm`, `qt_dialogs.qm`) seçilen dilden yüklenir.
- `app/gui/main.py`
  - Menü çubuğuna **Dil / Language** menüsü eklendi (Sistem dili, English, Türkçe).
  - Seçim kaydedilir ve "yeniden başlatılsın mı?" sorulur; `os.execv` ile aynı
    argümanlarla yeniden başlatılır.
  - Otomatik dil algılama artık kayıtlı tercihe saygılıdır (özellikle `en*`
    seçildiğinde tekrar Türkçe'ye dönmez).
- `locale/tr_TR/LC_MESSAGES/pisiman.po` yeni metinlerle güncellendi ve
  `pisiman.mo` yeniden derlendi.

## 7. Derleme altyapısı

- `pisiman.py`: `acquire_build_lock()` ile `flock(.build.lock)` tabanlı kilit.
  Aynı `WorkDir` üzerinde eşzamanlı ikinci kurulum engellenir (make_image()
  her çağrıda `image/` dizinini sildiği için veri kaybını önler).

## 8. Veri dizini yeniden düzenleme

- `data/kde_conf/` → `data/desktop_conf/`
- `data/yali/` → `data/installer/`
- Yeni EFI/GRUB kaynakları: `data/efi_grub/`, `data/grub/`
- Yeni ses ve polkit kaynakları: `data/audio/`, `data/polkit/`

---

## Bilinmeyenler / notlar

- Tüm yapılandırma değişiklikleri `make-live` adımında uygulanır;
  `pack-live`/`make-iso` tek başına yetmez (tam yeniden derleme gerekir).
- Yedek dosyalar (`*.bak`, `*.tar.gz`, `* copy`, `*.saglam`, `*yedek*`,
  `data/bck-efi/` vb.) sürüm kontrolüne **dahil edilmez** (bkz. `.gitignore`).
- Build çıktıları (`image/`, `iso/`, `*.iso`, `pisi.sqfs`) depoda tutulmaz.
