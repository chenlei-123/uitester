# -*- encoding: UTF-8 -*-

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from uitester.ui.case_manager.completer_widget import CompleterWidget


class TextEdit(QTextEdit):
    insert_func_name_signal = pyqtSignal(str)

    def __init__(self, tester, parent=None):
        super(TextEdit, self).__init__(parent)
        self.cmp = None
        self.tester = tester
        self.kw_core = self.tester.get_kw_runner()
        self.popup_widget = CompleterWidget()
        self.insert_func_name_signal.connect(self.insert_completion, Qt.QueuedConnection)
        self.popup_widget.func_list_widget.select_signal.connect(self.insert_completion, Qt.QueuedConnection)
        self.popup_widget.selected_func_name_signal.connect(self.popup_widget.update_desc, Qt.QueuedConnection)
        self.func_dict = {}

    def set_completer(self, completer):
        self.cmp = completer
        if not self.cmp:
            return
        self.cmp.setWidget(self)
        self.cmp.setCompletionMode(QCompleter.PopupCompletion)
        self.cmp.setCaseSensitivity(Qt.CaseInsensitive)
        self.func_dict = self.cmp.func_dict

    def completer(self):
        return self.cmp

    def insert_completion(self, string):
        tc = self.textCursor()
        tc.movePosition(QTextCursor.StartOfWord, QTextCursor.KeepAnchor)
        tc.insertText(string)
        self.popup_widget.hide()   # 插入选中项，同时关闭提示框
        self.setTextCursor(tc)

    def text_under_cursor(self):
        tc = self.textCursor()
        tc.select(QTextCursor.WordUnderCursor)
        return tc.selectedText()

    def keyPressEvent(self, e):
        if self.cmp and self.popup_widget.func_list_widget.isVisible():
            current_row = self.popup_widget.func_list_widget.currentRow()
            # 上下键控制list
            if e.key() == Qt.Key_Down:
                self.current_item_down(current_row)
                return

            if e.key() == Qt.Key_Up:
                self.current_item_up(current_row)
                return

            if e.key() in (Qt.Key_Return, Qt.Key_Enter):
                self.insert_func_name_signal.emit(self.popup_widget.func_list_widget.currentItem().text())
                return

        if e.key() in (Qt.Key_Return, Qt.Key_Enter):
            # TODO 逐行解析,update自动提示list
            self.parse_content()

        is_shortcut = ((e.modifiers() & Qt.ControlModifier) and e.key() == Qt.Key_E)  # 设置 ctrl + e 快捷键
        if not self.cmp or not is_shortcut:
            super(TextEdit, self).keyPressEvent(e)

        ctrl_or_shift = e.modifiers() & (Qt.ControlModifier | Qt.ShiftModifier)
        eow = "~!@#$%^&*()_+{}|:\"<>?,./;'[]\\-="
        has_modifier = (e.modifiers() != Qt.NoModifier) and not ctrl_or_shift
        completion_prefix = self.text_under_cursor()

        if not is_shortcut and (has_modifier or (not e.text()) or len(completion_prefix) < 1 or (e.text()[-1] in eow)):
            self.popup_widget.hide()
            return
        self.cmp.update(completion_prefix, self.popup_widget)

        # 更新提示框显示位置
        cursor_pos = self.cursorRect()  # 光标位置
        edit_pos = self.mapToGlobal(QPoint(5, 10))   # 获得TextEdit在屏幕中的坐标，QPoint(5, 10)中 5、10为距离光标的x、y偏移量
        x = edit_pos.x() + cursor_pos.x()
        y = edit_pos.y() + cursor_pos.y()
        self.popup_widget.setGeometry(x, y, 650, 280)    # 更新显示位置

    def parse_content(self):
        # TODO 解析内容
        # 获取case content
        # content_list = self.toPlainText().split("\n")
        # row_index = self.textCursor().blockNumber()  # 光标所在行号
        # line_content = content_list[row_index].strip()
        # if line_content.find('import') == 0:
        #     # TODO 修改import行，重置kw_core的user_func
        #     print('find import')
        #     self.kw_core.parse_line(line_content)
        pass

    def current_item_down(self, current_row):
        """
        向下移动选中项
        :param current_row:
        :return:
        """
        if current_row == self.popup_widget.func_list_widget.count() - 1:
            self.popup_widget.func_list_widget.setCurrentRow(current_row)
            return
        self.popup_widget.func_list_widget.setCurrentRow(current_row + 1)
        func_name = self.popup_widget.func_list_widget.currentItem().text()
        self.popup_widget.selected_func_name_signal.emit(func_name, self.func_dict)

    def current_item_up(self, current_row):
        """
        向上移动选中项
        :param current_row:
        :return:
        """
        if current_row == 0:
            self.popup_widget.func_list_widget.setCurrentRow(current_row)
            return
        self.popup_widget.func_list_widget.setCurrentRow(current_row - 1)
        func_name = self.popup_widget.func_list_widget.currentItem().text()
        self.popup_widget.selected_func_name_signal.emit(func_name, self.func_dict)


class Completer(QCompleter):
    def __init__(self, func_dict, parent=None):
        super(Completer, self).__init__(parent)
        self.func_dict = func_dict
        self.string_list = self.get_func_name_list(self.func_dict)

    def update(self, completion_text, popup_widget):
        filtered = []
        popup_widget.func_list_widget.clear()
        for string in self.string_list:
            if completion_text in string:
                filtered.append(string)
                popup_widget.func_list_widget.addItem(string)

        if len(filtered) < 1:
            popup_widget.hide()
            return
        popup_widget.show()
        popup_widget.func_list_widget.setCurrentRow(0)  # 设置默认选中项
        func_name = popup_widget.func_list_widget.currentItem().text()
        popup_widget.selected_func_name_signal.emit(func_name, self.func_dict)  # 发送signal，更新desc

    def get_func_name_list(self, func_dict):
        """
        获取func name列表
        :param func_dict:
        :return:
        """
        func_name_list = []
        for func_name, func in func_dict.items():
            func_name_list.append(func_name)
        return func_name_list
