# -*- encoding: UTF-8 -*-
import os

from PyQt5 import uic
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QWidget, QListWidget, QTextBrowser


class CompleterWidget(QWidget):
    select_signal = pyqtSignal(str, name="select_signal")
    selected_func_name_signal = pyqtSignal(str, str, name="selected_func_name_signal")

    def __init__(self, parent=None):
        super(CompleterWidget, self).__init__(parent)

        ui_dir_path = os.path.dirname(__file__)
        ui_file_path = os.path.join(ui_dir_path, 'completer_widget.ui')
        uic.loadUi(ui_file_path, self)

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool)

        self.func_list_widget = QListWidget()
        self.func_list_widget.setFixedWidth(200)
        self.func_list_widget.setSizeAdjustPolicy(QListWidget.AdjustToContents)
        self.func_list_layout.insertWidget(0, self.func_list_widget)
        self.desc_text_browser.setSizeAdjustPolicy(QTextBrowser.AdjustToContents)

        self.func_list_widget.setFocusPolicy(Qt.NoFocus)

    def update_desc(self, text, func_doc):
        """
        update the description according to the selected function name
        :param func_doc:
        :param text:
        :return:
        """
        if not text:
            return
        if not func_doc:  # desc is None
            self.desc_text_browser.setText("<pre> <font color='red'>\"" + text +
                                           "\" has no description." + "</font></pre>")
            return
        func_doc = func_doc.split("\n")
        func_desc = ''
        for line in func_doc:
            func_desc = func_desc + line.lstrip() + "\n"
        self.desc_text_browser.setText("<pre> <font color='green'>" + func_desc + "</font></pre>")
