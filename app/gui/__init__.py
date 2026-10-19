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

# Qt
import os
import locale
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTranslator, QLocale

# Arayuz tercihleri (dil secimi)
from app.gui import settings as gui_settings


def _apply_language_env():
    """Kayitli dil tercihini ortam degiskenlerine yazar.

    ONEMLI: main.py gettext'i import aninda kuruyor. Bu yuzden dil
    ayari MainWindow import edilmeden ONCE ortama yazilmali.

    Doner: kullanilacak dil kodu (kayitli dil yoksa sistem dili).
    """
    system_locale = QLocale.system().name()  # orn. 'tr_TR'
    saved = gui_settings.get_saved_language()
    if saved:
        os.environ["LANGUAGE"] = saved
        # Bazi araclar LANGUAGE'i yok sayar; LANG'i da esle.
        os.environ["LANG"] = saved + ".UTF-8"
        return saved
    return system_locale


def gui(args):
    # If no style is specified, use breeze as default
    if not any(arg.startswith("-style") for arg in args):
        args.append("-style")
        args.append("breeze")

    # Create applicatin
    app = QApplication(args)

    # Dil secimi: kayitli tercih sistem dilinden onceliklidir.
    # MainWindow bu noktadan SONRA import edilmeli.
    system_locale = _apply_language_env()

    from app.gui.main import MainWindow

    # Setup translations
    translator_code = QTranslator()
    translator_ui = QTranslator()
    translator_qt = QTranslator()
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

    # Try to load translation files
    qm_code = os.path.join(project_root, 'locale', system_locale, 'LC_MESSAGES', 'pisiman.qm')
    qm_ui = os.path.join(project_root, 'locale', system_locale, 'LC_MESSAGES', 'pisiman_ui.qm')
    # Qt'nin kendi diyalog dizgileri (sistemde qt_tr.qm yoksa diye uygulama ile gelir)
    qm_qt = os.path.join(project_root, 'locale', system_locale, 'LC_MESSAGES', 'qt_dialogs.qm')

    loaded = []
    if os.path.exists(qm_code) and translator_code.load(qm_code):
        app.installTranslator(translator_code)
        loaded.append("code")

    if os.path.exists(qm_ui) and translator_ui.load(qm_ui):
        app.installTranslator(translator_ui)
        loaded.append("UI")

    if os.path.exists(qm_qt) and translator_qt.load(qm_qt):
        app.installTranslator(translator_qt)
        loaded.append("Qt")

    if loaded:
        print(f"Loaded translations ({system_locale}): {', '.join(loaded)}")
    else:
        print(f"No translations found for {system_locale}")

    # Load and apply modern style
    try:
        qss_path = os.path.join(os.path.dirname(__file__), "ui", "style.qss")
        if os.path.exists(qss_path):
            with open(qss_path, "r") as f:
                app.setStyleSheet(f.read())
    except Exception as e:
        print(f"Style loading error: {e}")

    # Show main window
    mainWindow = MainWindow(args)
    mainWindow.show()

    app.setActiveWindow(mainWindow)

    # Close application if there's no window
    app.lastWindowClosed.connect(app.quit)

    # Go go go!
    app.exec()
