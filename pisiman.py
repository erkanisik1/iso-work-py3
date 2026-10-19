#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2005-2009, TUBITAK/UEKAE
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation; either version 2 of the License, or (at your option)
# any later version.
#
# Please read the COPYING file.
#

# System
import os
import sys
import time
import fcntl
from app.repotools import packages


def acquire_build_lock(work_dir):
    """
    Ayni WorkDir uzerinde ikinci bir kurulumu engeller.

    make_image() her calistiginda image/ dizinini image_dir(clean=True)
    ile SILER ve 1173 paketi bastan kurar. GUI'de "make-live" ve "make"
    butonlarinin ikisi de make_image() cagirir; art arda basildiginda
    ikinci kurulum oncekinin 40 dakikasini yok eder.

    Bu kilit sayesinde ayni WorkDir'de ayni anda tek kurulum olur.
    Islem bitince kilit otomatik birakilir (dosya taniticiya baglidir),
    yanlislikla kalici bir kilit dosyasi birakmaz.

    Dondurulmus (SIGSTOP) bir surec kilidi tutmaya devam eder; bu
    durumda asagidaki mesaj gorunur ve kullanici sureci oldurebilir.

    Doner:
        dosya nesnesi  -> kilit alindi, kurulum devam edebilir
        None           -> baska bir kurulum kilidi tutuyor, ABARTILMAMALI
    Kilit dosyasi acilamazsa uyari verip None yerine gecici bir
    nesne doner: koruma kullanilamaz ama kurulum engellenmez.
    """
    try:
        os.makedirs(work_dir, exist_ok=True)
        path = os.path.join(work_dir, ".build.lock")
        fh = open(path, "w")
    except OSError as e:
        print("UYARI: kilit dosyasi olusturulamadi (%s); koruma devre disi" % e)
        return open(os.devnull, "w")

    try:
        fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (IOError, OSError):
        print("")
        print("=" * 62)
        print("HATA: bu dizin uzerinde zaten bir kurulum calisiyor:")
        print("      %s" % work_dir)
        print("")
        print("Yeni kurulum oncekinin yaptiklarini SILER. Devam etmek")
        print("istediginizden emin degilseniz o sureci durdurun:")
        print("      pkill -f 'pisiman.py make'")
        print("=" * 62)
        print("")
        fh.close()
        return None

    # sahibini gorunur kil
    try:
        fh.write("%d\n%s\n" % (os.getpid(), time.strftime("%Y-%m-%d %H:%M:%S")))
        fh.flush()
    except IOError:
        pass
    return fh


def maker(op, project_file):
    from app.repotools import maker, project

    project = project.Project()
    err = project.open(project_file)
    if err:
        print("ERROR: %s" % err)
        return

    # Ayni WorkDir uzerinde ayni anda tek kurulum calissin.
    # make_image() image/ dizinini silip bastan kurdugu icin ikinci bir
    # calistirma ilkinin sonucunu yok eder.
    _lock = None
    if op in ("make", "make-live", "install-live"):
        _lock = acquire_build_lock(project.work_dir)
        if _lock is None:
            sys.exit(1)

    start = time.time()

    if op == "make" or op == "make-repo":
        # remove project folder image folder
        update_repo = True
        while True:
            try:
                project.get_repo(update_repo=update_repo)
            except packages.ExIndexBogus:
                print("ERROR: Unable to load package index. URL is wrong, or file is corrupt.")
                return
            except packages.ExPackageCycle as e:
                cycle = " > ".join(e.args[0])
                print("ERROR: package index has errors. Cyclic dependency found:\n  %s." % cycle)
                return
            except packages.ExPackageMissing as e:
                print("ERROR: Package index has errors. '%s' depends on non-existing '%s'." % (e.args))
                return
            missing_components, missing_packages = project.get_missing()

            if len(missing_components):
                print("WARNING: There are missing components. Removing.")
                print("\n".join(missing_components))
                if project.package_collections:
                    for component in missing_components:
                        for collection in project.package_collections:
                            if component in collection.packages.selectedComponents:
                                collection.packages.selectedComponents.remove(component)
                else:
                    for component in missing_components:
                        if component in project.selected_components:
                            project.selected_components.remove(component)
                update_repo = False
            if len(missing_packages):
                print("WARNING: There are missing packages. Removing.")
                print("\n".join(missing_packages))
                if project.package_collections:
                    for package in missing_packages:
                        for collection in project.package_collections:
                            if package in collection.packages.selectedPackages:
                                collection.packages.selectedPackages.remove(package)
                else:
                    for package in missing_packages:
                        if package in project.selected_packages:
                            project.selected_packages.remove(package)
                update_repo = False
            break
        maker.make_repos(project)

    if op == "check-repo":
        maker.check_repo_files(project)
    if op == "make" or op == "make-live":
        maker.make_image(project)
    # install-live
    # configure-live
    if op == "make" or op == "pack-live":
        maker.squash_image(project)
    if op == "make" or op == "make-iso":
        maker.make_iso(project)

    end = time.time()
    print("Total time is %s seconds." % (end - start))


def usage(app):
    print("Usage: %s [command] path/to/project.xml" % app)
    print()
    print("Commands:")
    print("  make-repo  : Make local repos")
    print("  check-repo : Check repo files")
    print("  make-live  : Install image")
    print("  pack-live  : Make squashfs")
    print("  make-iso   : Make ISO")
    print("  make       : Make all!")


def main(args):
    if len(args) == 2 and args[1] in ["help", "-h", "--help"]:
        usage(args[0])
    elif len(args) == 3:
        maker(args[1], args[2])
    else:
        from app import gui
        gui.gui(args)


if __name__ == '__main__':
    sys.exit(main(sys.argv))
