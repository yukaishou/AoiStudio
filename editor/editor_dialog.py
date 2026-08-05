import json
import os
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
                             QFormLayout, QLineEdit, QTextEdit, QPushButton,
                             QGroupBox, QScrollArea, QFileDialog, QMessageBox)
from PyQt5.QtCore import Qt, QTimer


class DialogJsonEditor(QWidget):
    """
    对话JSON编辑器独立组件
    - 手动Apply提交修改，脏标记防丢稿
    - 30秒自动保存到**已打开的源文件**，未另存的新文件不自动保存
    - 保存完成调用外部 self.main_win.build_id_file() 生成 config/dialog_index.json
    - 支持option condition条件字段
    """
    def __init__(self, parent=None, file_path=None, main_win=None):
        super().__init__(parent)
        self.main_win = main_win   # 外部主窗口，提供 build_id_file()
        self.current_data = {
            "id": "",
            "dialogs": []
        }
        self.init_ui()

        self.selected_tree_item = None
        self.selected_dialog_index = None
        self.selected_option_index = None
        self.is_edit_project = False
        self.editing_file_path = None

        # ========== 脏标记 ==========
        self.is_dirty = False

        # ========== 自动保存定时器：30秒自动写源文件（仅已打开文件生效） ==========
        self.auto_save_timer = QTimer(self)
        self.auto_save_timer.setInterval(30 * 1000)
        self.auto_save_timer.timeout.connect(self._do_autosave)
        self.auto_save_timer.start()

        if file_path:
            with open(file_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            self.set_data(raw)
            self.is_edit_project = True
            self.editing_file_path = file_path

    def init_ui(self):
        main_layout = QHBoxLayout(self)

        # ========== 左侧对话树 ==========
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["项目"])
        self.tree.itemSelectionChanged.connect(self.on_tree_select)
        left_layout.addWidget(self.tree)

        btn_layout = QHBoxLayout()
        self.btn_add_dialog = QPushButton("新增对话")
        self.btn_del_dialog = QPushButton("删除选中")
        self.btn_add_option = QPushButton("新增选项")
        self.btn_del_option = QPushButton("删除选项")

        self.btn_add_dialog.clicked.connect(self.add_dialog_item)
        self.btn_del_dialog.clicked.connect(self.delete_selected_item)
        self.btn_add_option.clicked.connect(self.add_option_item)
        self.btn_del_option.clicked.connect(self.delete_selected_item)

        btn_layout.addWidget(self.btn_add_dialog)
        btn_layout.addWidget(self.btn_del_dialog)
        btn_layout.addWidget(self.btn_add_option)
        btn_layout.addWidget(self.btn_del_option)
        left_layout.addLayout(btn_layout)

        # 文件操作按钮
        file_btn_layout = QHBoxLayout()
        self.btn_new = QPushButton("新建剧本")
        self.btn_load = QPushButton("加载JSON")
        self.btn_save = QPushButton("保存JSON")
        self.btn_rebuild_index = QPushButton("刷新索引") # 手动触发构建索引

        self.btn_new.clicked.connect(self.new_file)
        self.btn_load.clicked.connect(self.load_json_file)
        self.btn_save.clicked.connect(self.save_json_file)
        self.btn_rebuild_index.clicked.connect(self.call_rebuild_index)

        file_btn_layout.addWidget(self.btn_new)
        file_btn_layout.addWidget(self.btn_load)
        file_btn_layout.addWidget(self.btn_save)
        file_btn_layout.addWidget(self.btn_rebuild_index)
        left_layout.addLayout(file_btn_layout)

        # ========== 右侧编辑表单 ==========
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        right_container = QWidget()
        right_layout = QFormLayout(right_container)
        scroll.setWidget(right_container)

        # 顶层ID
        self.edit_id = QLineEdit()
        right_layout.addRow("顶层ID", self.edit_id)
        btn_apply_id = QPushButton("应用ID修改")
        btn_apply_id.clicked.connect(self.apply_id_change)
        right_layout.addRow("", btn_apply_id)

        group_dialog = QGroupBox("对话条目")
        dialog_form = QFormLayout(group_dialog)
        self.edit_speaker = QLineEdit()
        self.edit_text = QTextEdit()
        self.edit_voice = QLineEdit()
        self.edit_script = QLineEdit()
        dialog_form.addRow("speaker", self.edit_speaker)
        dialog_form.addRow("text", self.edit_text)
        dialog_form.addRow("voice", self.edit_voice)
        dialog_form.addRow("script", self.edit_script)
        btn_apply_dialog = QPushButton("应用对话修改")
        btn_apply_dialog.clicked.connect(self.apply_dialog_change)
        dialog_form.addRow("", btn_apply_dialog)
        right_layout.addRow(group_dialog)

        group_option = QGroupBox("选项(选中选项后编辑)")
        option_form = QFormLayout(group_option)
        self.edit_opt_text = QLineEdit()
        self.edit_opt_next = QLineEdit()
        self.edit_opt_script = QLineEdit()
        self.edit_opt_condition = QLineEdit()
        option_form.addRow("text", self.edit_opt_text)
        option_form.addRow("next_dialog", self.edit_opt_next)
        option_form.addRow("script", self.edit_opt_script)
        option_form.addRow("condition", self.edit_opt_condition)
        btn_apply_opt = QPushButton("应用选项修改")
        btn_apply_opt.clicked.connect(self.apply_option_change)
        option_form.addRow("", btn_apply_opt)
        right_layout.addRow(group_option)

        main_layout.addWidget(left_widget, stretch=1)
        main_layout.addWidget(scroll, stretch=2)

    def call_rebuild_index(self):
        """手动按钮调用构建索引"""
        if self.main_win and hasattr(self.main_win, "build_id_file"):
            self.main_win.build_id_file()
            QMessageBox.information(self, "完成", "已调用构建剧本索引(config/dialog_index.json)")
        else:
            QMessageBox.warning(self, "错误", "main_win未设置，无法调用build_id_file")

    def normalize_data(self, data: dict) -> dict:
        data.setdefault("id", "")
        data.setdefault("dialogs", [])
        for dlg in data["dialogs"]:
            dlg.setdefault("speaker", "")
            dlg.setdefault("text", "")
            dlg.setdefault("voice", "None")
            dlg.setdefault("script", "None")
            dlg.setdefault("options", [])
            for opt in dlg["options"]:
                opt.setdefault("text", "")
                opt.setdefault("next_dialog", "")
                opt.setdefault("script", "None")
                opt.setdefault("condition", None)
        return data

    def refresh_tree(self):
        self.tree.clear()
        root = QTreeWidgetItem(self.tree, [f"ID: {self.current_data['id']}"])
        for idx, dlg in enumerate(self.current_data["dialogs"]):
            preview_text = dlg.get('text', '').replace('\n',' ')[:12]
            dlg_item = QTreeWidgetItem(root, [f"对话{idx}: {dlg.get('speaker','')}｜{preview_text}..."])
            dlg_item.setData(0, Qt.UserRole, ("dialog", idx))
            options = dlg.get("options", [])
            for opt_idx, opt in enumerate(options):
                cond_preview = f"[cond:{opt['condition']}]" if opt.get("condition") else ""
                opt_item = QTreeWidgetItem(dlg_item, [f"选项{opt_idx}: {opt.get('text','')} {cond_preview}"])
                opt_item.setData(0, Qt.UserRole, ("option", idx, opt_idx))
        root.setExpanded(True)

    def clear_all_form(self):
        self.edit_id.clear()
        self.edit_speaker.clear()
        self.edit_text.clear()
        self.edit_voice.clear()
        self.edit_script.clear()
        self.edit_opt_text.clear()
        self.edit_opt_next.clear()
        self.edit_opt_script.clear()
        self.edit_opt_condition.clear()

    def on_tree_select(self):
        items = self.tree.selectedItems()
        if not items:
            self.selected_tree_item = None
            self.selected_dialog_index = None
            self.selected_option_index = None
            self.clear_all_form()
            return
        item = items[0]
        self.selected_tree_item = item
        data = item.data(0, Qt.UserRole)
        if data is None:
            return
        kind = data[0]
        if kind == "dialog":
            _, dlg_idx = data
            self.selected_dialog_index = dlg_idx
            self.selected_option_index = None
            self.load_dialog_to_form(dlg_idx)
        elif kind == "option":
            _, dlg_idx, opt_idx = data
            self.selected_dialog_index = dlg_idx
            self.selected_option_index = opt_idx
            self.load_option_to_form(dlg_idx, opt_idx)

    def load_dialog_to_form(self, dlg_idx):
        dlg = self.current_data["dialogs"][dlg_idx]
        self.edit_speaker.setText(dlg.get("speaker", ""))
        self.edit_text.setPlainText(dlg.get("text", ""))
        self.edit_voice.setText(dlg.get("voice", ""))
        self.edit_script.setText(dlg.get("script", ""))

    def load_option_to_form(self, dlg_idx, opt_idx):
        opt = self.current_data["dialogs"][dlg_idx]["options"][opt_idx]
        self.edit_opt_text.setText(opt.get("text", ""))
        self.edit_opt_next.setText(opt.get("next_dialog", ""))
        self.edit_opt_script.setText(opt.get("script", ""))
        cond_val = opt.get("condition")
        self.edit_opt_condition.setText(cond_val if cond_val is not None else "")

    # ====== 手动提交函数 ======
    def apply_id_change(self):
        self.current_data["id"] = self.edit_id.text()
        self.is_dirty = True
        self.refresh_tree()

    def apply_dialog_change(self):
        if self.selected_dialog_index is None or self.selected_option_index is not None:
            QMessageBox.warning(self, "提示", "请选中一条对话条目")
            return
        dlg = self.current_data["dialogs"][self.selected_dialog_index]
        dlg["speaker"] = self.edit_speaker.text()
        dlg["text"] = self.edit_text.toPlainText()
        dlg["voice"] = self.edit_voice.text()
        dlg["script"] = self.edit_script.text()
        self.is_dirty = True
        self.refresh_tree()

    def apply_option_change(self):
        if self.selected_dialog_index is None or self.selected_option_index is None:
            QMessageBox.warning(self, "提示", "请选中一个选项")
            return
        opt = self.current_data["dialogs"][self.selected_dialog_index]["options"][self.selected_option_index]
        opt["text"] = self.edit_opt_text.text()
        opt["next_dialog"] = self.edit_opt_next.text()
        opt["script"] = self.edit_opt_script.text()
        cond_text = self.edit_opt_condition.text().strip()
        opt["condition"] = cond_text if cond_text else None
        self.is_dirty = True
        self.refresh_tree()

    # ---------------- 添加删除条目 ----------------
    def add_dialog_item(self):
        new_dialog = {
            "speaker": "",
            "text": "",
            "voice": "None",
            "script": "None",
            "options": []
        }
        self.current_data["dialogs"].append(new_dialog)
        self.is_dirty = True
        self.refresh_tree()

    def add_option_item(self):
        if self.selected_dialog_index is None:
            QMessageBox.warning(self, "提示", "请先选中一条对话")
            return
        dlg = self.current_data["dialogs"][self.selected_dialog_index]
        dlg.setdefault("options", [])
        new_opt = {
            "text": "",
            "next_dialog": "",
            "script": "None",
            "condition": None
        }
        dlg["options"].append(new_opt)
        self.is_dirty = True
        self.refresh_tree()

    def delete_selected_item(self):
        if not self.selected_tree_item:
            return
        data = self.selected_tree_item.data(0, Qt.UserRole)
        if data is None:
            return
        kind = data[0]
        if kind == "dialog":
            _, idx = data
            del self.current_data["dialogs"][idx]
        elif kind == "option":
            _, d_idx, o_idx = data
            del self.current_data["dialogs"][d_idx]["options"][o_idx]
        self.is_dirty = True
        self.refresh_tree()
        self.selected_tree_item = None
        self.selected_dialog_index = None
        self.selected_option_index = None
        self.clear_all_form()

    # ---------------- 自动保存：直接写入源文件，仅已打开文件生效，不清除脏标记 ----------------
    def _do_autosave(self):
        """定时器回调：自动保存到源文件，新建未保存文件跳过"""
        if not self.is_edit_project or not self.editing_file_path:
            return
        try:
            with open(self.editing_file_path, "w", encoding="utf-8") as f:
                json.dump(self.current_data, f, ensure_ascii=False, indent=4)
        except Exception:
            # 自动保存出错静默，不弹窗打扰编辑
            pass

    # ---------------- 文件读写 ----------------
    def _check_dirty_before_action(self) -> bool:
        """返回True代表可以继续操作；False代表用户取消"""
        if not self.is_dirty:
            return True
        ret = QMessageBox.question(
            self, "未保存修改",
            "当前存在未保存的修改，是否保存？",
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
        )
        if ret == QMessageBox.Save:
            self.save_json_file()
            return True
        elif ret == QMessageBox.Discard:
            return True
        else:
            return False

    def new_file(self):
        if not self._check_dirty_before_action():
            return
        self.current_data = {
            "id": "",
            "dialogs": []
        }
        self.is_dirty = False
        self.is_edit_project = False
        self.editing_file_path = None
        self.clear_all_form()
        self.refresh_tree()

    def load_json_file(self):
        if not self._check_dirty_before_action():
            return
        path, _ = QFileDialog.getOpenFileName(self, "打开对话JSON", "", "JSON File (*.json)")
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            self.current_data = self.normalize_data(raw)
            self.is_edit_project = True
            self.editing_file_path = path
            self.is_dirty = False
        except Exception as e:
            QMessageBox.critical(self, "读取失败", str(e))
            return
        self.edit_id.setText(self.current_data.get("id", ""))
        self.refresh_tree()

    def save_json_file(self):
        saved_ok = False
        if self.is_edit_project:
            try:
                with open(self.editing_file_path, "w", encoding="utf-8") as f:
                    json.dump(self.current_data, f, ensure_ascii=False, indent=4)
                self.is_dirty = False
                QMessageBox.information(self, "成功", "保存完成！")
                saved_ok = True
            except Exception as e:
                QMessageBox.critical(self, "保存失败", str(e))
        else:
            path, _ = QFileDialog.getSaveFileName(self, "保存对话JSON", "", "JSON File (*.json)")
            if not path:
                return
            try:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(self.current_data, f, ensure_ascii=False, indent=4)
                self.is_dirty = False
                self.is_edit_project = True
                self.editing_file_path = path
                QMessageBox.information(self, "成功", "保存完成！")
                saved_ok = True
            except Exception as e:
                QMessageBox.critical(self, "保存失败", str(e))
        # 保存成功，调用主窗口构建索引
        if saved_ok and self.main_win and hasattr(self.main_win, "build_id_file"):
            self.main_win.build_id_file()

    # 对外接口
    def get_data(self):
        return self.current_data.copy()

    def set_data(self, data: dict):
        self.current_data = self.normalize_data(data)
        self.edit_id.setText(self.current_data.get("id", ""))
        self.refresh_tree()
        self.is_dirty = False


# ============ 测试窗口 ============
if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication, QMainWindow

    class TestMainWin(QMainWindow):
        """模拟你的主窗口，实现 build_id_file，实际项目删掉这个类"""
        def __init__(self):
            super().__init__()
        def build_id_file(self):
            os.makedirs("config", exist_ok=True)
            print("【模拟】调用 build_id_file()，输出 config/dialog_index.json")

    app = QApplication(sys.argv)
    win = TestMainWin()
    win.setWindowTitle("对话JSON编辑器【自动保存源文件｜支持option condition】")
    win.resize(1100,700)

    editor = DialogJsonEditor(main_win=win)
    win.setCentralWidget(editor)

    # 直接使用你提供的测试剧本样例
    sample = {
        "id": "test_dialog_editor_work",
        "dialogs": [
            {
                "speaker": "测试",
                "text": "这是一条测试文字，用来测试剧本编辑器是否可以在嵌入编辑器的情况下正常导出剧本",
                "voice": "None",
                "script": "cmd:switch bgm file:bgms/LevelOver1.wav 0.01",
                "options": [
                    {
                        "text": "选项A",
                        "next_dialog": "id:example1",
                        "script": "cmd:switch bgm file:bgms/LevelOver2.wav 0.05",
                        "condition": "affection: Mario == 0"
                    },
                    {
                        "text": "选项B",
                        "next_dialog": "file:dialogs/Yukimura_Chieri/001.json",
                        "script": "cmd:add flag yes \n affection Mario add 5"
                    },
                    {
                        "text": "选项C",
                        "next_dialog": "file:dialogs/Yukimura_Chieri/001.json",
                        "script": "None"
                    },
                    {
                        "text": "选项D",
                        "next_dialog": "file:dialogs/Yukimura_Chieri/001.json",
                        "script": "None"
                    }
                ]
            }
        ]
    }
    editor.set_data(sample)

    win.show()
    sys.exit(app.exec_())