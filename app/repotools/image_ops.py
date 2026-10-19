#!/usr/bin/python3
# -*- coding: utf-8 -*-

import os
import sys
import time
import shutil
import subprocess
import stat
import tempfile
import dbus
from .utility import wait_bus, run, xterm_title, strip_ansi

bus = None

def run_batch(cmd, shell=True, env=os.environ.copy()):
    proc = subprocess.Popen(cmd, shell=shell, env=env,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    for line in iter(proc.stdout.readline, b''):
        try:
            decoded_line = line.decode('utf-8', errors='ignore')
            print(strip_ansi(decoded_line), end='')
        except Exception as e:
            print(e)
    # print(proc.stderr.read().decode('utf-8', errors='ignore'))
    proc.poll()
    return proc.returncode

def overlay(project, path, to=None, upperdir=None, workdir=None):
    image_dir = project.image_dir()
    work_dir = project.work_dir
    overlay_dir = "{}/overlay".format(work_dir)

    if to is None:
        to = "{image_dir}/{path}".format(image_dir=image_dir, path=path)

    if upperdir is None:
        upperdir = "{}/upper_{}".format(overlay_dir, path)

    if workdir is None:
        workdir = "{}/work_{}".format(overlay_dir, path)

    for i in (overlay_dir, upperdir, workdir, to,):
        os.makedirs(i, exist_ok=True)

    run('/bin/mount -t overlay overlay -o lowerdir=/{path},upperdir={upperdir},workdir={workdir} {to}'.format(path=path, upperdir=upperdir, workdir=workdir, to=to))

def unoverlay(project, name, ignore_error=True):
    run('/bin/umount %s' % os.path.join(project.image_dir(), name), ignore_error=ignore_error)

def connectToDBus(path):
    global bus
    if os.environ.get('DBUS_SYSTEM_BUS_ADDRESS'):
        del os.environ['DBUS_SYSTEM_BUS_ADDRESS']
    os.environ['DBUS_SYSTEM_BUS_ADDRESS'] = "unix:path=%s/run/dbus/system_bus_socket" % path
    # Sonsuz dongu yok: dbus acilmazsa build kilitlenmesin.
    for _ in range(30):
        try:
            bus = dbus.SystemBus()
            return bus
        except Exception:
            print("trying to connect dbus..")
            time.sleep(1)
    print("UYARI: DBus'e baglanilamadi (30 sn); COMAR islemleri atlanacak")
    bus = None
    return None

def sanitize_live_users(image_dir):
    """Canli ISO'da yalnizca 'pisi' insan kullanicisi kalsin.

    uid >= 1000 olan ve 'pisi'/'nobody' disindaki girdileri
    passwd/shadow/group dosyalarindan temizler, ev dizinlerini kaldirir.
    Boylece ev sahibinden kopyalanmis kullanicilar (or. erkanisik) imaja
    sizmaz ve uid 1000 cakismasi nedeniyle pisi'nin olusturulmasi
    engellenmez. Dosyalarin .bak yedegi alinir.
    """
    etc = os.path.join(image_dir, "etc")
    passwd = os.path.join(etc, "passwd")
    if not os.path.isfile(passwd):
        return []

    keep = {"pisi", "nobody"}
    with open(passwd) as f:
        lines = f.readlines()

    removed = []
    kept = []
    for line in lines:
        parts = line.rstrip("\n").split(":")
        if len(parts) >= 4:
            try:
                uid = int(parts[2])
            except ValueError:
                uid = -1
            if uid >= 1000 and parts[0] not in keep:
                removed.append((parts[0], uid,
                                parts[5] if len(parts) > 5 else ""))
                continue
        kept.append(line)

    if not removed:
        return []

    names = set(n for n, _u, _h in removed)

    # Yedek
    for fn in ("passwd", "shadow", "group", "gshadow"):
        p = os.path.join(etc, fn)
        if os.path.isfile(p):
            try:
                shutil.copy2(p, p + ".bak")
            except OSError:
                pass

    with open(passwd, "w") as f:
        f.writelines(kept)

    for fn in ("shadow", "gshadow"):
        p = os.path.join(etc, fn)
        if not os.path.isfile(p):
            continue
        with open(p) as f:
            ls = f.readlines()
        with open(p, "w") as f:
            for line in ls:
                if line.split(":", 1)[0] not in names:
                    f.write(line)

    grp = os.path.join(etc, "group")
    if os.path.isfile(grp):
        with open(grp) as f:
            ls = f.readlines()
        out = []
        for line in ls:
            parts = line.rstrip("\n").split(":")
            if parts[0] in names:
                continue
            if len(parts) >= 4 and parts[3]:
                members = [m for m in parts[3].split(",") if m not in names]
                parts[3] = ",".join(members)
                line = ":".join(parts) + "\n"
            out.append(line)
        with open(grp, "w") as f:
            f.writelines(out)

    for _name, _uid, home in removed:
        if home.startswith("/home/") and home != "/home/pisi":
            hp = os.path.join(image_dir, home.lstrip("/"))
            if os.path.isdir(hp):
                shutil.rmtree(hp, ignore_errors=True)

    print("  Kaldirilan insan kullanicilari: %s"
          % ", ".join("%s(uid %d)" % (n, u) for n, u, _h in removed))
    return [n for n, _u, _h in removed]


def chroot_comar(image_dir):
    print("DEBUG: Setting up D-Bus in chroot: %s" % image_dir)
    # Ensure /etc/passwd and /etc/group exist, otherwise DBus/COMAR won't start
    print("DEBUG: Setting up D-Bus/COMAR in chroot: %s" % image_dir)
    os.makedirs(os.path.join(image_dir, "etc"), exist_ok=True)
    # ONEMLI: /etc/passwd, /etc/group ve /etc/shadow KOPYALANMAZ.
    # Onceki kod ev sahibinin bu dosyalarini imaja kopyaliyordu; sonuc:
    #   - canli sistemde "pisi" kullanicisi hic olusmuyor,
    #   - ev sahibinin kullanicilari (or. erkanisik) imajda gorunuyor,
    #   - SDDM autologin "User=pisi" hedefini bulamayip sifre soruyor.
    # Gercek kullanicilar COMAR (baselayout) tarafindan configure-pending
    # sirasinda olusturulur. Sadece ag icin gereken dosyalar, eksiklerse
    # kopyalanir.
    for f in ('hosts', 'resolv.conf'):
        src = os.path.join('/etc', f)
        dst = os.path.join(image_dir, 'etc', f)
        if os.path.exists(src) and not os.path.exists(dst):
            shutil.copy2(src, dst)
            print("DEBUG: Copied %s to chroot (missing)" % f)

    # /etc/passwd, group, shadow yoksa BASELAYOUT SABLONUNDAN olustur.
    # Ev sahibinden kopyalanmaz: aksi halde imajda host kullanicilari
    # gorunur ve "pisi" hic olusmaz (SDDM autologin sifre sorar).
    # dbus-daemon'un chroot icinde acilmasi icin de gecerli bir passwd
    # dosyasi sart.
    for f in ('passwd', 'group', 'shadow'):
        dst = os.path.join(image_dir, 'etc', f)
        tmpl = os.path.join(image_dir, 'usr/share/baselayout', f)
        if os.path.exists(tmpl) and (not os.path.exists(dst)
                                     or os.path.getsize(dst) == 0):
            shutil.copy2(tmpl, dst)
            print("DEBUG: /etc/%s baselayout sablonundan olusturuldu" % f)

    # Ensure /var/run -> /run link exists for legacy apps like pisi
    var_run = os.path.join(image_dir, "var/run")
    # os.system('rm -rf "%s"' % var_run) # Removed this hanging rm -rf
    try:
        # Link inside chroot must be relative to work both inside and outside
        os.symlink("../run", var_run)
        print("DEBUG: Created symlink %s -> ../run" % var_run)
    except OSError as e:
        print("DEBUG: Symlink error: %s" % e)
    
    os.makedirs(os.path.join(image_dir, "run/dbus"), exist_ok=True)
    os.makedirs(os.path.join(image_dir, "var/lib/dbus"), exist_ok=True)
    os.system('rm -f "%s"' % os.path.join(image_dir, "run/dbus/pid"))
    
    # Ensure machine-id
    if not os.path.exists(os.path.join(image_dir, "var/lib/dbus/machine-id")):
        run('chroot "%s" /usr/bin/dbus-uuidgen --ensure' % image_dir, ignore_error=True)
        
    # Start D-Bus
    print("DEBUG: Starting dbus-daemon via chroot command")
    # Setting DBUS_USER to root helps if nss is still tricky, but --system normally drops to dbus user
    run('chroot "%s" /usr/bin/dbus-daemon --system --fork --address=unix:path=/var/run/dbus/system_bus_socket' % image_dir, ignore_error=True)
    
    # Start COMAR
    if os.path.exists(os.path.join(image_dir, "usr/sbin/comard")):
        print("DEBUG: Starting comard via chroot command")
        run('chroot "%s" /usr/sbin/comard' % image_dir, ignore_error=True)
        
    socket_on_host = os.path.join(image_dir, "var/run/dbus/system_bus_socket")
    print("DEBUG: Waiting for socket: %s" % socket_on_host)
    if wait_bus(socket_on_host):
        print("DEBUG: D-Bus socket is READY on host.")
    else:
        print("DEBUG: D-Bus socket TIMEOUT on host!")

def get_exclude_list(project):
    excludes = [
        "var/cache/pisi/packages/*",
        "var/lib/pisi/index/*",
        "var/lib/pisi/scripts/*",
        "var/cache/pisi/archives/*"
    ]
    # Add more excludes from project if needed
    return excludes

def install_packages(project):
    image_dir = project.image_dir()
    if 'Calamares' in project.all_packages:
        packages = project.all_packages
    else:
        packages = project.all_install_image_packages
    
    run('pisi --yes-all --ignore-comar --ignore-dependency \
        --ignore-file-conflicts -D"%s" it %s \
        ' % (image_dir, " ".join(packages)))

def squash_image(project):
    from app.repotools.iso_ops import mkinitcpio
    image_dir = project.image_dir()
    image_file = project.image_file()

    mkinitcpio(project)

    print("squashfs image dir %s" % image_dir)
    if not image_dir.endswith("/"):
        image_dir += "/"
    
    temp = tempfile.NamedTemporaryFile(mode='w', delete=False)
    temp.write("\n".join(get_exclude_list(project)))
    temp.close()

    mksquashfs_cmd = 'mksquashfs "%s" "%s" -noappend -comp %s -ef "%s"' % (
        image_dir, image_file, project.squashfs_comp_type, temp.name)
    run(mksquashfs_cmd)
    os.unlink(temp.name)

    with open(os.path.join(project.work_dir, "finished.txt"), 'w') as _file:
        _file.write("pack-live")

def make_image(project):
    global bus
    print("Preparing install image...")
    xterm_title("Preparing install image")

    try:
        repo = project.get_repo()
        repo_dir = project.image_repo_dir()
        image_dir = project.image_dir(clean=True)
        
        run('pisi --yes-all -D"%s" ar pisilinux-install %s --ignore-check' % (image_dir, repo_dir + "/pisi-index.xml.bz2"))

        if project.type == "install":
            if project.all_install_image_packages:
                install_image_packages = project.all_install_image_packages
            else:
                install_image_packages = repo.full_deps("yali")
            run('pisi --yes-all --ignore-comar --ignore-dep -D"%s" it %s' % (image_dir, " ".join(install_image_packages)))
            if project.plugin_package:
                run('pisi --yes-all --ignore-comar -D"%s" it %s' % (image_dir, project.plugin_package))
        else:
            install_packages(project)

            # Canli masaustu yapilandirmasi: SDDM autologin (User=pisi),
            # pisi kullanicisi, KDE masaustu, kurulum araci girdileri.
            # Atlanirsa canli sistem login ekraninda kalir.
            from app.repotools.config_ops import setup_live_desktop
            setup_live_desktop(project)

            # Live USB'de vfat modulunun boot sirasinda yuklenmesi icin
            # (calisan ISO'da modules.autoload.d/kernel-6.18 -> "vfat")
            try:
                _kver = repo.packages["kernel"].version
                _adir = os.path.join(image_dir, "etc/modules.autoload.d")
                os.makedirs(_adir, exist_ok=True)
                # DIZIN degil, duz dosya (calisan ISO'da da dosya):
                #   /etc/modules.autoload.d/kernel-6.18  ->  "vfat"
                _afile = os.path.join(
                    _adir, "kernel-%s" % ".".join(_kver.split(".")[:2]))
                if os.path.isdir(_afile):
                    # Onceki hatali calistirmadan kalan dizini temizle
                    shutil.rmtree(_afile, ignore_errors=True)
                with open(_afile, "w") as _f:
                    _f.write("vfat\n")
                print("modules.autoload: %s -> vfat" % _afile)
            except (KeyError, AttributeError, TypeError) as e:
                print("UYARI: kernel surumu alinamadi (%s); autoload yazilmadi" % e)

        try:
            run('/bin/mount --bind /proc %s/proc' % image_dir)
            run('/bin/mount --bind /sys %s/sys' % image_dir)
            run('/bin/mount --bind /dev %s/dev' % image_dir)
            run('/bin/mount --bind /dev/pts %s/dev/pts' % image_dir)
            
            # comar and pisi config
            chroot_comar(image_dir)
            
            # Diagnostics before pisi
            print("DEBUG: Checking socket inside chroot...")
            run('chroot "%s" ls -l /run/dbus/system_bus_socket' % image_dir, ignore_error=True)
            run('chroot "%s" ls -l /var/run/dbus/system_bus_socket' % image_dir, ignore_error=True)
            
            run('chroot "%s" /usr/bin/env DBUS_SYSTEM_BUS_ADDRESS=unix:path=/var/run/dbus/system_bus_socket /usr/bin/pisi configure-pending baselayout' % image_dir)

            # ONEMLI: baselayout TEK BASINA yetmez. Diger paketlerin
            # yapilandirmasi (sddm, xdm, elogind, cups...) bekleyen
            # durumda kalir ve servisler etkinlestirilmez. Sonuc:
            # /etc/mudur/services/enabled/ bos kalir, canli sistem
            # display-manager olmadan metin login istemine ("pisilinux
            # login:") duser.
            # Calisan ISO'da bu adim "pisi configure-pending -dv" ile
            # yapiliyor; hata verirse dbus yeniden baslatilip tekrar
            # deneniyor.
            print("Configuring pending packages (all)...")
            _rc = run('chroot "%s" /usr/bin/env DBUS_SYSTEM_BUS_ADDRESS=unix:path=/var/run/dbus/system_bus_socket /usr/bin/pisi configure-pending -dv' % image_dir,
                      ignore_error=True)
            if _rc != 0:
                print("configure-pending -dv basarisiz (%s), dbus yeniden baslatiliyor" % _rc)
                run('chroot "%s" service dbus restart' % image_dir, ignore_error=True)
                run('chroot "%s" /usr/bin/env DBUS_SYSTEM_BUS_ADDRESS=unix:path=/var/run/dbus/system_bus_socket /usr/bin/pisi configure-pending -dv' % image_dir,
                    ignore_error=True)

            # Servisler etkinlesti mi? Etkin degilse canli sistem
            # metin login'inde kalir; sessizce gecmeyelim.
            _svc = os.path.join(image_dir, "etc/mudur/services/enabled")
            _enabled = sorted(os.listdir(_svc)) if os.path.isdir(_svc) else []
            if _enabled:
                print("Etkin servisler: %s" % ", ".join(_enabled))
                if "sddm" not in _enabled and "lightdm" not in _enabled:
                    print("  UYARI: display-manager servisi etkin degil; "
                          "canli sistem metin login'inde kalir")
            else:
                print("  UYARI: /etc/mudur/services/enabled bos; hicbir "
                      "servis etkin degil")

            # ------------------------------------------------------------------
            # Canli kullanici (SDDM autologin hedefi) ve canli inittab
            #
            # SDDM "User=pisi" ile otomatik giris yapar; ancak bu kullanici
            # imajda yoksa autologin gerceklesmez ve greeter sifre sorar.
            # Kullaniciyi referans araçtaki gibi COMAR (baselayout)
            # uzerinden olustur. COMAR calismazsa useradd ile tamamla.
            # ------------------------------------------------------------------
            print("Creating live user 'pisi'...")
            # uid 1000 cakismasi olmasin: once yabanci insan kullanicilarini at
            sanitize_live_users(image_dir)
            connectToDBus(image_dir)
            if bus:
                try:
                    obj = bus.get_object("tr.org.pardus.comar",
                                         "/package/baselayout")
                    obj.setUser(0, "", "", "", "pisilinux", "",
                                dbus_interface="tr.org.pardus.comar.User.Manager")
                except Exception as e:
                    print("  UYARI: setUser(root) basarisiz: %s" % e)

                if project.type != "install":
                    try:
                        obj.addUser(
                            1000, "pisi", "Pisi Linux", "/home/pisi",
                            "/bin/bash", "live",
                            ["wheel", "users", "lp", "lpadmin", "cdrom",
                             "floppy", "disk", "audio", "video", "power",
                             "dialout"],
                            [], [],
                            dbus_interface="tr.org.pardus.comar.User.Manager")
                        print("  pisi kullanicisi olusturuldu (COMAR)")
                    except Exception as e:
                        print("  UYARI: COMAR addUser basarisiz: %s" % e)

            _pw = os.path.join(image_dir, "etc/passwd")
            _has_pisi = False
            if os.path.isfile(_pw):
                with open(_pw) as _f:
                    _has_pisi = any(l.startswith("pisi:") for l in _f)

            if project.type != "install" and not _has_pisi:
                print("  UYARI: pisi yok; useradd ile olusturuluyor")
                # Yalnizca imajda GERCEKTEN var olan gruplari ekle;
                # olmayan bir grup useradd'i tamamen basarisiz eder.
                _wanted = ["users", "lp", "lpadmin", "cdrom", "floppy",
                           "disk", "audio", "video", "power", "dialout"]
                _existing = set()
                _grp = os.path.join(image_dir, "etc/group")
                if os.path.isfile(_grp):
                    with open(_grp) as _f:
                        for _l in _f:
                            _existing.add(_l.split(":", 1)[0])
                _extra = [g for g in _wanted if g in _existing]
                _cmd = ('chroot "%s" /usr/sbin/useradd -u 1000 -m '
                        '-d /home/pisi -s /bin/bash -g wheel' % image_dir)
                if _extra:
                    _cmd += " -G %s" % ",".join(_extra)
                _cmd += ' -c "Pisi Linux" pisi'
                run(_cmd, ignore_error=True)
                run('chroot "%s" /usr/bin/passwd -d pisi' % image_dir,
                    ignore_error=True)
                if os.path.isfile(_pw):
                    with open(_pw) as _f:
                        _has_pisi = any(l.startswith("pisi:") for l in _f)

            if project.type != "install":
                if _has_pisi:
                    print("  SDDM autologin hedefi: pisi (uid 1000) OK")
                else:
                    print("  UYARI: pisi kullanicisi OLUSMADI; canli sistem "
                          "login ekraninda kalir")

            if project.type != "install" and _has_pisi:
                # Parola her durumda "live" olsun (COMAR veya useradd).
                run('chroot "%s" /bin/sh -c \'echo "pisi:live" | '
                    '/usr/sbin/chpasswd\'' % image_dir, ignore_error=True)

                _sh = os.path.join(image_dir, "etc/shadow")
                _pw_ok = False
                if os.path.isfile(_sh):
                    with open(_sh) as _f:
                        for _l in _f:
                            _p = _l.rstrip("\n").split(":")
                            if _p and _p[0] == "pisi" and len(_p) > 1:
                                _pw_ok = _p[1] not in ("", "!", "*", "!!")
                                break
                print("  pisi parolasi: live -> %s"
                      % ("OK" if _pw_ok else "UYARI: dogrulanamadi"))

                # Son kez: baska insan kullanicisi sizmadi mi?
                sanitize_live_users(image_dir)

            # Ev dizini sahibi: calisan ISO'da pisi:wheel, mod 711
            run('chroot "%s" /bin/chown -R pisi:wheel /home/pisi' % image_dir,
                ignore_error=True)
            run('chroot "%s" /bin/chmod 711 /home/pisi' % image_dir,
                ignore_error=True)

            # Canli acilis icin inittab.live -> /etc/inittab
            _live_init = os.path.join(image_dir,
                                      "usr/share/baselayout/inittab.live")
            _etc_init = os.path.join(image_dir, "etc/inittab")
            if os.path.isfile(_live_init):
                try:
                    os.replace(_live_init, _etc_init)
                    print("inittab.live -> etc/inittab")
                except OSError as e:
                    print("UYARI: inittab.live uygulanamadi: %s" % e)

            # Ortam dosyasinin yeniden olusturulmasini zorla
            _prof = os.path.join(image_dir, "etc/profile.env")
            if os.path.isfile(_prof):
                try:
                    os.utime(_prof, (1, 1))
                except OSError:
                    pass
        finally:
            run('umount -l %s/dev/pts' % image_dir, ignore_error=True)
            run('umount -l %s/dev' % image_dir, ignore_error=True)
            run('umount -l %s/proc' % image_dir, ignore_error=True)
            run('umount -l %s/sys' % image_dir, ignore_error=True)

        # PipeWire oturum altyapisi: systemd'siz sistemde ses sunucusu
        # kullanici oturumunda baslatilmali. X11 ve Wayland icin ortak
        # (XDG autostart oturum tipinden bagimsiz calisir).
        #
        # Buraya, paketler kurulduktan ve chroot islemleri bittikten
        # SONRA konur; squashfs'e paketlenmeden hemen once.
        from app.repotools.audio_ops import setup_audio_stack
        setup_audio_stack(project)

        finished_path = os.path.join(project.work_dir, "finished.txt")
        with open(finished_path, 'w') as _file:
            _file.write("make-live")
    except KeyboardInterrupt:
        print("Keyboard Interrupt: make_image() cancelled.")
        sys.exit(1)
