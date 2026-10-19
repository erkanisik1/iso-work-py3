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
import tempfile

# Qt
try:
    import QTermWidget
    HAS_QTERMWIDGET = True
except ImportError:
    HAS_QTERMWIDGET = False

from PyQt6.QtWidgets import (QMessageBox, QMainWindow, QFileDialog,
                             QListWidgetItem, QPlainTextEdit, QMenu)
from PyQt6.QtGui import QFont, QTextCursor, QAction, QActionGroup
from PyQt6.QtCore import Qt, QProcess


# UI
from PyQt6 import uic


# Dialogs
from app.gui.languages import LanguagesDialog
from app.gui.packages import PackagesDialog
from app.gui.packagecollection import PackageCollectionDialog

# Progress Dialog
from app.gui.progress import Progress

# Repository tools
from app.repotools.packages import (Repository, ExIndexBogus, ExPackageCycle,
                                ExPackageMissing, fetch_uri)
from app.repotools.utility import strip_ansi
from app.repotools.project import Project, ExProjectMissing, ExProjectBogus

import gettext
import locale

# Setup gettext for i18n
# Get project root (where pisiman.py is located)
# app/gui/main.py -> app/gui -> app -> root (3 kademe)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
locale_dir = os.path.join(project_root, 'locale')
DATA_DIR = os.path.join(project_root, "data")

# Dil tercihi: once kullanicinin kayitli secimi, yoksa sistem dili.
# ONEMLI: gettext import aninda kuruldugu icin bu blok modul
# yuklenirken calisir; app/gui/__init__.py de MainWindow'u import
# etmeden once LANGUAGE/LANG'i ayarlar.
try:
    from app.gui.settings import get_saved_language
    saved_lang = get_saved_language()
except Exception:
    saved_lang = None

try:
    if saved_lang:
        # Kullanici acikca dil sectiyse sistem dilini tahmin etme.
        current_lang = saved_lang
    else:
        # Check if we have a locale set
        current_lang = os.environ.get('LANGUAGE') or os.environ.get('LANG', '')

        # If running under sudo, LANG might be reset, so try to detect from
        # user's locale
        if not current_lang or current_lang.startswith('en'):
            try:
                # Try to get user's actual locale
                import subprocess
                result = subprocess.run(['locale'], capture_output=True, text=True)
                for line in result.stdout.split('\n'):
                    if line.startswith('LANG='):
                        user_lang = line.split('=')[1].strip('"')
                        if user_lang and not user_lang.startswith('en'):
                            current_lang = user_lang
                        break
            except Exception:
                pass

    # Set LANGUAGE environment variable for gettext
    if current_lang:
        lang_code = current_lang.split('.')[0]  # tr_TR.UTF-8 -> tr_TR
        os.environ['LANGUAGE'] = lang_code

    locale.setlocale(locale.LC_ALL, '')
except Exception:
    pass

gettext.bindtextdomain('pisiman', locale_dir)
gettext.textdomain('pisiman')
_ = gettext.gettext


def get_finished_status(project):
    status = ("make-repo", "make-live", "pack-live", "make-iso")
    if not os.path.exists(os.path.join(project.work_dir, "finished.txt")):
        return -1

    with open(os.path.join(project.work_dir, "finished.txt"), 'r') as _file:
        state = _file.read()
    state = status.index(state)
    return state


class PackageCollectionListItem(QListWidgetItem):
    def __init__(self, parent, collection, language):
        QListWidgetItem.__init__(self, parent)
        self.collection = collection
        self.setText(collection.translations[language][0])


class TerminalFallback(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.process = QProcess(self)
        self.process.readyReadStandardOutput.connect(self.read_stdout)
        self.process.readyReadStandardError.connect(self.read_stderr)
        self.process.finished.connect(self._shell_finished)
        self._ensure_shell()

    def _ensure_shell(self):
        if self.process.state() == QProcess.ProcessState.NotRunning:
            self.process.start("bash", ["--norc", "--noprofile", "-i"])

    def _shell_finished(self):
        self.append_text("\n[shell kapandı, yeniden başlatılıyor...]\n")
        self._ensure_shell()

    def read_stdout(self):
        data = self.process.readAllStandardOutput().data().decode('utf-8', errors='ignore')
        self.append_text(data)

    def read_stderr(self):
        data = self.process.readAllStandardError().data().decode('utf-8', errors='ignore')
        self.append_text(data)

    def append_text(self, text):
        self.moveCursor(QTextCursor.MoveOperation.End)
        self.insertPlainText(strip_ansi(text))
        self.moveCursor(QTextCursor.MoveOperation.End)

    def sendText(self, text):
        if not text.endswith('\n'):
            text += '\n'
        self._ensure_shell()
        self.append_text("$ %s" % text.strip())
        self.process.write(text.encode('utf-8', errors='ignore'))

    def setHistorySize(self, size): pass
    def setScrollBarPosition(self, pos): pass
    def setTerminalFont(self, font): self.setFont(font)
    def setColorScheme(self, scheme): pass


class MainWindow(QMainWindow):
    def __init__(self, args):
        QMainWindow.__init__(self)
        ui_path = os.path.join(os.path.dirname(__file__), "ui", "mainv2.ui")
        uic.loadUi(ui_path, self)
        self.title = "Pisiman"
        # Terminal
        if HAS_QTERMWIDGET:
            self.terminal = QTermWidget.QTermWidget()
            self.terminal.setHistorySize(-1)
            self.terminal.setScrollBarPosition(2)
            font = QFont("Droid Sans Mono")
            font.setPointSize(10)
            self.terminal.setTerminalFont(font)
            self.terminal.setColorScheme(
                "/usr/share/qtermwidget5/color-schemes/BreezeModified.colorscheme")
        else:
            self.terminal = TerminalFallback()
            font = QFont("Monospace")
            font.setStyleHint(QFont.StyleHint.Monospace)
            font.setPointSize(10)
            self.terminal.setTerminalFont(font)
            self.terminal.setStyleSheet("background-color: #2e3436; color: #eeeeec;")

        self.terminalLayout.addWidget(self.terminal)
        self.terminal.show()

        # self.collectionFrame.hide()

        # Arguments
        self.args = args

        # Project
        self.project = Project()

        # Package repository
        self.repo = None

        # Package Selection collections
        self.collections = None

        # File menu
        self.actionNew.triggered.connect(self.slotNew)
        self.actionOpen.triggered.connect(self.slotOpen)
        self.actionSave.triggered.connect(self.slotSave)
        self.actionSaveAs.triggered.connect(self.slotSaveAs)
        self.actionExit.triggered.connect(self.close)

        # Project menu
        self.actionUpdateRepo.triggered.connect(self.slotUpdateRepo)
        self.actionLanguages.triggered.connect(self.slotSelectLanguages)
        self.actionPackages.triggered.connect(self.slotSelectPackages)
        # NOT: Tek satir olmali. Burada ikinci bir connect() varsa
        # "Imaj Olustur" tiklamasi terminale IKI adet "pisiman.py make"
        # yazar; ikincisi birincinin bitmesini bekleyip imaji bastan
        # kurar (flock da ise yaramaz, cunku es zamanli degil, ardisik).
        self.actionMakeImage.triggered.connect(self.slotMakeImage)

        self.actionMake_Repo.triggered.connect(self.slotMakeRepo)
        self.actionCheck_Repo.triggered.connect(self.slotCheckRepo)
        self.actionMake_Live.triggered.connect(self.slotMakeLive)
        self.actionPack_Live.triggered.connect(self.slotPackLive)
        self.actionMake_Iso.triggered.connect(self.slotMakeIso)

        self.actionRemoveMissingPackages.triggered.connect(
            self.slotRemoveMissingPackages)

        # Browse buttons
        self.pushBrowseRepository.clicked.connect(self.slotBrowseRepository)
        self.pushBrowseWorkFolder.clicked.connect(self.slotBrowseWorkFolder)
        self.pushBrowsePluginPackage.clicked.connect(
            self.slotBrowsePluginPackage)
        self.pushBrowseReleaseFiles.clicked.connect(
            self.slotBrowseReleaseFiles)
        self.btn_browse_iso_output_dir.clicked.connect(
            self.slotBrowseIsoOutputDir)

        # Change Package Selection
        self.pushAddCollection.clicked.connect(self.slotAddPackageCollection)
        self.pushModifyCollection.clicked.connect(
            self.slotModifyPackageCollection)
        self.pushRemoveCollection.clicked.connect(
            self.slotRemovePackageCollection)
        self.pushSetDefaultCollection.clicked.connect(
            self.slotSetDefaultCollection)
        self.checkCollection.stateChanged[int].connect(
            self.slotShowPackageCollection)
        self.listPackageCollection.itemClicked[QListWidgetItem].connect(
            self.slotClickedCollection)

        self.menuCommands.hovered[QAction].connect(self.updateCommands)

        # Dil secimi menusu (Dil / Language)
        self.setupLanguageMenu()

        # System settings tab (data/etc release dosyaları)
        self.releaseSave.clicked.connect(self.slotReleaseSave)

        # Initialize
        self.initialize()

        self.updateCommands()
        self.releaseFilesLoad()

    def initialize(self):
        if len(self.args) == 2:
            self.slotOpen(self.args[1])

    # ------------------------------------------------------------------
    # Dil secimi
    # ------------------------------------------------------------------
    def setupLanguageMenu(self):
        """MenuBar'a 'Dil / Language' menusu ekler.

        Secenekler locale/ altindaki cevirilerden uretilir. Secim
        ~/.config/pisiman/pisiman.conf dosyasina yazilir; yeni dilin
        tum arayuze uygulanmasi icin program yeniden baslatilir.
        """
        from app.gui import settings as gui_settings

        self.menuLanguage = QMenu(_("Language"), self)
        group = QActionGroup(self)
        group.setExclusive(True)

        saved = gui_settings.get_saved_language()

        # Sistem dili (otomatik algila)
        system_action = QAction(_("System default"), self)
        system_action.setCheckable(True)
        system_action.setChecked(not saved)
        system_action.triggered.connect(
            lambda checked=False: self.changeLanguage(None))
        group.addAction(system_action)
        self.menuLanguage.addAction(system_action)

        self.menuLanguage.addSeparator()

        for code, name in gui_settings.available_languages():
            action = QAction(name, self)
            action.setCheckable(True)
            action.setChecked(saved == code)
            action.setData(code)
            action.triggered.connect(
                lambda checked=False, c=code: self.changeLanguage(c))
            group.addAction(action)
            self.menuLanguage.addAction(action)

        self.menubar.addMenu(self.menuLanguage)

    def changeLanguage(self, code):
        """Dili kaydeder ve yeniden baslatmayi onerir.

        code None ise sistem dili kullanilir.
        """
        from app.gui import settings as gui_settings

        if gui_settings.get_saved_language() == code:
            return
        gui_settings.set_saved_language(code)

        box = QMessageBox(self)
        box.setWindowTitle(self.title)
        box.setIcon(QMessageBox.Icon.Question)
        box.setText(_("Interface language changed."))
        box.setInformativeText(
            _("The new language is fully applied after restarting the "
              "program.\n\nRestart now?\n\n(Note: a build running in the "
              "terminal will be interrupted.)"))
        box.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        box.setDefaultButton(QMessageBox.StandardButton.Yes)
        if box.exec() == QMessageBox.StandardButton.Yes:
            self.restartApplication()

    def restartApplication(self):
        """Uygulamayi ayni argumanlarla yeniden baslatir."""
        program = sys.executable or "python3"
        argv = [program] + list(sys.argv)
        try:
            os.execv(program, argv)
        except OSError as error:
            QMessageBox.warning(
                self, self.title,
                _("Could not restart the program:\n%s") % error)

    def initializeRepo(self):
        if not self.repo:
            if not self.checkProject():
                return
            if not self.updateRepo():
                return

    def slotNew(self):
        """
            "New" menu item fires this function.
        """
        self.project = Project()
        self.loadProject()

    def slotOpen(self, filename=None):
        """
            "Open..." menu item fires this function.
        """
        if not filename:
            filename = QFileDialog.getOpenFileName(
                self, _("Select project file"), os.path.join(os.getcwd(), "project-files"),
                "Xml Files (*.xml)", options=QFileDialog.Option.DontUseNativeDialog)
            filename = filename[0]
        if filename:
            self.project = Project()

            try:
                self.project.open(filename)
            except ExProjectMissing:
                QMessageBox.warning(
                    self, self.title, _("Project file is missing."))
                return
            except ExProjectBogus:
                QMessageBox.warning(
                    self, self.title, _("Project file is corrupt."))
                return
            self.loadProject()
            self.updateCommands()

    def slotSave(self):
        """
            "Save" menu item fires this function.
        """
        if self.project.filename:
            self.updateProject()
            self.project.save()
        else:
            self.slotSaveAs()

    def slotSaveAs(self):
        """
            "Save As..." menu item fires this function.
        """
        filename = QFileDialog.getSaveFileName(
            self, _("Save project"), os.path.join(os.getcwd(), "project-files"), "Xml Files (*.xml)", options=QFileDialog.Option.DontUseNativeDialog)
        filename = filename[0]
        if filename:
            self.project.filename = str(filename)
            self.slotSave()

    def get_path(self, text):
        print(text)
        if text != "":

            if(os.path.splitext(text)[1] != ""):
                _dir = os.path.dirname(text)
            else:
                _dir = text

            if(_dir.startswith("file:///")):
                _dir = _dir[7:]
            elif(_dir.startswith("file:/")):
                _dir = _dir[5:]

            if not os.path.exists(_dir) or _dir == "":
                _dir = "."
        else:
            _dir = "."

        print(_dir)
        return _dir

    def slotBrowseIsoOutputDir(self):
        _dir = self.get_path(self.le_iso_output_dir.text())

        new_dir = QFileDialog.getExistingDirectory(
            self, _("Select Iso Output Dir"), _dir, options=QFileDialog.Option.DontUseNativeDialog)

        if new_dir:
            self.le_iso_output_dir.setText(new_dir)

    def slotBrowseRepository(self):
        """
            Browse repository button fires this function.
        """

        _dir = self.get_path(self.lineRepository.text())

        filename = QFileDialog.getOpenFileName(
            self, _("Select repository index"), _dir,
            "Pisi Index Files(*-index.xml *-index.xml.xz)", options=QFileDialog.Option.DontUseNativeDialog)
        filename = filename[0]
        if filename:
            filename = str(filename)
            if filename.startswith("/"):
                filename = "file://%s" % filename
            self.lineRepository.setText(filename)

    def slotBrowsePluginPackage(self):
        """
            Browse plugin package button fires this function.
        """
        _dir = self.get_path(self.linePluginPackage.text())

        filename = QFileDialog.getOpenFileName(
            self, _("Select plugin package"), _dir, "Pisi Files(*.pisi)", options=QFileDialog.Option.DontUseNativeDialog)
        filename = filename[0]
        if filename:
            self.linePluginPackage.setText(filename)

    def slotBrowseReleaseFiles(self):
        """
            Browse release files button fires this function.
        """
        _dir = self.get_path(self.lineReleaseFiles.text())

        directory = QFileDialog.getExistingDirectory(self, "", _dir, options=QFileDialog.Option.DontUseNativeDialog)
        if directory:
            self.lineReleaseFiles.setText(directory)

    def slotBrowseWorkFolder(self):
        """
            Browse work folder button fires this function.
        """
        _dir = self.get_path(self.lineWorkFolder.text())

        directory = QFileDialog.getExistingDirectory(self, "", _dir, options=QFileDialog.Option.DontUseNativeDialog)
        if directory:
            self.lineWorkFolder.setText(directory)

    def slotAddPackageCollection(self):
        if not self.repo:
            self.initializeRepo()

        if not self.project.selected_languages:
            QMessageBox.warning(
                self, self.title, _("Installation Languages is not selected."))
            return

        dialog = PackageCollectionDialog(self, self.repo, self.project)
        if dialog.exec():
            item = PackageCollectionListItem(
                self.listPackageCollection, dialog.collection,
                self.project.default_language)
            self.project.package_collections.append(item.collection)

            if self.listPackageCollection.count() == 1:
                item.collection.default = "True"

        self.updateCollection()

    def slotModifyPackageCollection(self):
        index = self.listPackageCollection.currentRow()
        item = self.listPackageCollection.item(index)
        if not self.repo:
            self.initializeRepo()

        dialog = PackageCollectionDialog(
            self, self.repo, self.project, item.collection)
        if dialog.exec():
            if not item.collection._id == dialog.collection._id:
                item.setText(
                    dialog.collection.translations[
                        self.project.default_language][0])
            item.collection = dialog.collection

        self.updateCollection()

    def slotRemovePackageCollection(self):
        for item in self.listPackageCollection.selectedItems():
            self.listPackageCollection.takeItem(
                self.listPackageCollection.row(item))

        self.updateCollection()

    def slotClickedCollection(self, item):
        if item.collection.default == "True":
            if not self.pushSetDefaultCollection.isChecked():
                self.pushSetDefaultCollection.setChecked(True)
        else:
            if self.pushSetDefaultCollection.isChecked():
                self.pushSetDefaultCollection.setChecked(False)

    def slotSetDefaultCollection(self):
        if self.listPackageCollection.currentItem() and \
                not self.listPackageCollection.currentItem(
                ).collection.default:
            self.listPackageCollection.currentItem(
            ).collection.default = "True"
            currentIndex = self.listPackageCollection.currentRow()
            for index in range(self.listPackageCollection.count()):
                if index == currentIndex:
                    pass
                else:
                    self.listPackageCollection.item(
                        index).collection.default = ""

            self.pushSetDefaultCollection.setChecked(True)

    def slotShowPackageCollection(self, state):
        if state == Qt.CheckState.Checked:
            # self.collectionFrame.show()
            self.actionPackages.setVisible(False)
        else:
            # self.collectionFrame.hide()
            self.actionPackages.setVisible(True)

    def slotSelectLanguages(self):
        """
            "Languages..." menu item fires this function.
        """
        dialog = LanguagesDialog(self, self.project.selected_languages)
        if dialog.exec():
            self.project.default_language = dialog.languages[0]
            self.project.selected_languages = dialog.languages

    def slotSelectPackages(self):
        """
            "Packages..." menu item fires this function.
        """
        if not self.repo:
            if not self.checkProject():
                return
            if not self.updateRepo():
                return

        dialog = PackagesDialog(
            self, self.repo, self.project.selected_packages,
            self.project.selected_components)

        if dialog.exec():
            self.project.selected_packages = dialog.packages
            self.project.selected_components = dialog.components
            self.project.all_packages = dialog.all_packages


    def slotUpdateRepo(self):
        """
            Update repository button fires this function.
        """
        if not self.checkProject():
            return
        self.updateProject()
        self.updateRepo()

    def updateCommands(self):
        state = get_finished_status(self.project)
        # print(state)

        # self.actionCheck_Repo.setEnabled(state >= 0)
        self.actionMake_Live.setEnabled(state >= 0)
        self.actionPack_Live.setEnabled(state >= 1)
        self.actionMake_Iso.setEnabled(state >= 2)

    # Ayni komutun cok kisa sure icinde tekrar gonderilmesini engeller.
    # Cift tiklama ya da yinelenen sinyal baglantisi, terminale iki
    # "pisiman.py make ..." yazar; ikincisi birincinin bitmesini bekleyip
    # imaji bastan kurar (40+ dakika bosuna). Bu koruma yinelenen
    # komutu yok sayar.
    _COMMAND_DEBOUNCE = 5.0

    def _allow_command(self, cmd):
        now = time.time()
        last_cmd, last_time = getattr(self, "_last_command", (None, 0.0))
        if last_cmd == cmd and (now - last_time) < self._COMMAND_DEBOUNCE:
            print("[%s az once baslatildi; yinelenen komut yok sayildi]" % cmd)
            return False
        self._last_command = (cmd, now)
        return True

    def slotMakeImage(self):
        """
            Make image button fires this function.
        """
        if not self._allow_command("make"):
            return
        self.tabWidget.setCurrentIndex(2)
        if os.path.exists(os.path.join(self.project.work_dir, "finished.txt")):
            os.remove(os.path.join(self.project.work_dir, "finished.txt"))

        if not self.repo:
            if not self.checkProject():
                return
            if not self.updateRepo():
                return
        temp_project = tempfile.NamedTemporaryFile(delete=False)
        self.project.save(temp_project.name)
        app_path = self.args[0]
        if app_path[0] != "/":
            app_path = os.path.join(os.getcwd(), app_path)

        # Konsole Mode
        # cmd = 'konsole --noclose --workdir "%s" -e "%s" make "%s"' \
        # % (os.getcwd(), app_path, temp_project.name)
        # subprocess.Popen(["xdg-su", "-u", "root", "-c", cmd])

        cmd = '%s make %s' % (app_path, temp_project.name)
        self.terminal.sendText("sudo %s\n" % cmd)
        self.terminal.setFocus()
        self.updateCommands()

    def slotMakeRepo(self):
        """
            Make image button fires this function.
        """
        if not self._allow_command("make-repo"):
            return
        self.tabWidget.setCurrentIndex(2)
        if not self.repo:
            if not self.checkProject():
                return
            if not self.updateRepo():
                return
        temp_project = tempfile.NamedTemporaryFile(delete=False)
        self.project.save(temp_project.name)
        app_path = self.args[0]
        if app_path[0] != "/":
            app_path = os.path.join(os.getcwd(), app_path)

        # Konsole Mode
        # cmd = 'konsole --noclose --workdir "%s" -e "%s" make "%s"' \
        # % (os.getcwd(), app_path, temp_project.name)
        # subprocess.Popen(["xdg-su", "-u", "root", "-c", cmd])

        cmd = '%s make-repo %s' % (app_path, temp_project.name)
        self.terminal.sendText("sudo %s\n" % cmd)
        self.terminal.setFocus()
        self.updateCommands()

    def slotCheckRepo(self):
        """
            Make image button fires this function.
        """
        self.tabWidget.setCurrentIndex(2)
        if not self.repo:
            if not self.checkProject():
                return
            if not self.updateRepo():
                return
        temp_project = tempfile.NamedTemporaryFile(delete=False)
        self.project.save(temp_project.name)
        app_path = self.args[0]
        if app_path[0] != "/":
            app_path = os.path.join(os.getcwd(), app_path)

        # Konsole Mode
        # cmd = 'konsole --noclose --workdir "%s" -e "%s" make "%s"' \
        # % (os.getcwd(), app_path, temp_project.name)
        # subprocess.Popen(["xdg-su", "-u", "root", "-c", cmd])

        cmd = '%s check-repo %s' % (app_path, temp_project.name)
        self.terminal.sendText("sudo %s\n" % cmd)
        self.terminal.setFocus()
        self.updateCommands()

    def slotMakeLive(self):
        if not self._allow_command("make-live"):
            return
        self.tabWidget.setCurrentIndex(2)
        """
            Make image button fires this function.
        """
        if not self.repo:
            if not self.checkProject():
                return
            if not self.updateRepo():
                return
        temp_project = tempfile.NamedTemporaryFile(delete=False)
        self.project.save(temp_project.name)
        app_path = self.args[0]
        if app_path[0] != "/":
            app_path = os.path.join(os.getcwd(), app_path)

        # Konsole Mode
        # cmd = 'konsole --noclose --workdir "%s" -e "%s" make "%s"' \
        # % (os.getcwd(), app_path, temp_project.name)
        # subprocess.Popen(["xdg-su", "-u", "root", "-c", cmd])

        cmd = '%s make-live %s' % (app_path, temp_project.name)
        self.terminal.sendText("sudo %s\n" % cmd)
        self.terminal.setFocus()
        self.updateCommands()

    def slotPackLive(self):
        """
            Make image button fires this function.
        """
        if not self._allow_command("pack-live"):
            return
        self.tabWidget.setCurrentIndex(2)
        if not self.repo:
            if not self.checkProject():
                return
            if not self.updateRepo():
                return
        temp_project = tempfile.NamedTemporaryFile(delete=False)
        self.project.save(temp_project.name)
        app_path = self.args[0]
        if app_path[0] != "/":
            app_path = os.path.join(os.getcwd(), app_path)

        # Konsole Mode
        # cmd = 'konsole --noclose --workdir "%s" -e "%s" make "%s"' \
        # % (os.getcwd(), app_path, temp_project.name)
        # subprocess.Popen(["xdg-su", "-u", "root", "-c", cmd])

        cmd = '%s pack-live %s' % (app_path, temp_project.name)
        self.terminal.sendText("sudo %s\n" % cmd)
        self.terminal.setFocus()
        self.updateCommands()

    def slotMakeIso(self):
        """
            Make image button fires this function.
        """
        if not self._allow_command("make-iso"):
            return
        self.tabWidget.setCurrentIndex(2)
        if not self.repo:
            if not self.checkProject():
                return
            if not self.updateRepo():
                return
        temp_project = tempfile.NamedTemporaryFile(delete=False)
        self.project.save(temp_project.name)
        app_path = self.args[0]
        if app_path[0] != "/":
            app_path = os.path.join(os.getcwd(), app_path)

        # Konsole Mode
        # cmd = 'konsole --noclose --workdir "%s" -e "%s" make "%s"' \
        # % (os.getcwd(), app_path, temp_project.name)
        # subprocess.Popen(["xdg-su", "-u", "root", "-c", cmd])

        cmd = '%s make-iso %s' % (app_path, temp_project.name)
        self.terminal.sendText("sudo %s\n" % cmd)
        self.terminal.setFocus()
        self.updateCommands()

    def updateCollection(self):
        self.project.package_collections = []
        for index in range(self.listPackageCollection.count()):
            self.project.package_collections.append(
                self.listPackageCollection.item(index).collection)

    def checkProject(self):
        """
            Checks required fields for the project.
        """
        if not len(self.lineTitle.text()):
            QMessageBox.warning(
                self, self.windowTitle(),  _("Image title is missing."))
            return False
        if not len(self.lineRepository.text()):
            QMessageBox.warning(
                self, self.windowTitle(), _("Repository URL is missing."))
            return False
        if not len(self.lineWorkFolder.text()):
            QMessageBox.warning(
                self, self.windowTitle(),  _("Work folder is missing."))
            return False
        return True

    def updateProject(self):
        """
            Updates project information.
        """
        self.project.title = str(self.lineTitle.text())
        self.project.repo_uri = str(self.lineRepository.text())
        self.project.work_dir = str(self.lineWorkFolder.text())
        self.project.live_repo_uri = str(self.lineLiveIsoRepo.text())
        self.project.release_files = str(self.lineReleaseFiles.text())
        self.project.plugin_package = str(self.linePluginPackage.text())
        self.project.extra_params = str(self.lineParameters.text())
        self.project.type = ["install", "live"][self.comboType.currentIndex()]
        self.project.squashfs_comp_type = [
            "xz", "gzip", "lzma", "lzo", "zstd"][self.comboCompression.currentIndex()]

        self.project.iso_output_dir = str(self.le_iso_output_dir.text())
        self.project.use_project_dir_as_output_dir = self.check_use_project_dir.isChecked()

        if self.checkCollection.isChecked():
            self.updateCollection()
        else:
            self.listPackageCollection.clear()

    def releaseFilesLoad(self):
        """
            data/etc altındaki lsb-release, os-release ve pisilinux-release
            dosyalarını okuyup Sistem Ayarları sekmesindeki alanlara yazar.
        """
        files = {
            "lsb-release": self.lineLsbReleaseEdit,
            "os-release": self.lineOsReleaseEdit,
            "pisilinux-release": self.linePisilinuxRelease,
        }
        for name, widget in files.items():
            path = os.path.join(DATA_DIR, "etc", name)
            try:
                if os.path.exists(path):
                    with open(path, "r", encoding="utf-8", errors="replace") as f:
                        widget.setPlainText(f.read())
                else:
                    widget.setPlainText("Dosya bulunamadı: %s" % path)
            except Exception as e:
                widget.setPlainText("Hata: " + str(e))

    def slotReleaseSave(self):
        """
            Sistem Ayarları sekmesindeki release dosyalarını data/etc altına kaydeder.
        """
        files = {
            "lsb-release": self.lineLsbReleaseEdit.toPlainText(),
            "os-release": self.lineOsReleaseEdit.toPlainText(),
            "pisilinux-release": self.linePisilinuxRelease.toPlainText(),
        }
        try:
            for name, content in files.items():
                path = os.path.join(DATA_DIR, "etc", name)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
            QMessageBox.information(self, "Başarılı", "Release dosyaları başarıyla kaydedildi.")
        except Exception as e:
            QMessageBox.critical(self, "Hata", "Dosyalar kaydedilemedi: " + str(e))

    def loadProject(self):
        """
            Loads project information.
        """
        self.lineTitle.setText(str(self.project.title))
        self.lineRepository.setText(str(self.project.repo_uri))
        self.lineWorkFolder.setText(str(self.project.work_dir))
        self.lineLiveIsoRepo.setText(str(self.project.live_repo_uri))
        self.lineReleaseFiles.setText(str(self.project.release_files))
        self.linePluginPackage.setText(str(self.project.plugin_package))
        self.lineParameters.setText(str(self.project.extra_params))
        self.comboType.setCurrentIndex(
            ["install", "live"].index(self.project.type))
        self.comboCompression.setCurrentIndex(
            ["xz", "gzip", "lzma", "lzo", "zstd"].index(
                self.project.squashfs_comp_type))

        self.check_use_project_dir.setChecked(self.project.use_project_dir_as_output_dir)
        self.le_iso_output_dir.setText(str(self.project.iso_output_dir))

        self.listPackageCollection.clear()
        if self.project.package_collections:
            for index, collection in enumerate(
                    self.project.package_collections):
                PackageCollectionListItem(
                    self.listPackageCollection, collection,
                    self.project.default_language)
                if collection.default:
                    self.listPackageCollection.setCurrentRow(index)
            self.checkCollection.setChecked(True)
        else:
            self.checkCollection.setChecked(False)

    def slotRemoveMissingPackages(self):
        try:
            # curdir = os.getcwd()
            self.tabWidget.setCurrentIndex(2)

            repo = self.project.get_repo()
            repo_path = repo.cache_dir
            if repo_path.startswith("file:///"):
                repo_path = repo_path[7:]
            # print(_("Package index has errors. \
            #     '%s' depends on non-existing '%s'.") % e.args)
            # os.chdir(repo_path)
            if not os.path.exists("{}/../missing.txt".format(repo_path)):
                # os.chdir(curdir)
                QMessageBox.warning(self, self.title, _("Check repo before download.\nIf the repo is checked, there are no lost packages."))
                # print("check repo before download")
                return

            missing_packages = ""
            with open("{}/../missing.txt".format(repo_path)) as file_:
                missing_packages = file_.read()

            missing_packages = missing_packages.split("\n")
            print(missing_packages)
            for pack in missing_packages:
                __package = repo.packages[pack]
                _path = os.path.dirname(os.path.realpath(
                    os.path.join(repo.cache_dir,__package.uri)))
                # print(_path)

                if os.path.exists(_path):
                    __file = os.listdir(_path)
                    print(_path)
                    for f in __file:
                        if os.path.exists(_path + "/" + f):
                            os.remove(_path + "/" + f)

            # os.system("pisi fc {} --runtime-deps".format(
            # os.system("pisi fc {}".format(
            #    " ".join(missing_packages)))
            # os.system("pisi ix --skip-signing")
            QMessageBox.information(self, self.title,
                _("Packages removed that has wrong hash.\nRerun 'Make Inage (Ctrl+R)'."))
            # self.terminal.sendText("pisi fc {} -o {}\n".format(
            #     " ".join(missing_packages), os.path.join(repo_path, _path)))

            # self.terminal.sendText(
            #     "pisi ix --skip-signing {}\n".format(repo_path))

            os.system("rm -f {}/../missing.txt".format(repo_path))
            # os.chdir(curdir)
        except Exception as e:
            print("missing packages could not be downloaded")
            print(e)
            # Progress dialog
            # self.progress = Progress(self)
            # # Update project
            # self.updateProject()
            # # Get repository
            # try:
            #     self.repo = self.project.get_repo(
            #         self.progress, update_repo=True)
            # except ExPackageMissing as e:
            #     self.progress.finished()
            #
            #     curdir = os.getcwd()
            #
            #     repo_path = os.path.dirname(self.project.repo_uri)
            #     if repo_path.startswith("file:///"):
            #         repo_path = repo_path[7:]
            #     print(_("Package index has errors. \
            #         '%s' depends on non-existing '%s'.") % e.args)
            #     os.chdir(repo_path)
            #     os.system("pisi fc {} --runtime-deps".format(
            #         " ".join(e.args[1:])))
            #     os.system("pisi ix --skip-signing")
            #
            #     os.chdir(curdir)
            # else:
            #     self.progress.finished()
            #     break

    def updateRepo(self, update_repo=True):
        """
            Fetches package index and retrieves list of package and components.
        """
        # Progress dialog
        self.progress = Progress(self)
        # Update project
        self.updateProject()
        # Get repository
        try:
            self.repo = self.project.get_repo(
                self.progress, update_repo=update_repo)
        except ExIndexBogus as e:
            # print(e.args[0])
            QMessageBox.warning(self, self.title, _("Unable to load package \
                index. URL is wrong, or file is corrupt."))
            return False
        except ExPackageCycle as e:
            cycle = " > ".join(e.args[0])
            QMessageBox.warning(self, self.title, _("Package index has errors.\
                 Cyclic dependency found:\n  %s.") % cycle)
            return False
        except ExPackageMissing as e:
            QMessageBox.warning(self, self.title, _("Package index has errors.\
            '%s' depends on non-existing '%s'.") % e.args)
            return False
        except Exception as e:
            QMessageBox.warning(self, self.title, _("Unexpected error while fetching repository:\n%s") % e)
            return False
        finally:
            # Pencere her durumda kapanır (hata/farklı istisna dahil)
            self.progress.finished()

        missing_components, missing_packages = self.project.get_missing()
        if len(missing_components):
            QMessageBox.warning(self, self.title, _("There are missing \
            components: {}. Removing.".format(", ".join(missing_components))))
            for component in missing_components:
                if component in self.project.selected_components:
                    self.project.selected_components.remove(component)
            return self.updateRepo(update_repo=False)
            # self.updateRepo(update_repo=False)

        if len(missing_packages):
            QMessageBox.warning(self, self.title, _("There are missing \
            packages: {}. Removing.".format(", ".join(missing_packages))))
            for package in missing_packages:
                if package in self.project.selected_packages:
                    self.project.selected_packages.remove(package)
            return self.updateRepo(update_repo=False)

        return True
