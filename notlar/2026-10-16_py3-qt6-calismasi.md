# Çalışma Notu — 2026-10-16 (Py3 + PyQt6)

## 1. pisi-iso-creator_py3 dizininde yapılan Py3/Qt6 göçü (baz değişmeden önce)
- `repotools/`: `urllib2→urllib.request`, `except as`, `unicode→str`,
  `xrange→range`, `has_key→in`, `file()→open()`, `0666→0o666`,
  `map→list(map)`, binary/text `open()` + `bz2/lzma` bytes düzeltmeleri.
- `gui/`: `PyQt5→PyQt6`, `exec_()→exec()`, `QAction` QtGui'ye,
  `Qt.Checked→Qt.CheckState.Checked`, `Qt.AscendingOrder→Qt.SortOrder...`,
  `QEvent.KeyPress→QEvent.Type.KeyPress`,
  `QKeySequence.Copy→StandardKey.Copy`, `menu.exec_→exec`.
- `gui/terminal.py` (yeni): QTermWidget yoksa QPlainTextEdit fallback.
- `gettext.ldgettext` kaldırılmış → `dgettext` + try/except.
- 6 `.ui` `pyuic6` ile üretildi, `raw_rc.py` pyrcc5+import yaması.
- `make.sh`/`Makefile`/`required_packages.txt` güncellendi.
- `QTermWidget` python bağı yokluğu teyit edildi:
  `libqtermwidget6` (C++) kurulu ama `pyqtermwidget6` depolarda YOK.
- `tools/pyqtermwidget6/` altına upstream `lxqt/qtermwidget` `pyqt/`
  tarifi gömüldü (`pyproject.toml`, `project.py`, `sip/qtermwidget.sip` v2.4.0);
  derleme scripti yazılmadı, bekliyor.
- Alternatif araştırıldı: `termqt` 1.1 (PyQt6, saf Python, pip) adapter ile
  kullanılabilir; uygulanmadı.

## 2. Baz değişimi: erkanisik1/iso-work-py3
- `/home/erkanisik/iso-work-py3` altına klonlandı, oturum buraya taşındı.
- Bu repo zaten ileride: `uic.loadUi`, QProcess tabanlı terminal,
  `bindtextdomain` gettext, modüler `repotools`, `locale/` altyapısı.

## 3. iso-work-py3 üzerinde düzeltmeler (hepsi doğrulandı, commit YOK)
1. `app/repotools/maker.py`: `project.load()` → `project.open()` + hata kontrolü
   (böyle metot yoktu, `AttributeError` verirdi).
2. `TerminalFallback`: one-shot `sh -c` yerine kalıcı interaktif `bash`
   (üst üste komut çakışması giderildi, ölen shell yeniden başlar,
   gönderilen komut `$ ...` satırıyla loglanır).
3. **Sistem Ayarları sekmesi** eski projeden taşındı
   (`app/gui/ui/mainv2.ui` tab_4 + `releaseFilesLoad`/`slotReleaseSave`);
   `project_root` 4→3 kademe düzeltildi (`locale/` ve `DATA_DIR` artık repo kökü).
4. Dosya diyalogları: 9 çağrıya `DontUseNativeDialog` (Breeze ile uyum +
   sudo altında portal hatasına takılmama).
5. Çeviriler: gettext `.po`'ya 16 eksik dizgi (`.mo` üretildi);
   `qt_dialogs.ts/.qm` (YENİ): Qt'nin kendi dizgileri için
   `QFileDialog`+`QPlatformTheme` context'leri (45 dizgi);
   `pisiman_ui.ts`'ye yeni sekme dizgileri + 4 bitmemiş çeviri.
6. `style.qss`: `QListView` eklendi (dosya diyaloğu sol menüsü beyaz kalıyordu).
7. Proje XML kökü: `PisimanProject` katı kontrol korundu,
   `project-files/**/*.xml` 14 dosya çevrildi (14/14 açılıyor).
   `.tar.gz` arşivine dokunulmadı.
8. Takılan "Downloaded..." penceresi: `updateRepo()` → `try/finally`,
   `Progress.finished()` → `hide+deleteLater`; bilinmeyen hatada uyarı mesajı.

## 4. Doğrulananlar
- `py_compile` temiz; Qt6 enum taraması temiz.
- Offscreen smoke: MainWindow + diyaloglar + proje aç/kaydet turu.
- Terminalde ardışık komut çıktısı; sekme içerikleri + kaydetme turu;
  çeviriler (gettext + QTranslator) canlı diyalogda test edildi.

## 5. Yarın / bekleyenler
- Uygulamayı KAPATIP yeniden başlatıp gerçek `make` ile ilerleme
  penceresinin kapanışını teyit et (ekrandaki takılı pencere eski oturumdandı).
- `data/` ve `project-files/` kullanıcının kendi değişikliği — commit'e dahil
  edilmeden duruyor; ne yapılacağına karar ver.
- Hiçbir şey commitlenmedi/pushlanmadı.
- İstenirse: `pyqtermwidget6` derleme scripti veya `termqt` adapteri.
  (2026-10-16 akşamı karar: GEREK YOK — mevcut QProcess terminali yeterli.)
