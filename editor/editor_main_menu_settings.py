import json
import os

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLineEdit, QPushButton, QLabel, QFileDialog, QTextEdit, QGroupBox)
from PyQt5.QtCore import Qt


class ProjectConfigEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("主菜单设置")
        self.setWindowIcon(QIcon("res/AoiStudio.png"))
        self.resize(600, 300)
        self.config_path = ""
        self.config_data = {
            "main_menu_ui_path": "file:gui/main_menu_ui.json",
            "save_game_ui_path": "file:gui/save_game_ui.json",
            "settings_ui_path": "file:gui/settings_ui.json",
            "background": "None",
            "bgm": "None"
        }
        self.init_ui()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        # 操作按钮栏
        btn_layout = QHBoxLayout()
        self.btn_load = QPushButton("加载配置JSON")
        self.btn_load.clicked.connect(self.load_json)
        self.btn_save = QPushButton("保存配置JSON")
        self.btn_save.clicked.connect(self.save_json)
        self.btn_new = QPushButton("重置默认配置")
        self.btn_new.clicked.connect(self.reset_default)
        #btn_layout.addWidget(self.btn_load)
        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_new)
        main_layout.addLayout(btn_layout)

        # 表单分组
        group = QGroupBox("项目配置项")
        form_layout = QVBoxLayout(group)

        def make_row(label_text, key):
            row_layout = QHBoxLayout()
            lab = QLabel(label_text)
            lab.setFixedWidth(140)
            edit = QLineEdit()
            edit.setText(self.config_data[key])
            btn_file = QPushButton("选择文件")
            btn_file.clicked.connect(lambda checked, e=edit, k=key: self.select_file(e, k))
            row_layout.addWidget(lab)
            row_layout.addWidget(edit)
            row_layout.addWidget(btn_file)
            form_layout.addLayout(row_layout)
            return edit

        self.edits = {}
        self.edits["main_menu_ui_path"] = make_row("主菜单UI", "main_menu_ui_path")
        self.edits["save_game_ui_path"] = make_row("存档界面UI", "save_game_ui_path")
        self.edits["settings_ui_path"] = make_row("设置界面UI", "settings_ui_path")
        self.edits["background"] = make_row("默认背景图", "background")
        self.edits["bgm"] = make_row("默认BGM", "bgm")

        main_layout.addWidget(group)

        # JSON预览
        preview_group = QGroupBox("JSON预览")
        preview_layout = QVBoxLayout(preview_group)
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        preview_layout.addWidget(self.preview_text)
        #main_layout.addWidget(preview_group)

        self.refresh_preview()

    def select_file(self, line_edit: QLineEdit, key):
        """选择文件，自动转为 file:相对路径"""
        file_path, _ = QFileDialog.getOpenFileName(self, "选择资源文件")
        if not file_path:
            return
        # 转为相对路径，生成 file:xxx
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
        """把界面输入回写到config_data"""
        for k, widget in self.edits.items():
            self.config_data[k] = widget.text().strip()

    def refresh_preview(self):
        self.collect_form_data()
        pretty = json.dumps(self.config_data, ensure_ascii=False, indent=2)
        self.preview_text.setPlainText(pretty)

    def load_json(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "打开配置文件", filter="JSON Files (*.json)")
        if not filepath:
            return
        self.config_path = filepath
        with open(filepath, "r", encoding="utf-8") as f:
            self.config_data = json.load(f)
        # 回写到输入框
        for k, widget in self.edits.items():
            widget.setText(self.config_data.get(k, ""))
        self.refresh_preview()

    def save_json(self):
        if not self.config_path:
            filepath, _ = QFileDialog.getSaveFileName(self, "保存配置", filter="JSON Files (*.json)")
            if not filepath:
                return
            self.config_path = filepath
        self.collect_form_data()
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.config_data, f, ensure_ascii=False, indent=2)
        self.statusBar().showMessage(f"已保存到 {self.config_path}", 2000)

    def reset_default(self):
        self.config_data = {
            "main_menu_ui_path": "file:gui/main_menu_ui.json",
            "save_game_ui_path": "file:gui/save_game_ui.json",
            "settings_ui_path": "file:gui/settings_ui.json",
            "background": "None",
            "bgm": "None"
        }
        for k, widget in self.edits.items():
            widget.setText(self.config_data[k])
        self.refresh_preview()


if __name__ == "__main__":
    app = QApplication([])
    win = ProjectConfigEditor()
    win.show()
    app.exec_()