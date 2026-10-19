#!/usr/bin/python3
# -*- coding: utf-8 -*-

import os
import shutil
from .utility import run, xterm_title

def setup_live_kdm(project):
    image_dir = project.image_dir()
    kdmrc_path = os.path.join(image_dir, "etc/X11/kdm/kdmrc")
    if os.path.exists(kdmrc_path):
        lines = []
        with open(kdmrc_path, "r") as f:
            for line in f.readlines():
                if line.startswith("#AutoLoginEnable"):
                    lines.append("AutoLoginEnable=true\n")
                elif line.startswith("#AutoLoginUser"):
                    lines.append("AutoLoginUser=pisi\n")
                elif line.startswith("#ServerTimeout="):
                    lines.append("ServerTimeout=60\n")
                else:
                    lines.append(line)
        with open(kdmrc_path, "w") as f:
            f.write("".join(lines))
    else:
        print("*** %s doesn't exist, setup_live_kdm() returned" % kdmrc_path)

def setup_live_sddm(project):
    image_dir = project.image_dir()
    shutil.copy("./data/sddm/sddm.conf.d/sddm.conf",
                "{}/usr/lib/sddm/sddm.conf.d/".format(image_dir))
    shutil.copy("./data/etc/timezone", "{}/etc/".format(image_dir))

    # SDDM giris ekraninda X11 on secili olsun. state.conf'un "[Last]"
    # bolumu okunur; RememberLastSession=false oldugu icin bu deger her
    # giriste korunur (Wayland elle secilmedikce varsayilan X11 kalir).
    state_dir = os.path.join(image_dir, "var/lib/sddm")
    os.makedirs(state_dir, exist_ok=True)
    state = os.path.join(state_dir, "state.conf")
    with open(state, "w") as f:
        f.write("[Last]\nSession=plasmax11.desktop\nUser=pisi\n")
    try:
        os.chown(state, 65, 65)   # sddm:sddm
        os.chmod(state, 0o600)
    except OSError as e:
        print("  UYARI: state.conf sahipligi ayarlanamadi: %s" % e)
    print("  SDDM varsayilan oturum: plasmax11.desktop (X11)")

def setup_live_lxdm(project):
    image_dir = project.image_dir()
    lxdmconf_path = os.path.join(image_dir, "etc/lxdm/lxdm.conf")
    if os.path.exists(lxdmconf_path):
        lines = []
        with open(lxdmconf_path, "r") as f:
            for line in f.readlines():
                if line.startswith("# autologin=") or line.startswith("autologin="):
                    lines.append("autologin=pisi\n session=/usr/bin/startkde\n")
                elif line.startswith("session="):
                    if os.path.exists("%s/usr/bin/mate-session" % image_dir):
                        lines.append("session=/usr/bin/mate-session\n")
                    elif os.path.exists("%s/usr/bin/startxfce4" % image_dir):
                        lines.append("session=/usr/bin/startxfce4\n")
                    elif os.path.exists("%s/usr/bin/startlxqt" % image_dir):
                        lines.append("session=/usr/bin/startlxqt\n")
                    elif os.path.exists("%s/usr/bin/startlxde" % image_dir):
                        lines.append("session=/usr/bin/startlxde\n")
                else:
                    lines.append(line)
        with open(lxdmconf_path, "w") as f:
            f.write("".join(lines))
    else:
        print("*** {} doesn't exist, setup_live_lxdm() returned".format(lxdmconf_path))

def setup_live_lightdm(project):
    image_dir = project.image_dir()
    lxdmconf_path = os.path.join(image_dir, "etc/lightdm/lightdm.conf")
    if os.path.exists(lxdmconf_path):
        lines = []
        with open(lxdmconf_path, "r") as f:
            for line in f.readlines():
                if line.startswith("#autologin-user=") or line.startswith("autologin-user="):
                    lines.append("autologin-user=pisi\n")
                elif line.startswith("#autologin-session="):
                    sessions = os.listdir("%s/usr/share/xsessions" % image_dir)
                    session = sessions[0].split(".")[0]
                    lines.append("autologin-session=%s\n" % session)
                else:
                    lines.append(line)
        with open(lxdmconf_path, "w") as f:
            f.write("".join(lines))
    else:
        print("*** {} doesn't exist, setup_live_lxdm() returned".format(lxdmconf_path))

def setup_live_gdm(project):
    image_dir = project.image_dir()
    gdmconf_path = os.path.join(image_dir, "etc/gdm/custom.conf")
    if os.path.exists(gdmconf_path):
        lines = []
        with open(gdmconf_path, "r") as f:
            for line in f.readlines():
                if line.startswith("[daemon]"):
                    lines.append(line)
                    lines.append("AutomaticLoginEnable=True\n")
                    lines.append("AutomaticLogin=pisi\n")
                else:
                    lines.append(line)
        with open(gdmconf_path, "w") as f:
            f.write("".join(lines))
    else:
        print("*** {} doesn't exist, setup_live_gdm() returned".format(gdmconf_path))

def setup_live_dm(project, dm):
    if dm == "sddm":
        setup_live_sddm(project)
    elif dm == "lxdm":
        setup_live_lxdm(project)
    elif dm == "lightdm":
        setup_live_lightdm(project)
    elif dm == "gdm":
        setup_live_gdm(project)

def setup_live_policykit_conf(project):
    """Canli ISO'da pisi kullanicisina parolasiz yetki verir.

    ONEMLI: Polkit 106+ .pkla dosyalarini OKUMAZ; JavaScript .rules
    gerekir. Eski kod yalnizca .pkla yaziyordu. Ayrica referans arac
    /usr/share/polkit-1/rules.d/10-nopasswd.rules dosyasini da
    uretiyordu; refactor bunu dusurmus. Sonuc: yali-rs (pkexec)
    her acilista parola soruyordu.
    """
    image_dir = project.image_dir()

    # Bu kural paketlerden gelmiyor; referans arac uretiyordu, refactor
    # dusurmustu. Calisan ISO'daki dosya data/polkit/ altinda saklanir.
    rules_dir = os.path.join(image_dir, "usr/share/polkit-1/rules.d")
    os.makedirs(rules_dir, exist_ok=True)
    os.chmod(rules_dir, 0o755)
    nopasswd = os.path.join(rules_dir, "10-nopasswd.rules")
    src = os.path.join(os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__)))),
        "data/polkit/10-nopasswd.rules")
    if not os.path.isfile(src):
        src = "./data/polkit/10-nopasswd.rules"
    if os.path.isfile(src):
        shutil.copy(src, nopasswd)
    else:
        # data/ yoksa: pisi -> tum eylemler serbest
        with open(nopasswd, "w") as f:
            f.write("polkit.addRule(function(action, subject) {\n"
                    "        if (subject.user == \"pisi\") {\n"
                    "            return polkit.Result.YES;\n"
                    "        }\n"
                    "    });\n")
    os.chmod(nopasswd, 0o644)
    print("  polkit kurali: %s (pisi -> parolasiz)" % nopasswd)

    # Eski polkit (<106) icin .pkla. Modern polkit yok sayar ama dizin
    # izni 0755 olmali: 0644 iken icerige erisilemiyordu.
    legacy_dir = os.path.join(image_dir,
                              "etc/polkit-1/localauthority/90-mandatory.d")
    os.makedirs(legacy_dir, exist_ok=True)
    os.chmod(legacy_dir, 0o755)
    dest = os.path.join(legacy_dir, "livecd.pkla")
    with open(dest, "w") as f:
        f.write("[Live CD Rules]\n"
                "Identity=unix-user:pisi\n"
                "Action=*\n"
                "ResultAny=yes\n"
                "ResultInactive=yes\n"
                "ResultActive=yes\n")
    os.chmod(dest, 0o644)


# ---------------------------------------------------------------------------
# Canli masaustu yapilandirmasi
#
# Refactor sirasinda repotools/desktop_config.py ve bunun cagrilari
# tasindi. Modul ISO ile birlikte gelmiyordu; SDDM autologin'si
# (User=pisi / Session=plasmax11.desktop) uygulanmadigi icin canli
# sistem login ekraninda kaliyordu.
# ---------------------------------------------------------------------------

def yali_conf(project):
    """Kurulum araci (yali) masaustu girdileri ve polkit eylemi."""
    image_dir = project.image_dir()
    if "yali" in project.all_install_image_packages:
        for src, dst in (("yali.desktop", "usr/share/applications/"),
                         ("org.pisilinux.yali.policy",
                          "usr/share/polkit-1/actions/"),
                         ("yali-rescue.desktop", "usr/share/applications/")):
            _copy_if_exists("./data/installer/yali/%s" % src,
                            os.path.join(image_dir, dst))


def sddm_conf(project):
    """SDDM temasinin theme.conf ve arka planini kurar."""
    image_dir = project.image_dir()
    theme = os.path.join(image_dir, "usr/share/sddm/themes/pisilinux")
    if os.path.isdir(theme):
        for name in ("theme.conf", "bg.jpg"):
            _copy_if_exists("./data/sddm/%s" % name, theme)


def grub_conf(project):
    """GRUB tema dosyalarini gorsuntunun icine kopyalar."""
    image_dir = project.image_dir()
    if "grub2" in project.all_install_image_packages:
        run('cp -rf ./data/grub/ "%s/usr/share/"' % image_dir, ignore_error=True)


def kde_conf(project):
    """KDE canli masaustu: pisi kullanici dizini, skel, menu, duvar kagidi."""
    image_dir = project.image_dir()

    os.system("chroot %s chown -R pisi:wheel /home/pisi/.config" % image_dir)
    os.system("mkdir -p %s/home/pisi/Desktop" % image_dir)
    os.system("chroot %s chown -R pisi:wheel /home/pisi/.local" % image_dir)

    run('cp -rf ./data/etc/skel/.config "%s/home/pisi"' % image_dir,
        ignore_error=True)
    run('cp -rf ./data/etc/skel/ "%s/etc/"' % image_dir, ignore_error=True)
    run('cp -f ./data/etc/99-live-tz-fix "%s/etc/NetworkManager/dispatcher.d/"'
        % image_dir, ignore_error=True)
    os.system("chroot %s chmod -R 777 /home/pisi/.config" % image_dir)
    run('cp -rf ./data/etc/profile.d/ "%s/etc/"' % image_dir,
        ignore_error=True)
    run('cp -rf ./data/etc/xdg/ "%s/etc/"' % image_dir, ignore_error=True)

    # Bunlar kozmetik; eksik olsalar build'i durdurmamali.
    run('cp -f ./data/desktop_conf/kde_conf/script/* "%s/usr/local/bin"' % image_dir,
        ignore_error=True)
    run('cp -f ./data/desktop_conf/kde_conf/kde_menu/*.desktop "%s/usr/share/applications/"'
        % image_dir, ignore_error=True)
    run('cp -f ./data/desktop_conf/kde_conf/kde_menu/*.directory "%s/usr/share/desktop-directories/"'
        % image_dir, ignore_error=True)
    run('cp -rf ./data/desktop_conf/kde_conf/usr "%s/"' % image_dir,
        ignore_error=True)
    run('cp -rf ./data/desktop_conf/kde_conf/wallpapers "%s/usr/share"' % image_dir,
        ignore_error=True)
    os.system("chmod +x %s/usr/local/bin/*" % image_dir)


def etc_conf(project):
    run('cp -rf ./data/etc/skel/ "%s/etc/"' % project.image_dir(), ignore_error=True)


def calamares_conf(project):
    image_dir = project.image_dir()
    if "Calamares" in project.all_install_image_packages:
        run('cp -rf ./data/installer/calamares/branding "%s/usr/share/calamares/"'
            % image_dir)
        run('cp -rf ./data/installer/calamares/usr "%s/"' % image_dir)
        _copy_if_exists("./data/installer/calamares/settings.conf",
                        os.path.join(image_dir, "usr/share/calamares/"))
        _copy_if_exists(os.path.join(image_dir,
                                     "usr/share/applications/calamares.desktop"),
                        os.path.join(image_dir, "home/pisi/Desktop/"))


def _copy_if_exists(src, dest_dir):
    if not os.path.isfile(src):
        print("  ATLANDI (yok): %s" % src)
        return False
    os.makedirs(dest_dir, exist_ok=True)
    shutil.copy2(src, os.path.join(dest_dir, os.path.basename(src)))
    print("  %s" % os.path.join(dest_dir, os.path.basename(src)))
    return True


def setup_live_desktop(project):
    """
    Canli oturumun acilmasi icin gereken tum yapilandirmayi uygular.

    En onemlisi SDDM: data/sddm/sddm.conf.d/sddm.conf icerigi
    "User=pisi" ve "Session=plasmax11.desktop" ile autologin ayarlar.
    Bu dosya uygulanmazsa canli sistem login ekraninda bekler ve
    masaustu hic acilmaz.
    """
    print("Setting up live desktop...")
    xterm_title("Setting up live desktop")

    setup_live_sddm(project)
    setup_live_policykit_conf(project)
    yali_conf(project)
    grub_conf(project)
    sddm_conf(project)

    if "plasma-workspace" in project.all_install_image_packages:
        kde_conf(project)
        etc_conf(project)
        calamares_conf(project)

    # Autologin'in gercekten kuruldugunu dogrula (sessizce gecmesin).
    image_dir = project.image_dir()
    conf = os.path.join(image_dir, "usr/lib/sddm/sddm.conf.d/sddm.conf")
    if os.path.isfile(conf):
        with open(conf) as f:
            body = f.read()
        if "User=pisi" in body and "Session=plasmax11.desktop" in body:
            print("  SDDM autologin: User=pisi, Session=plasmax11.desktop (X11) OK")
        elif "User=pisi" in body:
            print("  UYARI: SDDM Session=plasmax11.desktop degil; "
                  "greeter'da Wayland on secili olabilir")
        else:
            print("  UYARI: SDDM autologin kullanici ayari yok "
                  "(login ekraninda kalir)")
    else:
        print("  UYARI: %s yok; SDDM autologin uygulanmadi" % conf)
