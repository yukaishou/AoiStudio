import json
import os
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QListWidget, QListWidgetItem, QLineEdit, QPushButton,
                             QLabel, QMessageBox, QMainWindow)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QIcon


class CharacterEditorWidget(QMainWindow):
    """
    角色编辑器【独立弹窗窗口】
    仅弹窗使用：editor = CharacterEditorWidget(parent=None,file_path="xxx"); editor.show()
    ⚠本类继承QMainWindow，不支持嵌入其他窗口布局/Dock
    """
    def __init__(self, parent=None, file_path=None):
        super().__init__(parent)
        self.characters = []
        self.file_path = file_path
        self.init_ui()

        # 如果传入文件路径，自动加载，增加异常捕获
        if self.file_path is not None:
            self.load_from_file()

    def init_ui(self):
        self.setWindowTitle("角色编辑器")
        self.resize(620, 420)
        if os.path.exists("res/AoiStudio.png"):
            self.setWindowIcon(QIcon("res/AoiStudio.png"))

        # QMainWindow必须创建centralWidget，布局挂在它上面，禁止直接self.setLayout()
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        main_layout.addWidget(QLabel("<h3>角色编辑器</h3>"))

        h_layout = QHBoxLayout()

        self.list_widget = QListWidget()
        self.list_widget.setMinimumWidth(180)
        self.list_widget.currentItemChanged.connect(self.on_select_item)
        h_layout.addWidget(self.list_widget)

        edit_layout = QVBoxLayout()
        edit_layout.addWidget(QLabel("角色名称:"))
        self.edit_name = QLineEdit()
        edit_layout.addWidget(self.edit_name)

        btn_layout = QHBoxLayout()
        self.btn_new = QPushButton("新增角色")
        self.btn_new.clicked.connect(self.add_new_character)
        self.btn_save = QPushButton("保存修改")
        self.btn_save.clicked.connect(self.save_current_edit)
        self.btn_del = QPushButton("删除选中")
        self.btn_del.clicked.connect(self.delete_selected)

        btn_layout.addWidget(self.btn_new)
        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_del)
        edit_layout.addLayout(btn_layout)
        edit_layout.addStretch()

        h_layout.addLayout(edit_layout)
        main_layout.addLayout(h_layout)

    def load_from_file(self):
        """从file_path读取json，捕获异常"""
        if not os.path.exists(self.file_path):
            QMessageBox.warning(self, "警告", f"角色文件不存在：{self.file_path}")
            return
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.load_json_data(data)
        except Exception as e:
            QMessageBox.critical(self, "读取失败", f"读取角色配置失败:\n{str(e)}")

    def load_json_data(self, data: dict):
        self.characters = data.get("characters", [])
        self.refresh_list()

    def get_json_data(self) -> dict:
        return {"characters": self.characters}

    def refresh_list(self):
        self.list_widget.clear()
        for idx, ch in enumerate(self.characters):
            item = QListWidgetItem(ch.get("name", f"角色{idx}"))
            item.setData(Qt.UserRole, idx)
            self.list_widget.addItem(item)

    def on_select_item(self, item: QListWidgetItem):
        if not item:
            self.edit_name.clear()
            return
        idx = item.data(Qt.UserRole)
        ch = self.characters[idx]
        self.edit_name.setText(ch.get("name", ""))

    def add_new_character(self):
        self.characters.append({"name": ""})
        self.refresh_list()
        self.list_widget.setCurrentRow(len(self.characters)-1)

    def save_current_edit(self):
        item = self.list_widget.currentItem()
        if not item:
            QMessageBox.warning(self, "提示", "请先选择一个角色")
            return
        idx = item.data(Qt.UserRole)
        new_name = self.edit_name.text().strip()
        self.characters[idx]["name"] = new_name
        self.refresh_list()

        if self.file_path:
            try:
                with open(self.file_path, "w", encoding="utf-8") as f:
                    json.dump(self.get_json_data(), f, ensure_ascii=False, indent=4)
                QMessageBox.information(self, "提示", "保存成功")
            except Exception as e:
                QMessageBox.critical(self, "保存失败", f"写入文件失败:\n{str(e)}")

    def delete_selected(self):
        item = self.list_widget.currentItem()
        if not item:
            return
        idx = item.data(Qt.UserRole)
        del self.characters[idx]
        self.refresh_list()
        self.edit_name.clear()


# ============ 示例运行 ============
if __name__ == "__main__":
    app = QApplication([])
    # 使用系统默认字体，自动兼容中文
    default_font = app.font()
    default_font.setStyleHint(QFont.System)
    app.setFont(default_font)

    init_data = {
        "characters": [
            {"name": "马里奥"},
            {"name": "千绘莉"},
            {"name": "柚希"}
        ]
    }

    win = CharacterEditorWidget()
    win.load_json_data(init_data)

    def print_result():
        output = win.get_json_data()
        print(json.dumps(output, indent=2, ensure_ascii=False))

    test_btn = QPushButton("打印当前JSON")
    test_btn.clicked.connect(print_result)
    # 加到centralWidget的布局
    win.centralWidget().layout().addWidget(test_btn)

    win.show()
    app.exec()