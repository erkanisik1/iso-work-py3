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
import os
import json
# from PyQt6.QtCore import QCoreApplication
from PyQt6.QtWidgets import QWidget, QFileDialog, QTableWidgetItem
from PyQt6 import uic

# _ = lambda x: QCoreApplication.translate


class RepoWidget(QWidget):
    def __init__(self, parent=None, *args):
        super(QWidget, self).__init__(parent)
        ui_path = os.path.join(os.path.dirname(__file__), "ui", "repowidget.ui")
        uic.loadUi(ui_path, self)
        
        self.pb_repo_open.clicked.connect(self.open)
        
        self.repo_list = []
        self.repo_path = None
        
    def open(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Open Repository JSON", os.getcwd(), "JSON files (*.json)", options=QFileDialog.Option.DontUseNativeDialog)
        if filename:
            self.repo_path = filename
            self.load()
            
    def load(self):
        if not self.repo_path:
            return
            
        with open(self.repo_path, "r") as f:
            self.repo_list = json.load(f)
            
        self.table_repo.setRowCount(len(self.repo_list))
        for i, repo in enumerate(self.repo_list):
            self.table_repo.setItem(i, 0, QTableWidgetItem(repo["name"]))
            self.table_repo.setItem(i, 1, QTableWidgetItem(repo["url"]))
            
    def save(self):
        if not self.repo_path:
            return
            
        self.repo_list = []
        for i in range(self.table_repo.rowCount()):
            name = self.table_repo.item(i, 0).text()
            url = self.table_repo.item(i, 1).text()
            self.repo_list.append({"name": name, "url": url})
            
        with open(self.repo_path, "w") as f:
            json.dump(self.repo_list, f, indent=4)
