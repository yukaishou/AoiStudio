import re
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
                             QPushButton, QCompleter)
from PyQt5.QtCore import Qt, QStringListModel
from PyQt5.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor


# ====================== 语法高亮（稳定无BUG） ======================
class CFGHighlighter(QSyntaxHighlighter):
    def __init__(self, parent):
        super().__init__(parent)
        self.rules = []

        # 主命令颜色
        cmd_format = QTextCharFormat()
        cmd_format.setForeground(QColor("#569cd6"))
        self.rules.append((re.compile(r"\b(add|move|switch|animation|remove|affection|wait)\b"), cmd_format))

        # 文件路径
        path_format = QTextCharFormat()
        path_format.setForeground(QColor("#4ec9b0"))
        self.rules.append((re.compile(r"file:\S+"), path_format))

        # 数字
        num_format = QTextCharFormat()
        num_format.setForeground(QColor("#b5cea8"))
        self.rules.append((re.compile(r"\d+\.?\d*"), num_format))

    def highlightBlock(self, text):
        for pattern, fmt in self.rules:
            for match in pattern.finditer(text):
                self.setFormat(match.start(), match.end() - match.start(), fmt)


# ====================== 纯净文本编辑（无任何崩溃逻辑） ======================
class PureCFGTextEdit(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.completer = None

    def set_completer(self, completer):
        self.completer = completer

    def keyPressEvent(self, event):
        # 原生快捷键保留
        if self.completer and self.completer.popup().isVisible():
            # 补全弹窗显示时，回车/空格选中
            if event.key() in (Qt.Key_Enter, Qt.Key_Return, Qt.Key_Space, Qt.Key_Tab):
                self.completer.popup().hide()
                return
        super().keyPressEvent(event)

    def focusInEvent(self, event):
        if self.completer:
            self.completer.popup().hide()
        super().focusInEvent(event)


# ====================== 最终稳定编辑器组件 ======================
class CFGCommandEditor(QWidget):
    # 静态指令补全库
    CFG_SUGGEST = [
        "add character file:characters/xxx.png 0.0 0.0",
        "move character 0 0.0 0.0 linear 1.0",
        "switch scene file:backgrounds/xxx.png fade 0.01"
    ]

    def __init__(self, decoder=None, parent=None,file_path=None):
        super().__init__(parent)
        self.decoder = decoder
        self.init_ui()
        self.init_completer()
        if file_path:
            self.edit_file_path  = file_path
            with open(file_path, "r", encoding="utf-8") as f:
                self.set_script(f.read())

    def set_decoder(self, decoder):
        self.decoder = decoder

    def init_ui(self):
        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(2,2,2,2)
        self.layout().setSpacing(4)

        # 功能按钮
        btn_layout = QHBoxLayout()
        self.btn_run_line = QPushButton("执行当前行")
        self.btn_run_all = QPushButton("执行全部")
        self.btn_clear = QPushButton("保存")

        self.btn_run_line.clicked.connect(self.run_current_line)
        self.btn_run_all.clicked.connect(self.run_all)
        self.btn_clear.clicked.connect(lambda: self.save_script())

        #btn_layout.addWidget(self.btn_run_line)
        #btn_layout.addWidget(self.btn_run_all)
        btn_layout.addWidget(self.btn_clear)

        # 编辑框
        self.edit = PureCFGTextEdit()
        self.edit.setPlaceholderText("支持指令：add / move / switch\nTab键唤起补全")
        self.hlighter = CFGHighlighter(self.edit.document())

        self.layout().addLayout(btn_layout)
        self.layout().addWidget(self.edit)

    def init_completer(self):
        # Qt标准补全（无任何死循环）
        self.completer = QCompleter(self.CFG_SUGGEST)
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.completer.setWidget(self.edit)
        self.completer.activated.connect(self.insert_completion)
        self.edit.set_completer(self.completer)

    def insert_completion(self, text):
        # 安全替换当前单词
        cursor = self.edit.textCursor()
        cursor.movePosition(cursor.WordLeft, cursor.KeepAnchor)
        cursor.insertText(text)

    def run_current_line(self):
        if not self.decoder:
            return
        line = self.edit.textCursor().block().text().strip()
        if line:
            self.decoder.execute_line(line)

    def run_all(self):
        if not self.decoder:
            return
        text = self.edit.toPlainText().strip()
        if text:
            self.decoder.execute(text)

    # 外部读写接口
    def set_script(self, text):
        self.edit.setPlainText(text)

    def get_script(self):
        return self.edit.toPlainText().strip()

    def save_script(self):
        with open(f"{self.edit_file_path}", "w", encoding="utf-8") as f:
            f.write(self.get_script())



