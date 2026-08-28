import re
import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton,
                               QCompleter, QFileDialog, QMessageBox)
from PySide6.QtCore import Qt, QStringListModel, QKeyCombination


# CFG指令补全模板（模块级常量，供编辑器和高亮器共享）
CFG_SUGGEST = [
    "add game_object obj_name px py rot sx sy",
    "add component obj_name ComponentName {{\"key\": \"value\"}}",
    "add character file:characters/sprite.png x y",
    "add background file:bg/bg01.png",
    "add flag flag_name",
    "remove character index",
    "remove flag flag_name",
    "move character idx tx ty ease dur",
    "switch background file:bg.png fade 0.5",
    "switch bgm file:bgm/test.ogg 1.0",
    "animation character idx fade_to alpha duration",
    "animation character idx shake amp dur",
    "animation character idx jump height dur",
    "affection add char_name value",
    "affection set char_name value",
    "affection reduce char_name value",
    "wait 2.0",
    "run file:path/to/script.cfg",
    "jump dialogue_file file:dialogue/test.cfg",
    "jump dialogue_index 0",
    "if have_flags:flag_name",
    "else",
    "endif",
    "quit"
]
from PySide6.QtGui import (QSyntaxHighlighter, QTextCharFormat, QColor, QKeySequence,
                           QTextCursor)


# ====================== 语法高亮 ======================
class CFGHighlighter(QSyntaxHighlighter):
    def __init__(self, parent):
        super().__init__(parent)
        #self.setDocumentHighlightingEnabled(True)
        self.rules = []

        # 1.注释 优先级最高
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#6A9955"))
        self.rules.append((re.compile(r"//.*$"), comment_format))

        # 主命令关键字
        cmd_format = QTextCharFormat()
        cmd_format.setForeground(QColor("#569cd6"))
        cmd_words = r"\b(add|move|switch|animation|remove|affection|wait|jump|quit|run|if|else|endif|true|false)\b"
        self.rules.append((re.compile(cmd_words), cmd_format))

        # 文件路径 file:xxx
        path_format = QTextCharFormat()
        path_format.setForeground(QColor("#4EC9B0"))
        self.rules.append((re.compile(r"file:\S+"), path_format))

        # flag标识
        flag_format = QTextCharFormat()
        flag_format.setForeground(QColor("#C586C0"))
        self.rules.append((re.compile(r"\bflag:\w+\b"), flag_format))
        self.rules.append((re.compile(r"\bhave_flags:\S+"), flag_format))

        # 条件前缀
        cond_format = QTextCharFormat()
        cond_format.setForeground(QColor("#C586C0"))
        self.rules.append((re.compile(r"\baffection:\S+"), cond_format))

        # 数字（整数浮点数）
        num_format = QTextCharFormat()
        num_format.setForeground(QColor("#B5CEA8"))
        self.rules.append((re.compile(r"\d+\.?\d*|\.\d+"), num_format))

        # 大括号 {}
        brace_format = QTextCharFormat()
        brace_format.setForeground(QColor("#DCDCAA"))
        self.rules.append((re.compile(r"[{}]"), brace_format))

        #字符串
        str_format = QTextCharFormat()
        str_format.setForeground(QColor("#B5CEA8"))
        self.rules.append((re.compile(r'".*?"'), str_format))



    def highlightBlock(self, text):
        for pattern, fmt in self.rules:
            for match in pattern.finditer(text):
                self.setFormat(match.start(), match.end() - match.start(), fmt)


# ====================== 文本编辑控件 ======================
class PureCFGTextEdit(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.completer: QCompleter | None = None
        self.setFontFamily("Consolas")
        self.setFontPointSize(12)
        self.setTabStopDistance(4 * 4)  # Tab宽度4字符

    def set_completer(self, completer: QCompleter):
        self.completer = completer
        completer.setWidget(self)

    def trigger_completion(self):
        """手动触发补全弹窗，根据当前行首词过滤建议"""
        if not self.completer:
            return
        cursor = self.textCursor()
        block = cursor.block()
        line_text = block.text().strip()
        first_word = line_text.split()[0].lower() if line_text else ""

        # 根据行首词过滤补全项
        filtered = [s for s in CFG_SUGGEST
                     if s.lower().startswith(first_word) or not first_word]

        completer_model = self.completer.completionModel()
        original_strings = [completer_model.data(completer_model.index(i))
                            for i in range(completer_model.rowCount())]
        # 临时替换补全列表
        self.completer.setModel(QStringListModel(filtered if filtered else original_strings))

        cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        prefix = cursor.selectedText()
        self.completer.setCompletionPrefix(prefix)
        popup = self.completer.popup()
        rect = self.cursorRect()
        rect.setWidth(popup.sizeHintForColumn(0))
        popup.setGeometry(rect)
        popup.show()

    def keyPressEvent(self, event):
        c = event.keyCombination()
        # Tab唤起补全
        if event.key() == Qt.Key_Tab and self.completer:
            self.trigger_completion()
            return

        if self.completer and self.completer.popup().isVisible():
            if event.key() in (Qt.Key_Enter, Qt.Key_Return, Qt.Key_Space, Qt.Key_Tab):
                event.accept()
                self.completer.popup().hide()
                return

        # Enter: 自动缩进
        if event.key() in (Qt.Key_Enter, Qt.Key_Return):
            cursor = self.textCursor()
            block = cursor.block()
            line_text = block.text().strip()

            # 当前行以 if 或 else 开头 → 缩进
            if line_text:
                first_word = line_text.split()[0].lower()
                if first_word in ("if", "else"):
                    cursor.insertBlock()
                    current_indent = block.text()[:len(block.text()) - len(block.text().lstrip())]
                    cursor.insertText(current_indent + "    ")
                    event.accept()
                    return
                # 当前行是 endif 或 else → 反缩进
                if first_word in ("endif",):
                    cursor.insertBlock()
                    current_indent = block.text()[:len(block.text()) - len(block.text().lstrip())]
                    # 去掉一级缩进
                    dedent = current_indent[:-4] if len(current_indent) >= 4 else ""
                    cursor.insertText(dedent)
                    event.accept()
                    return

            # 否则保留当前行缩进
            cursor.insertBlock()
            current_indent = block.text()[:len(block.text()) - len(block.text().lstrip())]
            cursor.insertText(current_indent)
            event.accept()
            return

        # Backspace: 在行首且前面是空格时删除一个缩进单位(4空格)
        if event.key() == Qt.Key_Backspace:
            cursor = self.textCursor()
            if cursor.columnNumber() > 0:
                block = cursor.block()
                text_before = block.text()[:cursor.columnNumber()]
                if text_before == text_before.lstrip():
                    # 光标后无非空白字符（光标在缩进末尾或已删到内容）
                    indent_len = len(text_before) - len(text_before.lstrip())
                    delete_count = min(indent_len, 4)
                    if delete_count > 0:
                        for _ in range(delete_count):
                            cursor.deletePreviousChar()
                        event.accept()
                        return

        super().keyPressEvent(event)

    def focusInEvent(self, event):
        if self.completer:
            self.completer.popup().hide()
        super().focusInEvent(event)


# ====================== CFG编辑器主组件 ======================
class CFGCommandEditor(QWidget):
    def __init__(self, decoder=None, parent=None, file_path=None):
        super().__init__(parent)
        self.decoder = decoder
        self.edit_file_path: str | None = file_path
        self._dirty = False  # 是否修改未保存

        self.init_ui()
        self.init_completer()

        if self.edit_file_path and os.path.exists(self.edit_file_path):
            self.load_file(self.edit_file_path)

        self.update_title_label()
        self.edit.textChanged.connect(self.on_text_changed)
        self.update_button_state()

    def set_decoder(self, decoder):
        self.decoder = decoder
        self.update_button_state()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        btn_layout = QHBoxLayout()
        self.btn_run_line = QPushButton("执行当前行(Shift+F5)")
        self.btn_run_all = QPushButton("执行全部(F5)")
        self.btn_reset_decoder = QPushButton("重置CFG解码器")
        self.btn_save = QPushButton("保存")
        self.btn_save_as = QPushButton("另存为…")

        self.btn_run_line.clicked.connect(self.run_current_line)
        self.btn_run_all.clicked.connect(self.run_all)
        self.btn_reset_decoder.clicked.connect(self.reset_decoder)
        self.btn_save.clicked.connect(self.save_script)
        self.btn_save_as.clicked.connect(self.save_as)

        #btn_layout.addWidget(self.btn_run_line)
        #btn_layout.addWidget(self.btn_run_all)
        #btn_layout.addWidget(self.btn_reset_decoder)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_save_as)

        self.edit = PureCFGTextEdit()
        self.edit.setPlaceholderText(
            "CFG脚本编辑器\n"
            "语法：换行分隔语句，{}支持代码块，//注释\n"
            "if/else/endif 支持条件分支，Enter自动缩进\n"
            "Tab唤起指令补全"
        )
        self.hlighter = CFGHighlighter(self.edit.document())

        layout.addLayout(btn_layout)
        layout.addWidget(self.edit)

        # ========== 修复快捷键，使用QAction ==========
        #self.act_run_all = self.edit.addAction("执行全部", self.run_all)
        #self.act_run_all.setShortcut(Qt.Key_F5)

        #self.act_run_line = self.edit.addAction("执行当前行", self.run_current_line)
        #self.act_run_line.setShortcut("Shift+F5")

    def init_completer(self):
        completer = QCompleter(CFG_SUGGEST, self)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.activated.connect(self.insert_completion)
        self.edit.set_completer(completer)

    def insert_completion(self, text: str):
        cursor = self.edit.textCursor()
        # 选中当前行的已输入内容并替换为补全文本
        block_start = cursor.block().position()
        # 找到当前行光标前第一个非空白字符位置
        block_text = cursor.block().text()
        visible_pos = cursor.position() - block_start
        # 回退到当前单词开头
        i = visible_pos
        while i > 0 and not block_text[i-1].isspace():
            i -= 1
        cursor.setPosition(block_start + i)
        cursor.setPosition(cursor.position() + (visible_pos - i), QTextCursor.MoveMode.KeepAnchor)
        cursor.insertText(text)

    def on_text_changed(self):
        self._dirty = True
        self.update_title_label()

    def update_title_label(self):
        """窗口标题标记脏状态"""
        base = "CFG脚本编辑器"
        path = self.edit_file_path if self.edit_file_path else "[未命名]"
        star = " *" if self._dirty else ""
        self.setWindowTitle(f"{base} — {path}{star}")

    def update_button_state(self):
        enable = self.decoder is not None
        self.btn_run_line.setEnabled(enable)
        self.btn_run_all.setEnabled(enable)
        self.btn_reset_decoder.setEnabled(enable)

    # ========== 运行控制 ==========
    def run_current_line(self):
        if not self.decoder:
            QMessageBox.warning(self, "警告", "CFG解码器未绑定！")
            return
        line = self.edit.textCursor().block().text().strip()
        if line:
            self.decoder.execute_line(line)

    def run_all(self):
        if not self.decoder:
            QMessageBox.warning(self, "警告", "CFG解码器未绑定！")
            return
        text = self.edit.toPlainText()
        if text.strip():
            self.decoder.execute(text)

    def reset_decoder(self):
        if not self.decoder:
            return
        self.decoder.reset()
        QMessageBox.information(self, "提示", "CFG解码器队列已清空重置")

    # ========== 脚本读写接口 ==========
    def set_script(self, text: str):
        self.edit.setPlainText(text)
        self._dirty = False
        self.update_title_label()

    def get_script(self) -> str:
        return self.edit.toPlainText()

    def load_file(self, filepath: str):
        try:
            with open(filepath, "r", encoding="utf‑8") as f:
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
            with open(self.edit_file_path, "w", encoding="utf‑8") as f:
                f.write(self.get_script())
            self._dirty = False
            self.update_title_label()
        except Exception as e:
            QMessageBox.critical(self, "保存失败", str(e))

    def save_as(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "另存CFG脚本", "", "CFG脚本(*.cfg);;全部文件(*)"
        )
        if not path:
            return
        self.edit_file_path = path
        self.save_script()

    def is_dirty(self) -> bool:
        return self._dirty