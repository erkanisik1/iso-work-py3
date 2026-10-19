#!/usr/bin/python3
# -*- coding: utf-8 -*-

import os
import shutil
import re
import glob
from .utility import run, xterm_title
from .image_ops import overlay, unoverlay

def setup_efi(project):
    image_dir = project.image_dir()
    iso_dir = project.iso_dir()

    def copy(src, dest):
        dest_full = os.path.join(iso_dir, dest)
        os.makedirs(os.path.dirname(dest_full), exist_ok=True)
        run('cp -PR "%s" "%s"' % (src, dest_full))

    # Copy EFI bootloader from data/efi
    if os.path.exists("./data/efi"):
        run('cp -PR ./data/efi/* "%s/."' % iso_dir)

    # isomounts: miso hook'u canli sistemi kurarken bu dosyayi okur
    # (/bootmnt/<miso basedir>/isomounts -> "pisi.sqfs x86_64 / squashfs").
    # ISO'da bulunmazsa hook neyi mount edecegini bilemez ve canli sistem
    # acilmaz. Refactor sirasinda bu adim kaybolmusdu; eski maker.py'de
    # "copy('./data/isomounts', 'pisi')" olarak vardi.
    if os.path.isfile("./data/isomounts"):
        copy("./data/isomounts", "pisi")
    else:
        print("UYARI: ./data/isomounts bulunamadi; miso hook'u canli "
              "sistemi acamaz")

    # Copy kernel and initrd for EFI
    os.makedirs("%s/EFI/pisi" % iso_dir, exist_ok=True)
    path = os.path.join(image_dir, "boot")
    for name in os.listdir(path):
        if name.startswith("kernel") or name.startswith("initr") or name.endswith(".bin"):
            if name.startswith("kernel"):
                copy(os.path.join(path, name), "EFI/pisi/kernel.efi")
            elif name.startswith("initr"):
                copy(os.path.join(path, name), "EFI/pisi/initrd.img")

def mkinitcpio(project):
    try:
        image_dir = project.image_dir()
        unoverlay(project, "dev", ignore_error=True)
        run('umount -l %s/dev/pts' % image_dir, ignore_error=True)
        run('umount -l %s/dev' % image_dir, ignore_error=True)
        run('umount -l %s/proc' % image_dir, ignore_error=True)
        run('umount -l %s/sys' % image_dir, ignore_error=True)

        def chrun(cmd):
            run('chroot "%s" %s' % (image_dir, cmd))

        def copy2(src, dest):
            run('cp -PR "%s" "%s"' % (src, os.path.join(image_dir, dest)))

        rep = project.get_repo()
        if "mkinitcpio" in project.all_install_image_packages:
            prog = "mkinitcpio"
            binary = "/usr/bin/mkinitcpio"
            config_path = "/etc/mkinitcpio-live.conf"
            extra_args = " -g /boot/initrd"
            copy2("./data/initcpio", "usr/lib")
            copy2("./data/mkinitcpio-live.conf", "etc")
        elif "mkinitramfs" in project.all_install_image_packages:
            prog = "mkinitramfs"
            binary = "/sbin/mkinitramfs-live"
            config_path = "/etc/initramfs.conf"
            extra_args = ""
            copy2("./data/initramfs/lib", "")
            copy2("./data/initramfs/sbin", "")

        try:
            run('/bin/mount --bind /proc %s/proc' % image_dir)
            run('/bin/mount --bind /sys %s/sys' % image_dir)
            run('/bin/mount --bind /dev %s/dev' % image_dir)
            run('/bin/mount --bind /dev/pts %s/dev/pts' % image_dir)

            kernel_version = rep.packages['kernel'].version

            # Kernel modul bagimliliklarini uret.
            #
            # Pisi cekirdek paketi depmod ciktisi (modules.dep, modules.alias,
            # modules.symbols, modules.devname) TASIMAZ; yalnizca derleme
            # sirasinda uretilen modules.builtin* dosyalarini icerir.
            # Eski mkinitramfs-live "Could not find module dependencies"
            # uyarisinda depmod'u kendisi calistiriyordu; modern mkinitcpio
            # icin bu fallback YOK. modules.dep olmadan add_modules() modul
            # adlarini cozemedigi icin tum moduller "module not found" ile
            # geciliyor ve initrd bos kaliyor:
            #     WARNING: No modules were added to the image.
            if prog == "mkinitcpio":
                chrun("depmod -a -b / %s" % kernel_version)

                # depmod'un nereye yazdigi kesin olsun: kmod'un bazi
                # surumleri usrmerge icin /usr/lib/modules kullanir.
                # Hangi yolun doluldugunu gor, yoksa baglanti kur.
                for _base in ("lib", "usr/lib"):
                    _dep = os.path.join(image_dir, _base, "modules",
                                        kernel_version, "modules.dep")
                    if os.path.isfile(_dep):
                        print("depmod cikti: %s" % _dep)
                        if _base == "usr/lib":
                            _link = os.path.join(image_dir, "lib/modules")
                            if not os.path.exists(_link):
                                os.symlink("/usr/lib/modules", _link)
                                print("  /lib/modules -> /usr/lib/modules baglantisi kuruldu")
                        break
                else:
                    print("UYARI: depmod modules.dep uretmedi; initrd yine bos "
                          "kalabilir. Elle kontrol edin: "
                          "%s/lib/modules/%s/modules.dep"
                          % (image_dir, kernel_version))

            chrun(" ".join([binary, "-k", kernel_version, "-c %s" % config_path, extra_args]))
        finally:
            run('umount -l %s/dev/pts' % image_dir, ignore_error=True)
            run('umount -l %s/dev' % image_dir, ignore_error=True)
            run('umount -l %s/proc' % image_dir, ignore_error=True)
            run('umount -l %s/sys' % image_dir, ignore_error=True)
            unoverlay(project, "dev", ignore_error=True)
    except KeyboardInterrupt:
        print("Keyboard Interrupt: mkinitcpio() cancelled.")
        import sys
        sys.exit(1)

def generate_grub_conf(project, kernel, initramfs):
    print("Generating grub.conf files...")
    xterm_title("Generating grub.conf files")
    image_dir = project.image_dir()
    iso_dir = project.iso_dir()

    grub_dict = {
        "kernel": kernel,
        "initramfs": initramfs,
        "title": project.title,
        "exparams": project.extra_params or ''
    }

    path = os.path.join(image_dir, "usr/share/grub/templates")
    dest = os.path.join(iso_dir, "pisi/boot/grub")
    os.makedirs(dest, exist_ok=True)
    for name in os.listdir(path):
        if name.startswith("menu"):
            with open(os.path.join(path, name), "r") as f:
                data = f.read()
            with open(os.path.join(dest, name), "w") as f:
                f.write(data % grub_dict)

def setup_grub(project):
    image_dir = project.image_dir()
    iso_dir = project.iso_dir()
    kernel = ""
    initramfs = ""

    path = os.path.join(iso_dir, "pisi/boot/grub")
    os.makedirs(path, exist_ok=True)

    def copy(src, dest):
        run('cp -P "%s" "%s"' % (src, os.path.join(iso_dir, dest)))

    path = os.path.join(image_dir, "boot")
    for name in os.listdir(path):
        if name.startswith("kernel") or name.startswith("initramfs") or name.startswith("initrd") or name.endswith(".bin"):
            if name.startswith("kernel"):
                kernel = name
            elif name.startswith("initramfs") or name.startswith("initrd"):
                initramfs = name
            copy(os.path.join(path, name), "pisi/boot/" + name)
    
    path = os.path.join(image_dir, "pisi/boot/grub")
    if os.path.exists(path):
        for name in os.listdir(path):
            copy(os.path.join(path, name), "boot/grub/" + name)

    generate_grub_conf(project, kernel, initramfs)

def generate_isolinux_conf(project):
    print("Generating isolinux config files...")
    xterm_title("Generating isolinux config files")

    params = project.extra_params or ''
    if "mkinitcpio" in project.all_install_image_packages:
        params += " misobasedir=pisi misolabel=pisilive overlay=free"

    if project.type == "live":
        params += " mudur=livecd"

    rescue_template = ""
    if project.type != "live":
        rescue_template = """
label rescue
    kernel /pisi/boot/kernel
    append initrd=/pisi/boot/initrd yali=rescue %s
""" % params

    isolinux_tmpl = """
default start
implicit 1
ui gfxboot bootlogo
prompt   1
timeout  200

label %s
    kernel /pisi/boot/kernel
    append initrd=/pisi/boot/initrd %s

%s

label harddisk
    localboot 0x80

label memtest
    kernel /pisi/boot/memtest

label hardware
    kernel hdt.c32
""" % (project.title, params, rescue_template)

    iso_dir = project.iso_dir()
    dest = os.path.join(iso_dir, "isolinux/isolinux.cfg")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "w") as f:
        f.write(isolinux_tmpl)

    image_dir = project.image_dir()
    gfx_cfg = os.path.join(image_dir, "usr/share/gfxtheme/pisilinux/install/gfxboot.cfg")
    if os.path.exists(gfx_cfg):
        with open(gfx_cfg, "r") as f:
            data = f.read()
        with open(os.path.join(iso_dir, "isolinux/gfxboot.cfg"), "w") as f:
            # Note: might need formatting if template has %s
            f.write(data)

def setup_isolinux(project):
    print("Generating isolinux files...")
    xterm_title("Generating isolinux files")

    image_dir = project.image_dir()
    iso_dir = project.iso_dir()
    
    os.makedirs(os.path.join(iso_dir, "isolinux"), exist_ok=True)
    os.makedirs(os.path.join(iso_dir, "pisi/boot"), exist_ok=True)

    def copy(src, dest):
        run('cp -P "%s" "%s"' % (src, os.path.join(iso_dir, dest)))

    path = os.path.join(image_dir, "boot")
    for name in os.listdir(path):
        if name.startswith("kernel") or name.startswith("initr") or name.endswith(".bin"):
            if name.startswith("kernel"):
                copy(os.path.join(path, name), "pisi/boot/kernel")
            elif name == "initrd" or name.startswith("initramfs"):
                copy(os.path.join(path, name), "pisi/boot/initrd")
            else:
                copy(os.path.join(path, name), "pisi/boot/%s" % name)

    tmplpath = os.path.join(image_dir, "usr/share/gfxtheme/pisilinux/install")
    if os.path.exists(tmplpath):
        dest = os.path.join(iso_dir, "isolinux")
        for name in os.listdir(tmplpath):
            if name != "gfxboot.cfg":
                copy(os.path.join(tmplpath, name), "isolinux/%s" % name)

    generate_isolinux_conf(project)

    syslinux_biost_dir = os.path.join(image_dir, "usr/lib/syslinux/bios")
    if os.path.exists(syslinux_biost_dir):
        for bin_file in ["isolinux.bin", "isohdpfx.bin", "hdt.c32", "ldlinux.c32", "libcom32.c32", "libutil.c32", "vesamenu.c32", "libmenu.c32", "libgpl.c32", "gfxboot.c32"]:
            src_bin = os.path.join(syslinux_biost_dir, bin_file)
            if os.path.exists(src_bin):
                copy(src_bin, "isolinux/%s" % bin_file)

    pci_ids = os.path.join(image_dir, "usr/share/hwdata/pci.ids")
    if os.path.exists(pci_ids):
        copy(pci_ids, "isolinux/pci.ids")

    copy(os.path.join(image_dir, "boot/memtest"), "pisi/boot/memtest")

def _iso_label(title):
    """ISO 9660 etiketi: mimari/paketleme son ekleri atilir, 30 karakter."""
    label = title.replace(" ", "_").replace("-", "_")
    for suf in ("cpio", "squashfs", "x86_64", "i686", "aarch64", "arm64"):
        while label.endswith("_" + suf):
            label = label[:-(len(suf) + 1)]
    if len(label) > 30:
        label = label[:30]
    return label


def load_grub_params(project, initcpio=False):
    """
    image_dir/grub.cfg dosyasini grub.cfg.template ile doldurur.

    UEFI grub.cfg'i ekran goruntulerini (/EFI/pisi/kernel.efi) ve
    initrd'yi (/EFI/pisi/initrd.img) gosterir; ayrica ozel miso
    hook'unun ihtiyacı olan iso_label= ve iso_filename= degerlerini
    kernel komut satirina ekler.
    """
    image_dir = project.image_dir()

    ver = [v for v in project.title.split(" ") if len(v.split(".")) > 1]
    ver = ver[0] if ver else "0.0"

    grub_dir = "/grub/themes/pisilinux/"
    pf2s = glob.glob(os.path.join(image_dir, "usr/share", grub_dir + "*.pf2"))
    loadfonts = "\n".join(["loadfont ($root)/boot" + grub_dir + os.path.basename(f)
                           for f in pf2s])

    rescue = """menuentry "PisiLinux %(version)s UEFI - %(res_trans)s" {
    load_video
    linux /EFI/pisi/kernel.efi yali=rescue
    initrd /EFI/pisi/initrd.img
}"""
    rescue_tr = rescue % {"version": ver, "res_trans": "Kurtarici"}
    rescue_eng = ""

    iso_label = _iso_label(project.title)
    iso_filename = os.path.basename(project.iso_file(clean=False))
    iso_cmdline = "iso_label=%s iso_filename=%s" % (iso_label, iso_filename)

    params = ""
    if initcpio:
        params = 'misobasedir=pisi misolabel=PisiLive overlay=free'

    tmpl = os.path.join(image_dir, "grub.cfg")
    if not os.path.isfile(tmpl):
        print("UYARI: %s yok; EFI grub.cfg uretilemiyor" % tmpl)
        return False

    with open(tmpl, "r") as f:
        data = f.read()

    with open(tmpl, "w") as f:
        f.write(data % {"fonts": loadfonts, "initcpio": params,
                        "version": ver, "rescue_tr": rescue_tr,
                        "rescue_eng": rescue_eng, "iso_cmdline": iso_cmdline})
    return True


def make_EFI(project):
    """
    UEFI icin GRUB bootloader uretir.

    Refactor sirasinda bu adim kayboldu ve "not implemented" notuyla
    yorumlandi. Sonuc: ISO'nun EFI dizininde yalnizca shim
    (./data/efi) kaliyordu; shim'in zincirlemesi gereken grubx64.efi
    ISO'da bulunmadigi icin UEFI'de menu HIC ACILMIYORDU.

    Uretilenlar:
      1. iso/EFI/boot/bootx64.efi   data/efi_grub'daki hazir GRUB
                                     (El Torito yolu buraya bakar)
      2. iso/EFI/BOOT/grub2/...     GRUB temasi
      3. efi.img:EFI/BOOT/bootx64.efi  grub2-mkstandalone ile uretilen
                                     GRUB (yalnizca efi.img'e konur)
    """
    print("Generating EFI (GRUB)...")
    xterm_title("Generating EFI (GRUB)")

    image_dir = project.image_dir()
    iso_dir = project.iso_dir()
    work_dir = project.work_dir
    efi_tmp = project.efi_tmp_path_dir(clean=True)

    def chrun(cmd):
        run('chroot "%s" %s' % (image_dir, cmd))

    # 0) Onceki build'den kalan buyuk/kucuk harf karisikligini temizle.
    #    ISO9660 + Joliet'te EFI/boot ve EFI/BOOT tek dizin olarak
    #    gorunur; ikisi birden varsa UEFI yukleme yolu belirsizlesir.
    stray = os.path.join(iso_dir, "EFI/BOOT")
    if os.path.isdir(stray):
        shutil.rmtree(stray, ignore_errors=True)
        print("  eski EFI/BOOT (buyuk harf) temizlendi")

    # 1) ISO'nun bootloader'i: data/efi_grub (EFI/boot altinda gelir)
    if os.path.isdir("./data/efi_grub/EFI"):
        run('cp -rf ./data/efi_grub/EFI "%s/"' % iso_dir, ignore_error=True)
        _b = os.path.join(iso_dir, "EFI/boot/bootx64.efi")
        print("  data/efi_grub -> EFI/boot (%s bayt)"
              % (os.path.getsize(_b) if os.path.isfile(_b) else 0))
    else:
        print("UYARI: ./data/efi_grub/EFI yok; UEFI menusu acilmayabilir")

    # 2) GRUB temasi -> EFI/BOOT/grub2/themes/pisilinux
    #    grub.cfg.template su yollari okur:
    #      ($root)/EFI/BOOT/grub2/themes/pisilinux/{terminus-14.pf2,
    #                                               theme.txt,
    #                                               unifont-regular-16.pf2}
    #    Tema kopyalanmazsa GRUB "file not found" basar, grafik menu acilmaz.
    theme_src = os.path.join(image_dir, "usr/share/grub/themes/pisilinux")
    theme_dst = os.path.join(iso_dir, "EFI/BOOT/grub2/themes/pisilinux")
    if os.path.isdir(theme_src):
        shutil.copytree(theme_src, theme_dst, dirs_exist_ok=True)
        print("  EFI/BOOT/grub2/themes/pisilinux kopyalandi")

        # unifont-regular-16.pf2 Pisi'de yok (yalnizca fontconfig
        # yapilandirmasi var). GRUB eksik fontu hata ile gectigi icen
        # en yakin 16px fontla ad altinda sagliyoruz.
        unifont = os.path.join(theme_dst, "unifont-regular-16.pf2")
        if not os.path.isfile(unifont):
            for alt in ("DejaVuSans-16.pf2", "ascii.pf2", "terminus-14.pf2"):
                p = os.path.join(theme_dst, alt)
                if os.path.isfile(p):
                    shutil.copy2(p, unifont)
                    print("  unifont-regular-16.pf2 yerine %s kullanildi" % alt)
                    break
    else:
        print("UYARI: usr/share/grub/themes/pisilinux yok")

    # 3) mkgrubx64.sh /boot/grub2/fonts/unicode.pf2 bekliyor ama Pisi
    #    fontu /usr/share/grub/unicode.pf2 altinda tutuyor.
    fonts_dir = os.path.join(image_dir, "boot/grub2/fonts")
    os.makedirs(fonts_dir, exist_ok=True)
    for src in ("/usr/share/grub/unicode.pf2", "/usr/share/grub/ascii.pf2"):
        s = os.path.join(image_dir, src.lstrip("/"))
        if os.path.isfile(s) and not os.path.isfile(
                os.path.join(fonts_dir, os.path.basename(s))):
            shutil.copy2(s, fonts_dir)

    # 4) Gorsuntunun cekirdegi/initrd'siyle fat GRUB uret.
    #    Bu GRUB YALNIZCA efi.img'e konur; ISO'nun bootloader'i
    #    data/efi_grub'daki hazir olanidir (El Torito yolu
    #    -e EFI/boot/bootx64.efi oraya bakar).
    grub_efi = os.path.join(image_dir, "grubx64.efi")
    if os.path.isfile("./data/mkgrubx64.sh") and os.path.isfile("./data/grub.cfg.template"):
        run("cp ./data/mkgrubx64.sh %s/" % image_dir)
        run("cp ./data/grub.cfg.template %s/grub.cfg" % image_dir)
        load_grub_params(project, initcpio=True)
        chrun("/mkgrubx64.sh -e /grubx64.efi")
        if os.path.isfile(grub_efi):
            print("  grubx64.efi uretildi (%s bayt)" % os.path.getsize(grub_efi))
        else:
            print("UYARI: grubx64.efi uretilemedi")
        run("rm -f %s/mkgrubx64.sh" % image_dir)
        run("rm -f %s/grub.cfg" % image_dir)
    else:
        print("UYARI: mkgrubx64.sh veya grub.cfg.template yok")

    # 5) 20 MB FAT imaj (etiket PisiLinux). Her build'de YENIDEN uretilir;
    #    aksi halde onceki build'den bayat kalir.
    run("rm -f %s/efi.img" % work_dir)
    run("dd if=/dev/zero bs=1M count=20 of=%s/efi.img" % work_dir)
    run("mkfs.vfat -n PisiLinux %s/efi.img" % work_dir)
    run("mount %s/efi.img %s" % (work_dir, efi_tmp))
    try:
        dst = os.path.join(efi_tmp, "EFI/BOOT")
        os.makedirs(dst, exist_ok=True)

        if os.path.isfile(grub_efi):
            shutil.copy2(grub_efi, os.path.join(dst, "bootx64.efi"))
            print("  efi.img/EFI/BOOT/bootx64.efi <- grubx64.efi")
        else:
            _fb = os.path.join(iso_dir, "EFI/boot/bootx64.efi")
            if os.path.isfile(_fb):
                shutil.copy2(_fb, os.path.join(dst, "bootx64.efi"))
                print("  efi.img/EFI/BOOT/bootx64.efi <- data/efi_grub (yedek)")

        for g in ("tr.gkb", "us.gkb"):
            _s = os.path.join(iso_dir, "EFI/boot", g)
            if os.path.isfile(_s):
                shutil.copy2(_s, os.path.join(dst, g))

        _out = os.path.join(dst, "bootx64.efi")
        print("  efi.img hazir: EFI/BOOT/bootx64.efi (%s bayt)"
              % (os.path.getsize(_out) if os.path.isfile(_out) else 0))
    finally:
        run("umount %s" % efi_tmp, ignore_error=True)
        run("umount -l %s" % efi_tmp, ignore_error=True)


def make_iso(project):
    try:
        iso_dir = project.iso_dir(clean=True)
        iso_file = project.iso_file(clean=True)
        work_dir = project.work_dir
        image_dir = project.image_dir()
        image_file = project.image_file()
        image_path = os.path.join(iso_dir, "pisi")

        os.makedirs(image_path, exist_ok=True)
        os.link(image_file, os.path.join(iso_dir, "pisi/pisi.sqfs"))

        def copy(src, dest):
            dest_full = os.path.join(iso_dir, dest)
            if os.path.isdir(src):
                if os.path.exists(dest_full):
                    shutil.rmtree(dest_full)
                shutil.copytree(src, dest_full, ignore=shutil.ignore_patterns(".svn"))
            else:
                shutil.copy2(src, dest_full)

        if project.release_files:
            path = os.path.expanduser(project.release_files)
            if os.path.exists(path):
                for name in os.listdir(path):
                    if name != ".svn":
                        copy(os.path.join(path, name), name)

        setup_isolinux(project)
        setup_efi(project)
        make_EFI(project)
        copy("./data/.miso", "")
        run("cp -p %s/efi.img %s/." % (work_dir, iso_dir), ignore_error=True)
        os.makedirs(os.path.join(iso_dir, "boot"), exist_ok=True)
        run("ln -s %s/pisi/pisi.sqfs %s/boot/pisi.sqfs" % (iso_dir, iso_dir))

        publisher = "Pisi GNU/Linux https://pisilinux.org"
        application = "Pisi GNU/Linux Live Media"
        # Etiket, EFI grub.cfg'inin kernel'e bildirdigi iso_label= ile
        # ayni olmak ZORUNDA. load_grub_params() _iso_label() uretiyor;
        # burada sabit bir deger kullanmak iki tarafi ayrilir ve canli
        # sistem ISO'yu bulamaz (13 Ekim'de ikisi de Pisi_Linux_2.4.4_KDE6
        # idi, uyumsuzluk refactor ile girdi).
        label = _iso_label(project.title)

        # xorriso komutu, calisan ISO ile (yalirs1) birebir ayni olmali.
        #
        # Kritik olan ucuncu arguman:
        #   -isohybrid-mbr isolinux/isohdpfx.bin   hibrit MBR yazar
        #   -append_partition 2 0xef <iso>/efi.img  GPT'de EFI sistem
        #                                        bolumu olusturur
        # UEFI firmware (ve VirtualBox) ISO'nun GPT'sini okuyup EFI
        # sistem bolumunu arar; bu iki arguman olmazsa hibrit MBR
        # kurulmaz ve UEFI'de menu HIC ACILMAZ.
        #
        # El Torito EFI girisi de dogrudan GRUB'a degil, 20 MB FAT
        # imaja (-e efi.img) isaret eder; make_EFI() onu uretir.
        new_iso = 'xorriso -as mkisofs \
        -rational-rock \
        -R -r \
        -iso-level 3 \
        -full-iso9660-filenames -omit-period \
        -joliet \
        -J -joliet-long \
        -f \
        -V "%s" \
        -cache-inodes \
        -o "%s" \
        -isohybrid-mbr "%s/isolinux/isohdpfx.bin" \
        -c isolinux/boot.cat \
        -b isolinux/isolinux.bin \
        -no-emul-boot -boot-load-size 4 -boot-info-table \
        -eltorito-alt-boot \
        -e efi.img \
        -isohybrid-gpt-basdat -no-emul-boot \
        -append_partition 2 0xef %s/efi.img \
        -partition_cyl_align all \
        -preparer "prepared by mkpisiiso" \
        -publisher "%s" -A "%s" "%s"' % (
            label, iso_file, iso_dir, iso_dir,
            publisher, application, iso_dir)

        run(new_iso)

        with open(os.path.join(project.work_dir, "finished.txt"), 'w') as _file:
            _file.write("make-iso")
    except KeyboardInterrupt:
        print("Keyboard Interrupt: make_iso() cancelled.")
        import sys
        sys.exit(1)
