import json
import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
                             QFormLayout, QLineEdit, QTextEdit, QPushButton,
                             QGroupBox, QScrollArea, QFileDialog, QMessageBox)
from PySide6.QtCore import Qt, QTimer


class DialogJsonEditor(QWidget):
    """
    对话JSON编辑器独立组件
    - 手动Apply提交修改，脏标记防丢稿
    - 对外 can_switch_out()：标签切换/关闭前调用，返回True才允许切走
    - 30秒自动保存代码保留但默认弃用
    - 保存完成调用外部 self.main_win.build_id_file() 生成 config/dialog_index.json
    - 支持option condition条件字段
    """
    def __init__(self, parent=None, file_path=None, main_win=None):
        super().__init__(parent)
        self.main_win = main_win   # 外部主窗口，提供 build_id_file()

        # 【修复】必须在init_ui之前初始化，init_ui内部会调用_update_button_state访问它们
        self.selected_tree_item = None
        self.selected_dialog_index = None
        self.selected_option_index = None
        self.is_edit_project = False
        self.editing_file_path = None
        self.is_dirty = False
        self._form_modified = False

        self.current_data = {
            "id": "",
            "dialogs": []
        }

        self.init_ui()

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
        self.btn_move_up = QPushButton("上移")
        self.btn_move_down = QPushButton("下移")

        self.btn_add_dialog.clicked.connect(self.add_dialog_item)
        self.btn_del_dialog.clicked.connect(self.delete_selected_item)
        self.btn_add_option.clicked.connect(self.add_option_item)
        self.btn_del_option.clicked.connect(self.delete_selected_item)
        self.btn_move_up.clicked.connect(self.move_selected_up)
        self.btn_move_down.clicked.connect(self.move_selected_down)

        btn_layout.addWidget(self.btn_add_dialog)
        btn_layout.addWidget(self.btn_del_dialog)
        btn_layout.addWidget(self.btn_add_option)
        btn_layout.addWidget(self.btn_del_option)
        btn_layout.addWidget(self.btn_move_up)
        btn_layout.addWidget(self.btn_move_down)
        left_layout.addLayout(btn_layout)

        # ========== 右侧编辑表单 ==========
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        right_container = QWidget()
        right_layout = QFormLayout(right_container)

        self.edit_id = QLineEdit()
        btn_apply_id = QPushButton("应用ID修改")
        btn_apply_id.clicked.connect(self.apply_id_change)
        right_layout.addRow("剧本ID", self.edit_id)
        right_layout.addRow("", btn_apply_id)

        group_dlg = QGroupBox("对话条目")
        form_dlg = QFormLayout(group_dlg)
        self.edit_speaker = QLineEdit()
        self.edit_text = QTextEdit()
        self.edit_voice = QLineEdit()
        form_dlg.addRow("说话人", self.edit_speaker)
        form_dlg.addRow("文本", self.edit_text)
        form_dlg.addRow("语音", self.edit_voice)
        btn_apply_dlg = QPushButton("应用对话修改")
        btn_apply_dlg.clicked.connect(self.apply_dialog_change)
        form_dlg.addRow("", btn_apply_dlg)
        right_layout.addRow(group_dlg)

        group_opt = QGroupBox("选项")
        form_opt = QFormLayout(group_opt)
        self.edit_opt_text = QLineEdit()
        self.edit_opt_next = QLineEdit()
        self.edit_opt_cond = QLineEdit()
        form_opt.addRow("选项文本", self.edit_opt_text)
        form_opt.addRow("跳转ID", self.edit_opt_next)
        form_opt.addRow("条件", self.edit_opt_cond)
        btn_apply_opt = QPushButton("应用选项修改")
        btn_apply_opt.clicked.connect(self.apply_option_change)
        form_opt.addRow("", btn_apply_opt)
        right_layout.addRow(group_opt)

        scroll.setWidget(right_container)
        main_layout.addWidget(left_widget, stretch=1)
        main_layout.addWidget(scroll, stretch=2)

        self._update_button_state()

    def _save_tree_expand_state(self):
        expand = set()
        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            if item.isExpanded():
                expand.add(i)
        return expand

    def _restore_tree_expand_state(self, expand_set):
        root = self.tree.invisibleRootItem()
        for idx in expand_set:
            if idx < root.childCount():
                root.child(idx).setExpanded(True)

    def refresh_tree(self):
        expand = self._save_tree_expand_state()
        self.tree.clear()
        for dlg_idx, dlg in enumerate(self.current_data["dialogs"]):
            dlg_item = QTreeWidgetItem([f"[{dlg_idx}] {dlg.get('speaker','')}:{dlg.get('text','')[:15]}"])
            dlg_item.setData(0, Qt.UserRole, ("dialog", dlg_idx))
            self.tree.addTopLevelItem(dlg_item)
            for opt_idx, opt in enumerate(dlg.get("options", [])):
                opt_item = QTreeWidgetItem([f"选项{opt_idx}:{opt.get('text','')[:15]}"])
                opt_item.setData(0, Qt.UserRole, ("option", dlg_idx, opt_idx))
                dlg_item.addChild(opt_item)
        self._restore_tree_expand_state(expand)

    def _update_button_state(self):
        sel_dlg = self.selected_dialog_index is not None
        sel_opt = self.selected_option_index is not None
        self.btn_add_option.setEnabled(sel_dlg and not sel_opt)
        self.btn_del_dialog.setEnabled(sel_dlg and not sel_opt)
        self.btn_del_option.setEnabled(sel_opt)
        self.btn_move_up.setEnabled(sel_dlg and not sel_opt)
        self.btn_move_down.setEnabled(sel_dlg and not sel_opt)

    def clear_all_form(self):
        self.edit_id.clear()
        self.edit_speaker.clear()
        self.edit_text.clear()
        self.edit_voice.clear()
        self.edit_opt_text.clear()
        self.edit_opt_next.clear()
        self.edit_opt_cond.clear()
        self._form_modified = False

    def on_tree_select(self):
        if self._form_modified:
            ret = QMessageBox.question(
                self, "表单尚未应用",
                "右侧表单存在未应用的修改。是否应用？\n取消则维持原有选中项。",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
            )
            if ret == QMessageBox.Save:
                self._apply_current_selection()
            elif ret == QMessageBox.Cancel:
                self.tree.blockSignals(True)
                if self.selected_tree_item:
                    self.tree.setCurrentItem(self.selected_tree_item)
                self.tree.blockSignals(False)
                return
            elif ret == QMessageBox.Discard:
                self._form_modified = False

        items = self.tree.selectedItems()
        self.clear_all_form()
        self.selected_tree_item = None
        self.selected_dialog_index = None
        self.selected_option_index = None

        if not items:
            self._update_button_state()
            return
        item = items[0]
        self.selected_tree_item = item
        ud = item.data(0, Qt.UserRole)
        if ud is None:
            self._update_button_state()
            return
        kind = ud[0]
        if kind == "dialog":
            _, dlg_idx = ud
            self.selected_dialog_index = dlg_idx
            d = self.current_data["dialogs"][dlg_idx]
            self.edit_speaker.setText(d.get("speaker", ""))
            self.edit_text.setPlainText(d.get("text", ""))
            self.edit_voice.setText(d.get("voice", ""))
        elif kind == "option":
            _, dlg_idx, opt_idx = ud
            self.selected_dialog_index = dlg_idx
            self.selected_option_index = opt_idx
            o = self.current_data["dialogs"][dlg_idx]["options"][opt_idx]
            self.edit_opt_text.setText(o.get("text", ""))
            self.edit_opt_next.setText(o.get("next", ""))
            self.edit_opt_cond.setText(o.get("condition") or "")
        self._update_button_state()

    def _apply_current_selection(self):
        if self.selected_option_index is not None:
            self.apply_option_change()
        elif self.selected_dialog_index is not None:
            self.apply_dialog_change()

    def apply_id_change(self):
        self.current_data["id"] = self.edit_id.text()
        self.is_dirty = True
        self.refresh_tree()

    def apply_dialog_change(self):
        if self.selected_dialog_index is None:
            return
        dlg = self.current_data["dialogs"][self.selected_dialog_index]
        dlg["speaker"] = self.edit_speaker.text()
        dlg["text"] = self.edit_text.toPlainText()
        dlg["voice"] = self.edit_voice.text()
        self.is_dirty = True
        self._form_modified = False
        self.refresh_tree()

    def apply_option_change(self):
        if self.selected_dialog_index is None or self.selected_option_index is None:
            return
        opt = self.current_data["dialogs"][self.selected_dialog_index]["options"][self.selected_option_index]
        opt["text"] = self.edit_opt_text.text()
        opt["next"] = self.edit_opt_next.text()
        opt["condition"] = self.edit_opt_cond.text() or None
        self.is_dirty = True
        self._form_modified = False
        self.refresh_tree()

    def add_dialog_item(self):
        self.current_data["dialogs"].append({"speaker":"","text":"","voice":"","options":[]})
        self.is_dirty = True
        self.refresh_tree()

    def add_option_item(self):
        if self.selected_dialog_index is None:
            return
        dlg = self.current_data["dialogs"][self.selected_dialog_index]
        dlg.setdefault("options", []).append({"text":"","next":"","condition":None})
        self.is_dirty = True
        self.refresh_tree()

    def delete_selected_item(self):
        reply = QMessageBox.question(self, "确认删除", "确定要删除该条目吗？", QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        if self.selected_option_index is not None:
            dlg = self.current_data["dialogs"][self.selected_dialog_index]
            del dlg["options"][self.selected_option_index]
        elif self.selected_dialog_index is not None:
            del self.current_data["dialogs"][self.selected_dialog_index]
        self.is_dirty = True
        self.selected_tree_item = None
        self.selected_dialog_index = None
        self.selected_option_index = None
        self.clear_all_form()
        self.refresh_tree()
        self._update_button_state()

    def move_selected_up(self):
        idx = self.selected_dialog_index
        if idx is None or idx <= 0:
            return
        lst = self.current_data["dialogs"]
        lst[idx-1], lst[idx] = lst[idx], lst[idx-1]
        self.selected_dialog_index -= 1
        self.is_dirty = True
        self.refresh_tree()

    def move_selected_down(self):
        idx = self.selected_dialog_index
        lst = self.current_data["dialogs"]
        if idx is None or idx >= len(lst)-1:
            return
        lst[idx+1], lst[idx] = lst[idx], lst[idx+1]
        self.selected_dialog_index += 1
        self.is_dirty = True
        self.refresh_tree()

    def call_rebuild_index(self):
        if self.main_win and hasattr(self.main_win, "build_id_file"):
            self.main_win.build_id_file()
            QMessageBox.information(self, "完成", "已调用构建剧本索引 config/dialog_index.json")

    def can_switch_out(self) -> bool:
        if self._form_modified:
            r = QMessageBox.question(
                self, "表单尚未应用",
                "当前表单存在未应用的修改，是否应用？",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
            )
            if r == QMessageBox.Save:
                self._apply_current_selection()
            elif r == QMessageBox.Cancel:
                return False
            elif r == QMessageBox.Discard:
                self._form_modified = False
        if self.is_dirty:
            ret = QMessageBox.question(
                self, "标签有未保存改动",
                "本标签存在未保存修改，是否保存？",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
            )
            if ret == QMessageBox.Save:
                self.save_json_file()
            elif ret == QMessageBox.Cancel:
                return False
        return True

    def _do_autosave(self):
        return

    def _check_dirty_before_action(self) -> bool:
        return self.can_switch_out()

    def new_file(self):
        if not self._check_dirty_before_action():
            return
        self.current_data = {"id":"", "dialogs":[]}
        self.is_dirty = False
        self.is_edit_project = False
        self.editing_file_path = None
        self.clear_all_form()
        self.refresh_tree()

    def load_json_file(self):
        if not self._check_dirty_before_action():
            return
        path, _ = QFileDialog.getOpenFileName(self, "打开对话JSON", "", "JSON Files (*.json)")
        if not path:
            return
        try:
            with open(path, "r", encoding="utf‑8") as f:
                raw = json.load(f)
            self.set_data(raw)
            self.is_edit_project = True
            self.editing_file_path = path
        except Exception as e:
            QMessageBox.critical(self, "读取失败", str(e))

    def save_json_file(self):
        saved_ok = False
        if self.is_edit_project and self.editing_file_path:
            target = self.editing_file_path
        else:
            target, _ = QFileDialog.getSaveFileName(self, "保存剧本JSON", "", "JSON Files (*.json)")
            if not target:
                return
            self.editing_file_path = target
            self.is_edit_project = True
        try:
            with open(target, "w", encoding="utf‑8") as f:
                json.dump(self.current_data, f, ensure_ascii=False, indent=4)
            self.is_dirty = False
            self._form_modified = False
            saved_ok = True
            QMessageBox.information(self, "保存成功", target)
        except Exception as e:
            QMessageBox.critical(self, "保存失败", str(e))
        if saved_ok and self.main_win and hasattr(self.main_win, "build_id_file"):
            self.main_win.build_id_file()

    def normalize_data(self, data:dict) -> dict:
        data.setdefault("id", "")
        data.setdefault("dialogs", [])
        for d in data["dialogs"]:
            d.setdefault("speaker", "")
            d.setdefault("text", "")
            d.setdefault("voice", "")
            d.setdefault("options", [])
            for o in d["options"]:
                o.setdefault("text", "")
                o.setdefault("next", "")
                o.setdefault("condition", None)
        return data

    def get_data(self):
        return self.current_data.copy()

    def set_data(self, data:dict):
        self.current_data = self.normalize_data(data)
        self.edit_id.setText(self.current_data.get("id",""))
        self.refresh_tree()
        self.is_dirty = False
        self.clear_all_form()
        self._update_button_state()