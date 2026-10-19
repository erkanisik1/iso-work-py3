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
from PyQt6.QtCore import QEventLoop, QCoreApplication
from PyQt6.QtWidgets import QProgressDialog

class Progress:
    def __init__(self, parent):
        self.parent = parent
        self.dialog = None
        self.application = None

    def started(self, title):
        # Eski diyalog açık kaldıysa önce kapat (üst üste binmesin)
        self.finished()
        self.dialog = QProgressDialog(title, "Stop", 0, 0, self.parent)
        self.dialog.setGeometry(
            self.parent.x() + (self.parent.width() // 2 - 150),
            self.parent.y() + (self.parent.height() // 2 - 40),
            300, 80)
        self.dialog.setCancelButton(None)
        self.dialog.show()
        QCoreApplication.processEvents(QEventLoop.ProcessEventsFlag.AllEvents)

    def progress(self, msg, percent):
        if not self.dialog:
            return
        self.dialog.setLabelText(msg)
        # otherwise KProgressDialog automatically closes itself, sigh
        if percent < 100:
            self.dialog.setValue(percent)
        QCoreApplication.processEvents(QEventLoop.ProcessEventsFlag.AllEvents)

    def finished(self):
        try:
            if self.dialog:
                dlg, self.dialog = self.dialog, None
                dlg.hide()
                dlg.done(0)
                dlg.close()
                dlg.deleteLater()
                QCoreApplication.processEvents(QEventLoop.ProcessEventsFlag.AllEvents)
        except Exception:
            pass
        self.dialog = None
