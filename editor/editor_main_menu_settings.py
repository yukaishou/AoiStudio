import json
import os
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLineEdit, QPushButton, QLabel, QFileDialog, QTextEdit, QGroupBox)
from PyQt5.QtCore import Qt


class ConfigPopupWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("主菜单设置")
        self.resize(720, 520)
        self.config_path = ""
        self.config_data = {
            "main_menu_ui_path": "file:gui/main_menu_ui.json",
            "save_game_ui_path": "file:gui/save_game_ui.json",
            "settings_ui_path": "file:gui/settings_ui.json",
            "background": "file:backgrounds/BG_1.jpeg",
            "bgm": "file:bgms/bgm2.mp3"
        }
        self._edits = {}
        self._preview_text = None

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        # 按钮栏
        btn_layout = QHBoxLayout()
        self.btn_load = QPushButton("加载配置JSON")
        self.btn_load.clicked.connect(self.load_json)
        self.btn_save = QPushButton("保存配置JSON")
        self.btn_save.clicked.connect(self.save_json)
        self.btn_reset = QPushButton("重置默认配置")
        self.btn_reset.clicked.connect(self.reset_default)
        #btn_layout.addWidget(self.btn_load)
        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_reset)
        main_layout.addLayout(btn_layout)

        group = QGroupBox("项目配置项")
        form_layout = QVBoxLayout(group)

        def make_row(label_text, key):
            row_layout = QHBoxLayout()
            lab = QLabel(label_text)
            lab.setFixedWidth(140)
            edit = QLineEdit()
            edit.setText(self.config_data[key])
            btn_file = QPushButton("选择文件")
            btn_file.clicked.connect(lambda ch, e=edit, k=key: self.select_file(e, k))
            row_layout.addWidget(lab)
            row_layout.addWidget(edit)
            row_layout.addWidget(btn_file)
            form_layout.addLayout(row_layout)
            self._edits[key] = edit

        make_row("主菜单UI", "main_menu_ui_path")
        make_row("存档界面UI", "save_game_ui_path")
        make_row("设置界面UI", "settings_ui_path")
        make_row("默认背景图", "background")
        make_row("默认BGM", "bgm")

        main_layout.addWidget(group)

        preview_group = QGroupBox("JSON预览")
        preview_layout = QVBoxLayout(preview_group)
        self._preview_text = QTextEdit()
        self._preview_text.setReadOnly(True)
        preview_layout.addWidget(self._preview_text)
        main_layout.addWidget(preview_group)

        self.refresh_preview()

    def select_file(self, line_edit: QLineEdit, key):
        if not self.isWidgetType():
            return
        file_path, _ = QFileDialog.getOpenFileName(self, "选择资源文件")
        if not file_path:
            return
        base_dir = os.path.dirname(self.config_path) if self.config_path else os.getcwd()
        try:
            rel_path = os.path.relpath(file_path, base_dir)
            rel_path = rel_path.replace("\\", "/")
            line_edit.setText(f"file:{rel_path}")
        except Exception:
            line_edit.setText(f"file:{file_path}")
        self.collect_form_data()
        self.refresh_preview()

    def collect_form_data(self):
        if not self.isWidgetType():
            return
        for k, widget in self._edits.items():
            if widget and widget.isWidgetType():
                self.config_data[k] = widget.text().strip()

    def refresh_preview(self):
        # 核心防护：窗口/控件已销毁直接返回
        if not self.isWidgetType():
            return
        if self._preview_text is None or not self._preview_text.isWidgetType():
            return
        self.collect_form_data()
        pretty = json.dumps(self.config_data, ensure_ascii=False, indent=2)
        self._preview_text.setPlainText(pretty)

    def load_json(self,path):
        if not self.isWidgetType():
            return
        if path:
            self.config_path = path
            filepath = path
        else:
            filepath, _ = QFileDialog.getOpenFileName(self, "打开配置文件", filter="JSON Files (*.json)")
        if not filepath:
            return
        self.config_path = filepath
        with open(filepath, "r", encoding="utf-8") as f:
            self.config_data = json.load(f)
        for k, w in self._edits.items():
            if w and w.isWidgetType():
                w.setText(self.config_data.get(k, ""))
        self.refresh_preview()

    def save_json(self):
        if not self.isWidgetType():
            return
        if not self.config_path:
            filepath, _ = QFileDialog.getSaveFileName(self, "保存配置", filter="JSON Files (*.json)")
            if not filepath:
                return
            self.config_path = filepath
        self.collect_form_data()
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.config_data, f, ensure_ascii=False, indent=2)

    def reset_default(self):
        if not self.isWidgetType():
            return
        self.config_data = {
            "main_menu_ui_path": "file:gui/main_menu_ui.json",
            "save_game_ui_path": "file:gui/save_game_ui.json",
            "settings_ui_path": "file:gui/settings_ui.json",
            "background": "file:backgrounds/BG_1.jpeg",
            "bgm": "file:bgms/bgm2.mp3"
        }
        for k, w in self._edits.items():
            if w and w.isWidgetType():
                w.setText(self.config_data[k])
        self.refresh_preview()

    def closeEvent(self, event):
        """弹窗关闭事件，清空内部引用，切断悬空对象"""
        self._edits.clear()
        self._preview_text = None
        super().closeEvent(event)