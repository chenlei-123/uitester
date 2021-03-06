# -*- encoding: UTF-8 -*-
import logging
import re
from PyQt5.QtCore import pyqtSignal, Qt, QPoint
from PyQt5.QtGui import QTextCursor

from PyQt5.QtWidgets import QTextEdit, QCompleter

from uitester.ui.case_manager.completer_widget import CompleterWidget

logger = logging.getLogger("Tester")

class TextEdit(QTextEdit):
    insert_func_name_signal = pyqtSignal(str, str, name="insert_func_name_signal")
    parse_error_info_signal = pyqtSignal(str, name="parse_error_info_signal")

    def __init__(self, kw_core, parent=None):
        super(TextEdit, self).__init__(parent)
        self.kw_core = kw_core
        self.cmp = None
        self.high_lighter = None
        self.setPlaceholderText("Case Content")
        self.import_lines = set()

        self.popup_widget = CompleterWidget()

        self.insert_func_name_signal.connect(self.insert_completion, Qt.QueuedConnection)
        self.popup_widget.selected_func_name_signal.connect(self.popup_widget.update_desc, Qt.QueuedConnection)
        self.textChanged.connect(self.text_change)

    def text_change(self):
        """
        editor content change event
        :return:
        """
        completion_prefix = self.text_under_cursor()
        if not completion_prefix:
            if self.popup_widget.isVisible():
                self.popup_widget.hide()
            return
        prefix_or_special = len(completion_prefix) < 2 and completion_prefix != "$"
        if prefix_or_special:
            self.popup_widget.hide()
            return
        self.cmp.update(completion_prefix, self.popup_widget)
        self.update_popup_widget_position()
        self.activateWindow()

    def set_completer(self, completer):
        self.cmp = completer
        if not self.cmp:
            return
        self.cmp.setWidget(self)
        self.cmp.setCompletionMode(QCompleter.PopupCompletion)
        self.cmp.setCaseSensitivity(Qt.CaseInsensitive)

    def completer(self):
        return self.cmp

    def set_highlighter(self, high_lighter):
        self.high_lighter = high_lighter

    def insert_completion(self, prefix, selected_word):
        tc = self.textCursor()
        is_char_after_cursor = self.is_char(tc)
        if not tc.atBlockEnd() and (not is_char_after_cursor):
            if prefix.startswith("$") and (not prefix.endswith(".")) and not prefix[1:]:
                selected_word = "$" + selected_word  # add "$" to the var
            elif "." in prefix:
                selected_word = "." + selected_word  # add "." to the attr
        tc.movePosition(QTextCursor.StartOfWord, QTextCursor.KeepAnchor)
        tc.insertText(selected_word)
        self.popup_widget.hide()   # insert the text into text edit, and hide the popup_widget
        self.setTextCursor(tc)

    def line_text(self, line_number):
        """
        get the specify line text
        :param line_number:
        :return:
        """
        case_content = self.toPlainText()
        content_list = case_content.split("\n")
        return content_list[line_number]

    def is_char(self, tc):
        """
        is validate char after the cursor
        :param tc:
        :return:
        """
        line_number = tc.blockNumber()
        column_number = tc.columnNumber()
        line_text = self.line_text(line_number)
        is_char_after_cursor = False
        if line_text[column_number:column_number+1]:
            regex = "[a-zA-Z0-9_]"
            match = re.search(regex, line_text[column_number:column_number+1])
            if match:
                is_char_after_cursor = True
        return is_char_after_cursor

    def text_under_cursor(self):
        text = ""
        tc = self.textCursor()
        cursor_index = tc.columnNumber() + 1
        tc.select(QTextCursor.BlockUnderCursor)
        if not tc.selectedText().strip():
            return text
        block_before_cursor_list = []  # block list before cursor
        if cursor_index < len(tc.selectedText()):
            block_before_cursor_list = tc.selectedText()[:cursor_index].split(" ")
        else:
            block_before_cursor_list = tc.selectedText().split(" ")
        text = block_before_cursor_list[len(block_before_cursor_list) - 1].strip()
        return text

    def mousePressEvent(self, event):
        """
        while the mouse pressed and the popup_widget is visible, hide the popup_widget
        :param event:
        :return:
        """
        if self.cmp and self.popup_widget.func_list_widget.isVisible():
            self.popup_widget.hide()
        super(TextEdit, self).mousePressEvent(event)

    def keyPressEvent(self, e):
        completion_prefix = self.text_under_cursor()
        if self.cmp and self.popup_widget.func_list_widget.isVisible():
            current_row = self.popup_widget.func_list_widget.currentRow()
            if e.key() == Qt.Key_Down:
                self.current_item_down(current_row)
                return

            if e.key() == Qt.Key_Up:
                self.current_item_up(current_row)
                return

            if e.key() in (Qt.Key_Return, Qt.Key_Enter):
                selected_word = self.popup_widget.func_list_widget.currentItem().text()
                self.insert_func_name_signal.emit(completion_prefix, selected_word)
                return

        if e.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.parse_content()

        is_shortcut = ((e.modifiers() & Qt.ControlModifier) and e.key() == Qt.Key_E)  # shortcut key:ctrl + e
        if is_shortcut:
            self.cmp.update("", self.popup_widget)
            self.update_popup_widget_position()
            self.activateWindow()
            return

        if not self.cmp or not is_shortcut:
            super(TextEdit, self).keyPressEvent(e)

    def parse_content(self):
        """
        parse the editor's content,and show the error massage in console
        :return:
        """
        self.parse_import()

        content_list = self.toPlainText().split("\n")
        row_index = self.textCursor().blockNumber()  # row number of the text cursor
        line_content = content_list[row_index].strip()
        if not line_content:
            return
        if line_content.find('import') != 0:
            try:
                self.kw_core.parse_line(line_content)
            except Exception as e:
                self.parse_error_info_signal.emit("<font color='red'>" + str(e) + "</font>")

    def update_popup_widget_position(self):
        """
        set completer widget's position
        :return:
        """
        cursor_pos = self.cursorRect()
        edit_pos = self.mapToGlobal(QPoint(10, 15))
        x = edit_pos.x() + cursor_pos.x()
        y = edit_pos.y() + cursor_pos.y()
        self.popup_widget.setGeometry(x, y, 650, 280)

    def get_import_from_content(self, init_import_lines=None):
        """
        get all 'import' block from edit text
        :return:
        """
        current_import_lines = set()
        if init_import_lines:
            self.import_lines = init_import_lines
            return self.import_lines
        if not self.toPlainText():
            return current_import_lines
        content_list = self.toPlainText().split("\n")

        for line in content_list:
            if line.strip().find('import') == 0:
                current_import_lines.add(line.strip())
        return current_import_lines

    def parse_import(self):
        """
        parse the 'import' block
        :return:
        """
        current_import = self.get_import_from_content()

        # check the changes between the case content in db and the edit text content
        is_import_no_updated = (len(self.import_lines) == len(current_import)) and (set(current_import) == set(self.import_lines))
        if is_import_no_updated:
            return
        if self.kw_core.kw_func != self.kw_core.default_func:
            self.kw_core.kw_func.clear()
            self.kw_core.kw_func = {**self.kw_core.default_func}
        self.import_lines = current_import
        for import_cmd in self.import_lines:
            try:
                self.kw_core.parse_line(import_cmd)
            except Exception as e:
                self.parse_error_info_signal.emit("<font color='red'>" + str(e) + "</font>")
        self.update_completer_high_lighter()

    def update_completer_high_lighter(self):
        """
        update completer and high lighter
        :return:
        """
        if not self.kw_core.kw_func:
            return
        self.cmp.func_dict = self.kw_core.kw_func  # update completer's func_list
        # update highlighter's kw list
        kw_list = set()
        for func_name, func in self.cmp.func_dict.items():
            kw_list.add(func_name)
        self.high_lighter.__init__(self, kw_list)
        # refresh the text
        tc = self.textCursor()
        content = self.toPlainText()
        index = tc.position()
        self.setText(content)
        tc.setPosition(index)
        self.setTextCursor(tc)
        self.activateWindow()

    def current_item_down(self, current_row):
        """
        move down to the next item
        :param current_row:
        :return:
        """
        if current_row == self.popup_widget.func_list_widget.count() - 1:
            self.popup_widget.func_list_widget.setCurrentRow(current_row)
            return
        self.popup_widget.func_list_widget.setCurrentRow(current_row + 1)
        item_text = self.popup_widget.func_list_widget.currentItem().text()
        item_desc = ""
        if item_text in self.cmp.get_func_name_list(self.kw_core.kw_func):
            if self.cmp.func_dict[item_text].__doc__:
                item_desc = self.cmp.func_dict[item_text].__doc__
        self.popup_widget.selected_func_name_signal.emit(item_text, item_desc)

    def current_item_up(self, current_row):
        """
        move up to the previous item
        :param current_row:
        :return:
        """
        if current_row == 0:
            self.popup_widget.func_list_widget.setCurrentRow(current_row)
            return
        self.popup_widget.func_list_widget.setCurrentRow(current_row - 1)
        item_text = self.popup_widget.func_list_widget.currentItem().text()
        item_desc = ""
        if item_text in self.kw_core.kw_func:
            if self.cmp.func_dict[item_text].__doc__:
                item_desc = self.cmp.func_dict[item_text].__doc__
        self.popup_widget.selected_func_name_signal.emit(item_text, item_desc)


class Completer(QCompleter):
    def __init__(self, debug_runner, parent=None):
        super(Completer, self).__init__(parent)
        self.debug_runner = debug_runner
        self.func_dict = self.debug_runner.get_func("")
        self.popup_widget = None
        self.func_name_list = self.get_func_name_list(self.func_dict)

    def update(self, completion_text, popup_widget):
        match_str_list = []
        self.popup_widget = popup_widget
        popup_widget.func_list_widget.clear()
        text_prefix = ""   # the prefix of the word
        all_completer_word_list = []  # all the word that waiting for matched

        if completion_text.startswith("$") and (not completion_text.endswith(".")):  # match var
            text_prefix = completion_text[1:]
            all_completer_word_list = self.debug_runner.get_var(text_prefix)
        elif completion_text.startswith("$") and (completion_text.endswith(".")):  # match var property
            var_word = completion_text[1:].split(".")[0]  # get var word
            text_prefix = completion_text[1:].split(".")[1]  # get property prefix
            all_completer_word_list = self.debug_runner.get_property(var_word, text_prefix)
        else:  # match func name
            all_completer_word_list = self.debug_runner.get_func(completion_text)
            text_prefix = completion_text

        for completer_word in all_completer_word_list:
            if text_prefix in completer_word and text_prefix != completer_word:
                match_str_list.append(completer_word)
                popup_widget.func_list_widget.addItem(completer_word)
        popup_widget.func_list_widget.sortItems()  # ASC

        if len(match_str_list) < 1:
            popup_widget.hide()
            return
        self.init_completer_widget()

    def init_completer_widget(self):
        """
        init the completer widget's data
        :return:
        """
        self.popup_widget.show()
        self.popup_widget.setFocusPolicy(Qt.NoFocus)
        # set the current item
        self.popup_widget.func_list_widget.setCurrentRow(0)
        item_text = self.popup_widget.func_list_widget.currentItem().text()
        item_desc = ""
        if item_text in self.func_name_list:
            if self.func_dict[item_text].__doc__:
                item_desc = self.func_dict[item_text].__doc__
        self.popup_widget.selected_func_name_signal.emit(item_text, item_desc)

    def get_func_name_list(self, func_dict):
        """
        get function name list
        :param func_dict:
        :return:
        """
        func_name_list = []
        for func_name, func in func_dict.items():
            func_name_list.append(func_name)
        return func_name_list
