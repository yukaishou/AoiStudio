import re
import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton,
                               QCompleter, QFileDialog, QMessageBox)
from PySide6.QtCore import Qt, QStringListModel
from PySide6.QtGui import (QSyntaxHighlighter, QTextCharFormat, QColor, QTextCursor)


# ====================== Python语法高亮（配色对齐你的CFG高亮） ======================
class PythonHighlighter(QSyntaxHighlighter):
    def __init__(self, parent):
        super().__init__(parent)
        self.rules = []

        # 注释
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#6A9955"))
        self.rules.append((re.compile(r"#.*$"), comment_format))

        # Python关键字
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#569cd6"))
        keywords = r"\b(and|as|assert|async|await|break|class|continue|def|del|elif|else|except|finally|for|from|global|if|import|in|is|lambda|nonlocal|not|or|pass|raise|return|try|while|with|yield|True|False|None)\b"
        self.rules.append((re.compile(keywords), keyword_format))

        # 字符串 双引号
        str_double_format = QTextCharFormat()
        str_double_format.setForeground(QColor("#CE9178"))
        self.rules.append((re.compile(r'"[^"\\]*(\\.[^"\\]*)*"'), str_double_format))
        # 单引号
        str_single_format = QTextCharFormat()
        str_single_format.setForeground(QColor("#CE9178"))
        self.rules.append((re.compile(r"'[^'\\]*(\\.[^'\\]*)*'"), str_single_format))

        # 数字
        num_format = QTextCharFormat()
        num_format.setForeground(QColor("#B5CEA8"))
        self.rules.append((re.compile(r"\b\d+\.?\d*|\.\d+\b"), num_format))

        # 内置函数简单标记
        builtin_fmt = QTextCharFormat()
        builtin_fmt.setForeground(QColor("#4EC9B0"))
        builtins = r"\b(print|len|range|input|int|str|float|list|dict|set|tuple|open|abs|max|min|sum)\b"
        self.rules.append((re.compile(builtins), builtin_fmt))

        # 装饰器 @xxx
        decor_fmt = QTextCharFormat()
        decor_fmt.setForeground(QColor("#C586C0"))
        self.rules.append((re.compile(r"@\w+"), decor_fmt))

    def highlightBlock(self, text):
        for pattern, fmt in self.rules:
            for match in pattern.finditer(text):
                self.setFormat(match.start(), match.end() - match.start(), fmt)


# ====================== Python专用文本编辑控件（拷贝你PureCFGTextEdit逻辑） ======================
class PurePyTextEdit(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.completer: QCompleter | None = None
        self.setFontFamily("Consolas")
        self.setFontPointSize(12)
        self.setTabStopDistance(4 * 4)  # Tab等于4空格

    def set_completer(self, completer: QCompleter):
        self.completer = completer
        completer.setWidget(self)

    def trigger_completion(self):
        if not self.completer:
            return
        cursor = self.textCursor()
        cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        prefix = cursor.selectedText()
        self.completer.setCompletionPrefix(prefix)
        popup = self.completer.popup()
        rect = self.cursorRect()
        rect.setWidth(popup.sizeHintForColumn(0))
        popup.setGeometry(rect)
        popup.show()

    def keyPressEvent(self, event):
        # Tab唤起补全
        if event.key() == Qt.Key_Tab and self.completer:
            self.trigger_completion()
            return

        if self.completer and self.completer.popup().isVisible():
            if event.key() in (Qt.Key_Enter, Qt.Key_Return, Qt.Key_Space, Qt.Key_Tab):
                event.accept()
                self.completer.popup().hide()
                return

        super().keyPressEvent(event)

    def focusInEvent(self, event):
        if self.completer:
            self.completer.popup().hide()
        super().focusInEvent(event)


# ====================== Python脚本编辑器主组件，接口完全对齐CFGCommandEditor ======================
class PyScriptEditor(QWidget):
    # Python补全候选列表，模仿你CFG_SUGGEST
    PY_SUGGEST = [
        "def func_name():",
        "for i in range(10):",
        "if condition:",
        "elif condition:",
        "else:",
        "while True:",
        "print()",
        "len()",
        "try:",
        "except Exception as e:",
        "import ",
        "from xxx import yyy",
        "class MyClass:",
        "return ",
        "# ",
        "\"\"\"docstring\"\"\""
    ]

    def __init__(self, decoder=None, parent=None, file_path=None):
        super().__init__(parent)
        self.decoder = decoder
        self.edit_file_path: str | None = file_path
        self._dirty = False

        self.init_ui()
        self.init_completer()

        if self.edit_file_path and os.path.exists(self.edit_file_path):
            self.load_file(self.edit_file_path)

        self.update_title_label()
        self.edit.textChanged.connect(self.on_text_changed)
        self.update_button_state()

    def set_decoder(self, decoder):
        """外部注入执行器decoder，需要实现 execute(text), execute_line(line), reset()"""
        self.decoder = decoder
        self.update_button_state()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        btn_layout = QHBoxLayout()
        self.btn_run_line = QPushButton("执行当前行(Shift+F5)")
        self.btn_run_all = QPushButton("执行全部(F5)")
        self.btn_reset_decoder = QPushButton("重置Python执行器")
        self.btn_save = QPushButton("保存")
        self.btn_save_as = QPushButton("另存为…")

        self.btn_run_line.clicked.connect(self.run_current_line)
        self.btn_run_all.clicked.connect(self.run_all)
        self.btn_reset_decoder.clicked.connect(self.reset_decoder)
        self.btn_save.clicked.connect(self.save_script)
        self.btn_save_as.clicked.connect(self.save_as)

        # 如果你不需要运行按钮，可以注释下面三行，和你cfg代码保持一致
        #btn_layout.addWidget(self.btn_run_line)
        #btn_layout.addWidget(self.btn_run_all)
        #btn_layout.addWidget(self.btn_reset_decoder)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_save_as)

        self.edit = PurePyTextEdit()
        self.edit.setPlaceholderText(
            "Python脚本编辑器\n"
            "Tab唤起代码补全\n"
            "⚠️ 实际执行由外部decoder提供，本组件不内置Python解释器\n"
        )
        self.hlighter = PythonHighlighter(self.edit.document())

        layout.addLayout(btn_layout)
        layout.addWidget(self.edit)

    def init_completer(self):
        completer = QCompleter(self.PY_SUGGEST, self)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.activated.connect(self.insert_completion)
        self.edit.set_completer(completer)

    def insert_completion(self, text: str):
        cursor = self.edit.textCursor()
        cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        cursor.insertText(text)

    def on_text_changed(self):
        self._dirty = True
        self.update_title_label()

    def update_title_label(self):
        base = "Python脚本编辑器"
        path = self.edit_file_path if self.edit_file_path else "[未命名]"
        star = " *" if self._dirty else ""
        self.setWindowTitle(f"{base} — {path}{star}")

    def update_button_state(self):
        enable = self.decoder is not None
        self.btn_run_line.setEnabled(enable)
        self.btn_run_all.setEnabled(enable)
        self.btn_reset_decoder.setEnabled(enable)

    # ========== 运行控制（全部委托外部decoder，本控件不执行任何exec/eval） ==========
    def run_current_line(self):
        if not self.decoder:
            QMessageBox.warning(self, "警告", "Python执行器decoder未绑定！")
            return
        line = self.edit.textCursor().block().text().strip()
        if line:
            self.decoder.execute_line(line)

    def run_all(self):
        if not self.decoder:
            QMessageBox.warning(self, "警告", "Python执行器decoder未绑定！")
            return
        text = self.edit.toPlainText()
        if text.strip():
            self.decoder.execute(text)

    def reset_decoder(self):
        if not self.decoder:
            return
        self.decoder.reset()
        QMessageBox.information(self, "提示", "Python执行器已重置")

    # ========== 文件读写接口，和CFG版本1:1对齐 ==========
    def set_script(self, text: str):
        self.edit.setPlainText(text)
        self._dirty = False
        self.update_title_label()

    def get_script(self) -> str:
        return self.edit.toPlainText()

    def load_file(self, filepath: str):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                self.set_script(f.read())
            self.edit_file_path = filepath
            self._dirty = False
            self.update_title_label()
        except Exception as e:
            QMessageBox.critical(self, "读取失败", f"无法读取文件：{e}")

    def save_script(self):
        if not self.edit_file_path:
            return self.save_as()
        try:
            with open(self.edit_file_path, "w", encoding="utf-8") as f:
                f.write(self.get_script())
            self._dirty = False
            self.update_title_label()
        except Exception as e:
            QMessageBox.critical(self, "保存失败", str(e))

    def save_as(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "另存Python脚本", "", "Python脚本(*.py);;全部文件(*)"
        )
        if not path:
            return
        self.edit_file_path = path
        self.save_script()

    def is_dirty(self) -> bool:
        return self._dirty