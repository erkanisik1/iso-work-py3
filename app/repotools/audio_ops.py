#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
PipeWire ses yigini kurulumu - ISO gorsuntusune (image/) dosya enjekte eder.

NEDEN GEREKIYOR
---------------
Bu ISO, systemd'siz bir sistem uretir (PID 1 = init, yalnizca elogind var).
Bu yuzden systemd'in pipewire.socket / pipewire-pulse.socket servisleri yok;
oturum yonetimi kullanici oturumunda bir script ile kurulmak zorunda.

Sorun ucu:
  1. /etc/pulse/client.conf icinde autospawn acik birakildiginda, sunucu
     yokken libpulse (Plasma dahil her istemci) kendisi
     "pulseaudio --start" cagirip gercek PulseAudio'yu ayaga kaldirir.
  2. Gercek PulseAudio, org.bluez'e A2DP/HFP profillerini kaydeder.
  3. PipeWire ayni profilleri kaydetmeye calisir, BlueZ "NotPermitted"
     doner; WirePlumber cihazi hic enumerate edemez.
  4. Sonuc: Bluetooth hoparlor sisteme bagli gorunur ama KDE ses
     ayarlarinda KAYBOLUR.

Bu modul:
  - /usr/bin/pipewire-session ve /usr/bin/bt-watch betiklerini kopyalar
  - ilgili autostart .desktop dosyalarini ekler
  - client.conf icindeki autospawn satirlarini kapatir
  - gorsuntude wireplamber olup olmadigini dogrular (yoksa uyari verir)

Kullanim (app/repotools/image_ops.py icinde, install_packages() SONRASI):
    from app.repotools.audio_ops import setup_audio_stack
    setup_audio_stack(project)
"""

import os
import re
import shutil
import stat

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))), "data", "audio")


def _log(msg):
    print("[audio-ops] %s" % msg)


def _install(src, dst_dir, name):
    """Dosyayi hedef dizine 0755 izinle kopyalar."""
    if not os.path.isfile(src):
        _log("ATLANDI (kaynak yok): %s" % src)
        return False
    os.makedirs(dst_dir, exist_ok=True)
    dst = os.path.join(dst_dir, name)
    shutil.copy2(src, dst)
    os.chmod(dst, 0o755)
    _log("kuruldu: %s" % dst)
    return True


def _patch_client_conf(image_dir):
    """
    /etc/pulse/client.conf icindeki acik autospawn satirlarini kapatir.

    PA paketinin varsayilan dosyasinda ayar yorum icindedir
    ("; autospawn = yes") ve bu durumda PA hicbir zaman otomatik
    baslamaz. Sorun, ayarin yorumdan cikarilmis olmasidir.
    """
    conf = os.path.join(image_dir, "etc/pulse/client.conf")
    if not os.path.isfile(conf):
        _log("client.conf bulunamadi, autospawn yamasi atlandi")
        return False

    with open(conf, "r") as f:
        lines = f.readlines()

    changed = 0
    out = []
    for line in lines:
        # Yorum satiri olmayan "autospawn = yes/no" satirlarini pasiflestir
        m = re.match(r"^(\s*)autospawn\s*=\s*\S+\s*$", line)
        if m:
            out.append("%s; autospawn = no   # ses dagogi pipewire-pulse (audio_ops)\n"
                       % m.group(1))
            changed += 1
        else:
            out.append(line)

    if changed == 0:
        out.append("\n")

    # Onemli: yorum satiri "autospawn" ayarini TUMAMAZ, PulseAudio
    # tanimlanmis bir deger bulamayinca varsayilana doner ve
    # varsayilan "yes"tir. Yani satirlari yorumlamak tek basina
    # YETMEZ; acik bir "autospawn = no" bulunmalidir.
    has_active = any(re.match(r"^\s*autospawn\s*=\s*\S+", l) for l in out)
    if not has_active:
        out.append("; pipewire-session tarafindan yonetilir (audio_ops)\n"
                   "autospawn = no\n")
        _log("client.conf: acik 'autospawn = no' eklendi (varsayilan yes "
             "oldugu icin yorumlamak yeterli degildir)")
        changed += 1

    with open(conf, "w") as f:
        f.writelines(out)

    _log("client.conf: autospawn kapatildi (%d satir)" % changed)
    return True


def _check_wireplumber(image_dir):
    """
    wireplamberin gorsuntude OLDUGUNDAN emin ol.

    Yoksa pipewire calisir ama oturum/politika yoneticisi olmadigi icin
    hicbir ses cikti cikti cihazi olusmaz. Bu, scriptin duzeltmeseye
    calistigi en yaygin senaryodur; sessizce gecmemek icin uyari verir.
    """
    wp = os.path.join(image_dir, "usr/bin/wireplumber")
    lib = None
    for name in os.listdir(os.path.join(image_dir, "usr/lib")) \
            if os.path.isdir(os.path.join(image_dir, "usr/lib")) else []:
        if name.startswith("libwireplumber"):
            lib = name
            break

    if os.path.isfile(wp) and lib:
        _log("wireplamber OK (%s, %s)" % (os.path.basename(wp), lib))
        return True

    _log("UYARI: wireplamber gorsuntude YOK!")
    _log("       Proje XML'ine <SelectedPackage>wireplumber</SelectedPackage> ekleyin.")
    _log("       Aksi halde pipewire calisir ama ses cihazi olusmaz.")
    return False


def _check_daemons(image_dir):
    """Beklenen ses araclarinin gorsuntude var oldugunu dogrular."""
    for name in ("pipewire", "pulseaudio"):
        path = os.path.join(image_dir, "usr/bin", name)
        _log("%-12s %s" % (name, "VAR" if os.path.exists(path) else "YOK"))


def _check_sessions(image_dir):
    """
    Hem X11 hem Wayland oturumunun sesle birlikte hazir oldugunu dogrular.

    Ses yigini oturum tipinden bagimsizdir: XDG autostart her iki
    oturumda da calisir. Ama oturum giris dosyalari gercekten
    mevcut mu, diye bakmak iyi olur; biri silinmis olursa build
    sonrasi fark etmek zor olur.
    """
    _log("---")
    _log("oturumlar:")
    for label, xsession, wayland, launcher in (
        ("X11", "usr/share/xsessions/plasmax11.desktop",
         None, "usr/bin/startplasma-x11"),
        ("Wayland", None,
         "usr/share/wayland-sessions/plasma.desktop",
         "usr/bin/startplasma-wayland"),
    ):
        parts = []
        session_file = xsession or wayland
        parts.append("oturum dosyasi %s" %
                     ("VAR" if os.path.isfile(os.path.join(image_dir, session_file))
                      else "YOK"))
        parts.append("baslatici %s" %
                     ("VAR" if os.path.isfile(os.path.join(image_dir, launcher))
                      else "YOK"))
        _log("  %-8s %s" % (label, ", ".join(parts)))


def setup_audio_stack(project, drop_pulseaudio_autostart=True):
    """
    Gorsuntuye PipeWire oturum altyapisini kurar.

    drop_pulseaudio_autostart=True (varsayilan):
        /etc/xdg/autostart/pulseaudio.desktop kaldirilir.

        Bu dosya "start-pulseaudio-x11" cagirir; o script de
        "pactl load-module module-x11-publish" ile baslar. PipeWire
        bu modulu SAGLAMAZ, her X11 oturumunda "Hata: Hiçbir giriş
        yok" + cikis kodu 1 ile hata verir. X11 ve Wayland icin
        gereksiz oldugundan kaldirilir.

        Kaybi olan X11 tarafi:
          - module-x11-publish  : _PULSE_SERVER kok pencere ozelligi.
                                  Yalnizca cok eski istemciler kullanir;
                                  modern libpulse soket/D-Bus kullanir.
          - module-x11-cork-request : tam ekran uygulamada susturma.
          - module-x11-xsmp    : 2000'lerden kalma oturum yonetimi.
        Bunlarin hicbiri KDE Plasma 6'da kullanilmaz; X11 zil olaylari
        icin pipewire-pulse zaten libpipewire-module-x11-bell modulunu
        kendi yukler (DISPLAY varsa etkin), module-device-manager da
        pipewire surumuyle yuklenir.

        pulseaudio PAKETI kurulu kalir: plasma-pa ve pulseaudio-qt6
        buna bagimli olabilir. Sadece otomatik baslatma engellenir
        (autospawn = no) ve autostart girisi kaldirilir.
    """
    image_dir = project.image_dir()
    _log("gorsuntu: %s" % image_dir)

    # 1) Betikler
    _install(os.path.join(DATA_DIR, "usr/bin/pipewire-session"),
             os.path.join(image_dir, "usr/bin"), "pipewire-session")
    _install(os.path.join(DATA_DIR, "usr/bin/bt-watch"),
             os.path.join(image_dir, "usr/bin"), "bt-watch")

    # 2) Autostart dosyalari
    autostart = os.path.join(image_dir, "etc/xdg/autostart")
    for name in ("pipewire-session.desktop", "bt-watch.desktop"):
        src = os.path.join(DATA_DIR, "etc/xdg/autostart", name)
        if os.path.isfile(src):
            os.makedirs(autostart, exist_ok=True)
            shutil.copy2(src, os.path.join(autostart, name))
            os.chmod(os.path.join(autostart, name), 0o644)
            _log("kuruldu: %s" % os.path.join(autostart, name))
        else:
            _log("ATLANDI (kaynak yok): %s" % src)

    # 3) PulseAudio otomatik baslatmasini kapat
    _patch_client_conf(image_dir)

    # 4) Istege bagli: calisamayan pulseaudio autostart'ini kaldir
    pa_desktop = os.path.join(autostart, "pulseaudio.desktop")
    if drop_pulseaudio_autostart and os.path.isfile(pa_desktop):
        os.remove(pa_desktop)
        _log("kaldirildi: %s (pipewire-pulse module-x11-publish saflamaz; "
             "her X11 oturumunda hata verirdi)" % pa_desktop)
    elif os.path.isfile(pa_desktop):
        _log("korundu: %s (drop_pulseaudio_autostart=False)" % pa_desktop)

    # 5) Dogrulama
    _check_daemons(image_dir)
    _check_wireplumber(image_dir)
    _check_sessions(image_dir)

    _log("---")


class _Project(object):
    """CLI kullanimi icin sahte proje sinifi."""

    def __init__(self, image_dir):
        self._image_dir = image_dir

    def image_dir(self):
        return self._image_dir


def _cli(argv):
    """
    Dogrudan calistirilabilir:

        python3 app/repotools/audio_ops.py <image_dir> [--keep-pa-autostart]

    Boylece tam build yapmadan mevcut bir gorsuntuye de uygulanabilir
    (build "make-live" bittikten sonra, "pack-live" oncesi).
    """
    args = [a for a in argv[1:] if not a.startswith("--")]
    flags = [a for a in argv[1:] if a.startswith("--")]

    if not args:
        print("kullanim: %s <image_dir> [--keep-pa-autostart]" % argv[0])
        return 2

    image_dir = os.path.abspath(args[0])
    if not os.path.isdir(image_dir):
        print("HATA: dizin yok: %s" % image_dir)
        return 1

    setup_audio_stack(_Project(image_dir),
                      drop_pulseaudio_autostart="--keep-pa-autostart" not in flags)
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_cli(sys.argv))