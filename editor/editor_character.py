import json
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QListWidget, QListWidgetItem, QLineEdit, QPushButton,
                             QLabel, QMessageBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QIcon


class CharacterEditorWidget(QWidget):
    """
    角色编辑器组件：独立Widget，可以：
    1. 作为弹窗：editor = CharacterEditorWidget(); editor.show()
    2. 嵌入主窗口布局：main_layout.addWidget(editor)
    ✅完整支持中文输入、显示、JSON导出
    """
    def __init__(self, parent=None,file_path=None):
        super().__init__(parent)
        self.characters = []  # 存储角色数据 [{"name": "xxx"}, ...]
        self.file_path = file_path
        self.init_ui()
        self.load_json_data(json.load(open(self.file_path, encoding="utf-8")))
    def init_ui(self):
        self.setWindowTitle("角色编辑器")
        self.setWindowIcon(QIcon("res/AoiStudio.png"))
        main_layout = QVBoxLayout(self)

        # 标题
        main_layout.addWidget(QLabel("<h3>角色编辑器</h3>"))

        # 水平分割：角色列表 | 编辑区
        h_layout = QHBoxLayout()

        # 角色列表
        self.list_widget = QListWidget()
        self.list_widget.setMinimumWidth(180)
        self.list_widget.currentItemChanged.connect(self.on_select_item)
        h_layout.addWidget(self.list_widget)

        # 编辑面板
        edit_layout = QVBoxLayout()
        edit_layout.addWidget(QLabel("角色名称:"))
        self.edit_name = QLineEdit()
        edit_layout.addWidget(self.edit_name)

        # 按钮行
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

        self.setLayout(main_layout)

    def load_json_data(self, data: dict):
        """加载json数据，输入 {"characters": [{"name":"马里奥"}]}"""
        self.characters = data.get("characters", [])
        self.refresh_list()

    def get_json_data(self) -> dict:
        """获取编辑后的完整json结构"""
        return {"characters": self.characters}

    def refresh_list(self):
        """刷新列表控件"""
        self.list_widget.clear()
        for idx, ch in enumerate(self.characters):
            item = QListWidgetItem(ch.get("name", f"角色{idx}"))
            item.setData(Qt.UserRole, idx)
            self.list_widget.addItem(item)

    def on_select_item(self, item: QListWidgetItem):
        """选中列表项，填充到输入框"""
        if not item:
            self.edit_name.clear()
            return
        idx = item.data(Qt.UserRole)
        ch = self.characters[idx]
        self.edit_name.setText(ch.get("name", ""))

    def add_new_character(self):
        """新增空白角色"""
        self.characters.append({"name": ""})
        self.refresh_list()
        self.list_widget.setCurrentRow(len(self.characters)-1)

    def save_current_edit(self):
        """保存当前选中项的修改"""
        item = self.list_widget.currentItem()
        if not item:
            QMessageBox.warning(self, "提示", "请先选择一个角色")
            return
        idx = item.data(Qt.UserRole)
        new_name = self.edit_name.text().strip()
        self.characters[idx]["name"] = new_name
        self.refresh_list()
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(self.get_json_data(), f, ensure_ascii=False, indent=4)
        QMessageBox.information(self, "提示", "保存成功")

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
    # 全局设置中文字体，解决方框乱码
    #font = QFont()
    #font.setFamily("SimHei")  # 黑体 Windows; Linux/Mac自动降级
    #app.setFont(font)

    # 初始测试数据，中文角色测试
    init_data = {
        "characters": [
            {"name": "马里奥"},
            {"name": "千绘莉"},
            {"name": "柚希"}
        ]
    }

    win = CharacterEditorWidget()
    win.load_json_data(init_data)
    win.resize(600,400)

    # 打印JSON，关键：ensure_ascii=False 输出原始中文，不要转义
    def print_result():
        output = win.get_json_data()
        print(json.dumps(output, indent=2, ensure_ascii=False))

    test_btn = QPushButton("打印当前JSON")
    test_btn.clicked.connect(print_result)
    win.layout().addWidget(test_btn)

    win.show()
    app.exec_()