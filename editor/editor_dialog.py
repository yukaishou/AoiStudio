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
    - 支持option condition、script脚本字段
    """
    def __init__(self, parent=None, file_path=None, main_win=None):
        super().__init__(parent)
        self.main_win = main_win   # 外部主窗口，提供 build_id_file()

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

        self._edit_widgets = []  # 保存所有编辑控件，用于blockSignals

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
        # 使用 currentItemChanged，可以拿到前一个节点，优化同dialog跳转
        self.tree.currentItemChanged.connect(self.on_tree_current_changed)
        left_layout.addWidget(self.tree)

        btn_layout = QHBoxLayout()
        self.btn_add_dialog = QPushButton("新增对话")
        self.btn_del_dialog = QPushButton("删除选中")
        self.btn_add_option = QPushButton("新增选项")
        self.btn_del_option = QPushButton("删除选项")
        self.btn_move_up = QPushButton("上移")
        self.btn_move_down = QPushButton("下移")

        self.btn_save = QPushButton("保存")
        self.btn_save_as = QPushButton("另存为")
        self.btn_rebuild_index = QPushButton("重建索引")

        self.btn_add_dialog.clicked.connect(self.add_dialog_item)
        self.btn_del_dialog.clicked.connect(self.delete_selected_item)
        self.btn_add_option.clicked.connect(self.add_option_item)
        self.btn_del_option.clicked.connect(self.delete_selected_item)
        self.btn_move_up.clicked.connect(self.move_selected_up)
        self.btn_move_down.clicked.connect(self.move_selected_down)

        self.btn_save.clicked.connect(self.save_json_file)
        self.btn_save_as.clicked.connect(self._on_save_as)
        self.btn_rebuild_index.clicked.connect(self.call_rebuild_index)

        btn_layout.addWidget(self.btn_add_dialog)
        btn_layout.addWidget(self.btn_del_dialog)
        btn_layout.addWidget(self.btn_add_option)
        btn_layout.addWidget(self.btn_del_option)
        btn_layout.addWidget(self.btn_move_up)
        btn_layout.addWidget(self.btn_move_down)
        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_save_as)
        btn_layout.addWidget(self.btn_rebuild_index)

        left_layout.addLayout(btn_layout)

        # ========== 右侧编辑表单 ==========
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        right_container = QWidget()
        right_layout = QFormLayout(right_container)

        self.edit_id = QLineEdit()
        self.edit_speaker = QLineEdit()
        self.edit_text = QTextEdit()
        self.edit_voice = QLineEdit()
        self.edit_dialog_script = QTextEdit()

        self.edit_opt_text = QLineEdit()
        self.edit_opt_next = QLineEdit()
        self.edit_opt_cond = QLineEdit()
        self.edit_opt_script = QTextEdit()

        right_layout.addRow("剧本ID", self.edit_id)

        group_dlg = QGroupBox("对话条目")
        form_dlg = QFormLayout(group_dlg)
        form_dlg.addRow("说话人", self.edit_speaker)
        form_dlg.addRow("文本", self.edit_text)
        form_dlg.addRow("语音", self.edit_voice)
        form_dlg.addRow("脚本", self.edit_dialog_script)
        btn_apply_dlg = QPushButton("应用对话修改")
        btn_apply_dlg.clicked.connect(self.apply_dialog_change)
        form_dlg.addRow("", btn_apply_dlg)
        right_layout.addRow(group_dlg)

        group_opt = QGroupBox("选项")
        form_opt = QFormLayout(group_opt)
        form_opt.addRow("选项文本", self.edit_opt_text)
        form_opt.addRow("跳转ID(next_dialog)", self.edit_opt_next)
        form_opt.addRow("条件condition", self.edit_opt_cond)
        form_opt.addRow("选项脚本", self.edit_opt_script)
        btn_apply_opt = QPushButton("应用选项修改")
        btn_apply_opt.clicked.connect(self.apply_option_change)
        form_opt.addRow("", btn_apply_opt)
        right_layout.addRow(group_opt)

        scroll.setWidget(right_container)
        main_layout.addWidget(left_widget, stretch=1)
        main_layout.addWidget(scroll, stretch=2)

        # 收集所有编辑控件，用于blockSignals
        self._edit_widgets = [
            self.edit_speaker,
            self.edit_text,
            self.edit_voice,
            self.edit_dialog_script,
            self.edit_opt_text,
            self.edit_opt_next,
            self.edit_opt_cond,
            self.edit_opt_script
        ]
        # 仅用户手动输入才标记表单修改；代码setText不会触发
        for w in self._edit_widgets:
            w.textChanged.connect(self._on_user_form_modify)

        self._update_button_state()

    def _block_all_edit_signals(self, block: bool):
        for w in self._edit_widgets:
            w.blockSignals(block)

    def _on_user_form_modify(self):
        """用户手动键盘输入才标记表单修改"""
        self._form_modified = True

    def on_tree_current_changed(self, current_item, prev_item):
        """处理树节点切换，优化同dialog：dialog -> 子option跳过确认弹窗"""
        skip_confirm = False
        if prev_item is not None and current_item is not None:
            prev_data = prev_item.data(0, Qt.UserRole)
            curr_data = current_item.data(0, Qt.UserRole)
            if prev_data and curr_data:
                # 旧节点是dialog，新节点是它的子option，同一个dialog索引
                if prev_data[0] == "dialog" and curr_data[0] == "option":
                    if prev_data[1] == curr_data[1]:
                        skip_confirm = True

        if skip_confirm:
            self._form_modified = False
            self.on_tree_select()
            return

        self.on_tree_select()

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
            self._block_all_edit_signals(True)
            self.edit_speaker.setText(d.get("speaker", ""))
            self.edit_text.setPlainText(d.get("text", ""))
            self.edit_voice.setText(d.get("voice", ""))
            self.edit_dialog_script.setPlainText(d.get("script", ""))
            self._block_all_edit_signals(False)
        elif kind == "option":
            _, dlg_idx, opt_idx = ud
            self.selected_dialog_index = dlg_idx
            self.selected_option_index = opt_idx
            opt = self.current_data["dialogs"][dlg_idx]["options"][opt_idx]
            self._block_all_edit_signals(True)
            self.edit_opt_text.setText(opt.get("text", ""))
            self.edit_opt_next.setText(opt.get("next_dialog", ""))
            self.edit_opt_cond.setText(opt.get("condition", "") or "")
            self.edit_opt_script.setPlainText(opt.get("script", ""))
            self._block_all_edit_signals(False)

        self._form_modified = False
        self._update_button_state()

    def clear_all_form(self):
        self._block_all_edit_signals(True)
        self.edit_id.clear()
        self.edit_speaker.clear()
        self.edit_text.clear()
        self.edit_voice.clear()
        self.edit_dialog_script.clear()
        self.edit_opt_text.clear()
        self.edit_opt_next.clear()
        self.edit_opt_cond.clear()
        self.edit_opt_script.clear()
        self._block_all_edit_signals(False)
        self._form_modified = False

    def _apply_current_selection(self):
        if self.selected_option_index is not None:
            self.apply_option_change()
        elif self.selected_dialog_index is not None:
            self.apply_dialog_change()

    def apply_dialog_change(self):
        if self.selected_dialog_index is None:
            return
        dlg = self.current_data["dialogs"][self.selected_dialog_index]
        dlg["speaker"] = self.edit_speaker.text()
        dlg["text"] = self.edit_text.toPlainText()
        dlg["voice"] = self.edit_voice.text()
        dlg["script"] = self.edit_dialog_script.toPlainText()
        self.is_dirty = True
        self._form_modified = False
        self.refresh_tree()

    def apply_option_change(self):
        if self.selected_dialog_index is None or self.selected_option_index is None:
            return
        opt = self.current_data["dialogs"][self.selected_dialog_index]["options"][self.selected_option_index]
        opt["text"] = self.edit_opt_text.text()
        opt["next_dialog"] = self.edit_opt_next.text()
        opt["condition"] = self.edit_opt_cond.text() or None
        opt["script"] = self.edit_opt_script.toPlainText()
        self.is_dirty = True
        self._form_modified = False
        self.refresh_tree()

    def apply_id_change(self):
        self.current_data["id"] = self.edit_id.text()
        self.is_dirty = True
        self.refresh_tree()

    def add_dialog_item(self):
        self.current_data["dialogs"].append({
            "speaker": "",
            "text": "",
            "voice": "",
            "script": "",
            "options": []
        })
        self.is_dirty = True
        self.refresh_tree()

    def add_option_item(self):
        if self.selected_dialog_index is None or self.selected_option_index is not None:
            return
        dlg = self.current_data["dialogs"][self.selected_dialog_index]
        dlg.setdefault("options", [])
        dlg["options"].append({
            "text": "",
            "next_dialog": "",
            "condition": None,
            "script": ""
        })
        self.is_dirty = True
        self.refresh_tree()

    def delete_selected_item(self):
        if self.selected_option_index is not None:
            dlg = self.current_data["dialogs"][self.selected_dialog_index]
            del dlg["options"][self.selected_option_index]
        elif self.selected_dialog_index is not None:
            del self.current_data["dialogs"][self.selected_dialog_index]
        else:
            return
        self.is_dirty = True
        self.clear_all_form()
        self.refresh_tree()

    def move_selected_up(self):
        idx = self.selected_dialog_index
        if idx is None or idx <= 0 or self.selected_option_index is not None:
            return
        lst = self.current_data["dialogs"]
        lst[idx-1], lst[idx] = lst[idx], lst[idx-1]
        self.selected_dialog_index -= 1
        self.is_dirty = True
        self.refresh_tree()

    def move_selected_down(self):
        idx = self.selected_dialog_index
        lst = self.current_data["dialogs"]
        if idx is None or idx >= len(lst)-1 or self.selected_option_index is not None:
            return
        lst[idx+1], lst[idx] = lst[idx], lst[idx+1]
        self.selected_dialog_index += 1
        self.is_dirty = True
        self.refresh_tree()

    def refresh_tree(self):
        expand_set = set()
        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            if item.isExpanded():
                expand_set.add(i)
        self.tree.clear()
        for dlg_idx, dlg in enumerate(self.current_data["dialogs"]):
            dlg_item = QTreeWidgetItem([f"[{dlg_idx}] {dlg.get('speaker','')}:{dlg.get('text','')[:20]}"])
            dlg_item.setData(0, Qt.UserRole, ("dialog", dlg_idx))
            self.tree.addTopLevelItem(dlg_item)
            for opt_idx, opt in enumerate(dlg.get("options", [])):
                opt_item = QTreeWidgetItem([f"选项{opt_idx}:{opt.get('text','')[:20]}"])
                opt_item.setData(0, Qt.UserRole, ("option", dlg_idx, opt_idx))
                dlg_item.addChild(opt_item)
        for idx in expand_set:
            if idx < self.tree.topLevelItemCount():
                self.tree.topLevelItem(idx).setExpanded(True)
        self._update_button_state()

    def _update_button_state(self):
        sel_dlg = self.selected_dialog_index is not None
        sel_opt = self.selected_option_index is not None
        self.btn_add_option.setEnabled(sel_dlg and not sel_opt)
        self.btn_del_dialog.setEnabled(sel_dlg and not sel_opt)
        self.btn_del_option.setEnabled(sel_opt)
        self.btn_move_up.setEnabled(sel_dlg and not sel_opt and self.selected_dialog_index > 0)
        self.btn_move_down.setEnabled(sel_dlg and not sel_opt and self.selected_dialog_index < len(self.current_data["dialogs"]) - 1)

    def call_rebuild_index(self):
        if self.main_win and hasattr(self.main_win, "build_id_file"):
            self.main_win.build_id_file()
            QMessageBox.information(self, "完成", "已调用构建剧本索引 config/dialog_index.json")

    def _on_save_as(self):
        path, _ = QFileDialog.getSaveFileName(self, "另存为剧本JSON", "", "JSON Files (*.json)")
        if not path:
            return
        self.editing_file_path = path
        self.is_edit_project = True
        self.save_json_file()

    def save_json_file(self):
        target = self.editing_file_path
        if not (self.is_edit_project and target):
            target, _ = QFileDialog.getSaveFileName(self, "保存剧本JSON", "", "JSON Files (*.json)")
            if not target:
                return
            self.editing_file_path = target
            self.is_edit_project = True
        try:
            with open(target, "w", encoding="utf-8") as f:
                json.dump(self.current_data, f, ensure_ascii=False, indent=4)
            self.is_dirty = False
            self._form_modified = False
            QMessageBox.information(self, "保存成功", f"已保存：{target}")
            if self.main_win and hasattr(self.main_win, "build_id_file"):
                self.main_win.build_id_file()
        except Exception as e:
            QMessageBox.critical(self, "保存失败", str(e))

    def can_switch_out(self) -> bool:
        """外部标签切换/关闭调用，返回True允许切走"""
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
                "本剧本存在未保存修改，是否保存？",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
            )
            if ret == QMessageBox.Save:
                self.save_json_file()
            elif ret == QMessageBox.Cancel:
                return False
        return True

    def _do_autosave(self):
        pass

    def new_file(self):
        if not self.can_switch_out():
            return
        self.current_data = {"id": "", "dialogs": []}
        self.is_dirty = False
        self.is_edit_project = False
        self.editing_file_path = None
        self.clear_all_form()
        self.refresh_tree()

    def load_json_file(self):
        if not self.can_switch_out():
            return
        path, _ = QFileDialog.getOpenFileName(self, "打开对话JSON", "", "JSON Files (*.json)")
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            self.set_data(raw)
            self.is_edit_project = True
            self.editing_file_path = path
        except Exception as e:
            QMessageBox.critical(self, "读取失败", str(e))

    def set_data(self, data: dict):
        self.current_data = self.normalize_data(data)
        self._block_all_edit_signals(True)
        self.edit_id.setText(self.current_data.get("id", ""))
        self._block_all_edit_signals(False)
        self.refresh_tree()
        self.is_dirty = False
        self.clear_all_form()

    def normalize_data(self, data: dict) -> dict:
        out = {
            "id": data.get("id", ""),
            "dialogs": []
        }
        for d in data.get("dialogs", []):
            dlg = {
                "speaker": d.get("speaker", ""),
                "text": d.get("text", ""),
                "voice": d.get("voice", ""),
                "script": d.get("script", ""),
                "options": []
            }
            for o in d.get("options", []):
                dlg["options"].append({
                    "text": o.get("text", ""),
                    "next_dialog": o.get("next_dialog", ""),
                    "condition": o.get("condition"),
                    "script": o.get("script", "")
                })
            out["dialogs"].append(dlg)
        return out

    def get_data(self):
        return self.current_data.copy()