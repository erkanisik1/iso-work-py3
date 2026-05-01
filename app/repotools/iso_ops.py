#!/usr/bin/python3
# -*- coding: utf-8 -*-

import os
import shutil
import re
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
        # make_EFI(project) # FIXME: not implemented here yet
        copy("./data/.miso", "")
        run("cp -p %s/efi.img %s/." % (work_dir, iso_dir), ignore_error=True)
        os.makedirs(os.path.join(iso_dir, "boot"), exist_ok=True)
        run("ln -s %s/pisi/pisi.sqfs %s/boot/pisi.sqfs" % (iso_dir, iso_dir))

        publisher = "Pisi GNU/Linux https://pisilinux.org"
        application = "Pisi GNU/Linux Live Media"
        label = "PisiLive Minimal"

        new_iso = 'xorriso -as mkisofs \
        -f -V "%s" -o "%s" \
        -J -joliet-long -cache-inodes \
        -b isolinux/isolinux.bin \
        -c isolinux/boot.cat \
        -no-emul-boot \
        -boot-load-size 4 \
        -boot-info-table \
        -eltorito-alt-boot \
        -eltorito-platform efi \
        -e EFI/boot/bootx64.efi \
        -no-emul-boot \
        -isohybrid-gpt-basdat \
        -publisher "%s" -A "%s" "%s"' % (
            label, iso_file, publisher, application, iso_dir)

        run(new_iso)

        with open(os.path.join(project.work_dir, "finished.txt"), 'w') as _file:
            _file.write("make-iso")
    except KeyboardInterrupt:
        print("Keyboard Interrupt: make_iso() cancelled.")
        import sys
        sys.exit(1)
