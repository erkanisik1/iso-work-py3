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
"""Pisiman arayuz tercihleri (dil secimi gibi).

Ayar dosyasi: $XDG_CONFIG_HOME/pisiman/pisiman.conf (yoksa ~/.config/...).

Dil tercihi burada tutulur; boylece kullanici sectigi dil sonraki
acilislarda da gecerli olur. Kayit yoksa sistem dili kullanilir.
"""

import os

# app/gui/settings.py -> app/gui -> app -> proje koku (3 kademe)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
LOCALE_DIR = os.path.join(PROJECT_ROOT, "locale")

# Yerlesik gorunen adlar. Tabloda olmayan bir dil icin kod, varsa
# po dosyasindaki "Language:" degeri, yoksa kodun kendisi gosterilir.
LANGUAGE_NAMES = {
    "tr": "Türkçe",
    "en": "English",
    "de": "Deutsch",
    "fr": "Français",
    "es": "Español",
    "it": "Italiano",
    "ru": "Русский",
    "nl": "Nederlands",
    "pt": "Português",
    "pl": "Polski",
    "ar": "العربية",
    "el": "Ελληνικά",
    "az": "Azərbaycan dili",
    "fa": "فارسی",
}


def _config_dir():
    base = os.environ.get("XDG_CONFIG_HOME")
    if not base:
        base = os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(base, "pisiman")


def config_path():
    """Ayar dosyasinin tam yolu."""
    return os.path.join(_config_dir(), "pisiman.conf")


def get_saved_language():
    """Kayitli dil kodunu dondurur (orn. 'tr_TR'); kayit yoksa None."""
    try:
        with open(config_path()) as handle:
            for line in handle:
                line = line.strip()
                if not line or line.startswith(("#", "[")):
                    continue
                if "=" not in line:
                    continue
                key, value = line.split("=", 1)
                if key.strip() == "language":
                    value = value.strip().strip('"').strip("'")
                    return value or None
    except OSError:
        return None
    return None


def set_saved_language(code):
    """Dil kodunu kaydeder. code None/bos ise kaydi siler (sistem dili)."""
    path = config_path()
    if not code:
        try:
            os.remove(path)
        except OSError:
            pass
        return
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as handle:
            handle.write("[General]\n")
            handle.write("language = %s\n" % code)
    except OSError:
        pass


def _po_language_name(locale_name):
    """po dosyasindaki 'Language:' alanindan dil adini okumayi dener."""
    po = os.path.join(LOCALE_DIR, locale_name, "LC_MESSAGES", "pisiman.po")
    try:
        with open(po, encoding="utf-8", errors="ignore") as handle:
            for line in handle:
                line = line.strip()
                if line.startswith('"Language:'):
                    return line.split(":", 1)[1].strip().strip("\\n").strip()
    except OSError:
        pass
    return None


def display_name(code):
    """Dil kodunu insan okunur ada cevirir."""
    base = code.replace("-", "_")
    short = base.split("_")[0]
    if base in LANGUAGE_NAMES:
        return LANGUAGE_NAMES[base]
    if short in LANGUAGE_NAMES:
        return LANGUAGE_NAMES[short]
    # po dosyasindaki Language alanina bak (varsa)
    for candidate in (base, code):
        name = _po_language_name(candidate)
        if name:
            return name
    return base


def available_languages():
    """locale/ altinda cevirisi bulunan diller: [(kod, ad), ...] sirali."""
    result = []
    if os.path.isdir(LOCALE_DIR):
        for name in sorted(os.listdir(LOCALE_DIR)):
            messages = os.path.join(LOCALE_DIR, name, "LC_MESSAGES")
            found = False
            for fname in ("pisiman.mo", "pisiman.qm"):
                if os.path.isfile(os.path.join(messages, fname)):
                    found = True
                    break
            if found:
                result.append((name, display_name(name)))
    return result
