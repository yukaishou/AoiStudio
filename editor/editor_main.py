import os
import shutil
import sys
import threading
import time
import traceback

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QTreeView, QListView,
    QSplitter, QMenu, QInputDialog, QFileDialog,
    QMessageBox, QWidget, QVBoxLayout, QHBoxLayout, QFileSystemModel, QLabel,
    QTabWidget, QTextEdit, QScrollArea, QPushButton, QSlider
)
from PySide6.QtCore import Qt, QMimeData, QPoint, QDir, QFileInfo, QUrl
from PySide6.QtGui import QIcon, QPixmap, QAction
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

from common import AoiStudioCrasher
from common import check_game_file_full
import json

from editor import editor_dialog
from editor import editor_script
from editor import editor_project_settings
from editor import tool_id_builder
from editor import editor_character
from editor import editor_main_menu_settings
from editor import editor_doc_view
from editor import editor_python_edit
import subprocess

import zipfile


# -------------------------- 主题QSS样式 --------------------------
LIGHT_THEME_QSS = """
QMainWindow, QWidget{
    background-color: #f0f0f0;
    color:#191919;
}
QMenuBar{
    background-color:#e8e8e8;
}
QMenuBar::item{
    padding:4px 12px;
}
QMenuBar::item:selected{
    background-color:#d0d0d0;
}
QMenu{
    background-color:#ffffff;
    border:1px solid #aaaaaa;
}
QMenu::item:selected{
    background-color:#b8d4f0;
}
QTabWidget::pane{
    border:1px solid #aaaaaa;
}
QTabBar::tab{
    background:#e0e0e0;
    padding:6px 12px;
    border:1px solid #aaaaaa;
    border-bottom:none;
}
QTabBar::tab:selected{
    background:#f0f0f0;
}
QTreeView,QListView,QTextEdit{
    background:#ffffff;
    border:1px solid #aaaaaa;
}
QTreeView::viewport {
    background:#ffffff;
}
QListView::viewport {
    background:#ffffff;
}
QTreeView::item, QListView::item{
    background:#ffffff;
}
QTreeView::item:selected, QListView::item:selected{
    background:#b8d4f0;
    color:#000000;
}
QPushButton{
    padding:5px 12px;
    border:1px solid #999999;
    border-radius:2px;
    background:#f7f7f7;
}
QPushButton:hover{
    background:#e4e4e4;
}
QSlider::groove:horizontal{
    height:6px;
    background:#cccccc;
    border-radius:3px;
}
QSlider::handle:horizontal{
    width:14px;
    margin:-4px 0;
    background:#777777;
    border-radius:7px;
}
#PathBarLabel{
    background-color:#e8e8e8;
    border-bottom:1px solid #aaaaaa;
}
"""

DARK_THEME_QSS = """
QMainWindow, QWidget{
    background-color: #2c2c2c;
    color:#dddddd;
}
QMenuBar{
    background-color:#383838;
}
QMenuBar::item{
    padding:4px 12px;
}
QMenuBar::item:selected{
    background-color:#4e4e4e;
}
QMenu{
    background-color:#383838;
    border:1px solid #555555;
}
QMenu::item:selected{
    background-color:#2d5b8c;
}
QTabWidget::pane{
    border:1px solid #444444;
}
QTabBar::tab{
    background:#383838;
    padding:6px 12px;
    border:1px solid #444444;
    border-bottom:none;
}
QTabBar::tab:selected{
    background:#2c2c2c;
}
QTreeView,QListView,QTextEdit{
    background:#343434;
    border:1px solid #444444;
    color:#dddddd;
}
QTreeView::viewport {
    background:#343434;
}
QListView::viewport {
    background:#343434;
}
QTreeView::item, QListView::item{
    background:#343434;
    color:#dddddd;
}
QTreeView::item:selected, QListView::item:selected{
    background:#2d5b8c;
}
QPushButton{
    padding:5px 12px;
    border:1px solid #555555;
    border-radius:2px;
    background:#444444;
    color:#dddddd;
}
QPushButton:hover{
    background:#525252;
}
QSlider::groove:horizontal{
    height:6px;
    background:#505050;
    border-radius:3px;
}
QSlider::handle:horizontal{
    width:14px;
    margin:-4px 0;
    background:#aaaaaa;
    border-radius:7px;
}
QScrollArea{
    border:none;
}
#PathBarLabel{
    background-color:#3c3c3c;
    border-bottom:1px solid #444444;
}
"""


def ms_to_time(ms):
    sec = ms // 1000
    m = sec // 60
    s = sec % 60
    return f"{m:02d}:{s:02d}"


class PreviewPage(QWidget):
    def __init__(self, file_path, parent=None):
        super().__init__(parent)

        if not isinstance(file_path, (str, os.PathLike)) or not file_path:
            raise ValueError(f"PreviewPage 收到非法路径: {repr(file_path)}")

        self.file_path = file_path
        self.player = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setAlignment(Qt.AlignCenter)

        ext = os.path.splitext(file_path)[1].lower()
        img_exts = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}
        text_exts = {".txt", ".json", ".md", ".ini", ".csv", ".py", ".xml", ".html", ".css", ".cfg"}
        audio_exts = {".mp3", ".wav", ".flac", ".ogg", ".m4a", ".wma"}

        if ext in img_exts:
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            img_label = QLabel()
            img_label.setAlignment(Qt.AlignCenter)
            pix = QPixmap(file_path)
            if pix.isNull():
                img_label.setText("图片加载失败")
            else:
                img_label.setPixmap(pix)
            scroll.setWidget(img_label)
            layout.addWidget(scroll)

        elif ext in text_exts:
            text_edit = QTextEdit()
            text_edit.setReadOnly(True)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    text_edit.setText(f.read())
            except Exception:
                text_edit.setText("无法读取文件（编码错误）")
            layout.addWidget(text_edit)

        elif ext in audio_exts:
            self.player = QMediaPlayer()
            self.player.setSource(QUrl.fromLocalFile(file_path))
            self.audio_output = QAudioOutput()
            self.player.setAudioOutput(self.audio_output)
            self.audio_output.setVolume(0.8)

            audio_label = QLabel(f"🎵 {os.path.basename(file_path)}")
            audio_label.setAlignment(Qt.AlignCenter)
            font = audio_label.font()
            font.setPointSize(11)
            audio_label.setFont(font)

            self.slider = QSlider(Qt.Horizontal)
            self.slider.setRange(0, 0)
            self.time_label = QLabel("00:00 / 00:00")
            self.time_label.setAlignment(Qt.AlignCenter)
            self.play_btn = QPushButton("播放")

            sub_layout = QHBoxLayout()
            sub_layout.addWidget(self.play_btn)
            sub_layout.addWidget(self.slider)
            sub_layout.addWidget(self.time_label)

            layout.addWidget(audio_label)
            layout.addSpacing(8)
            layout.addLayout(sub_layout)

            self.play_btn.clicked.connect(self.toggle_play)
            self.player.durationChanged.connect(self.on_duration_changed)
            self.player.positionChanged.connect(self.on_position_changed)
            self.slider.sliderMoved.connect(self.on_slider_user_move)

        else:
            tip = QLabel(f"暂不支持预览：{os.path.basename(file_path)}\n后缀：{ext}")
            tip.setAlignment(Qt.AlignCenter)
            layout.addWidget(tip)

    def toggle_play(self):
        if not self.player:
            return
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
            self.play_btn.setText("播放")
        else:
            win = self.window()
            if hasattr(win, "pause_all_audio"):
                win.pause_all_audio(exclude=self)
            self.player.play()
            self.play_btn.setText("暂停")

    def on_duration_changed(self, dur):
        self.slider.setRange(0, dur)
        total = ms_to_time(dur)
        cur = ms_to_time(self.player.position())
        self.time_label.setText(f"{cur} / {total}")

    def on_position_changed(self, pos):
        self.slider.blockSignals(True)
        self.slider.setValue(pos)
        self.slider.blockSignals(False)
        total = ms_to_time(self.player.duration())
        cur = ms_to_time(pos)
        self.time_label.setText(f"{cur} / {total}")

    def on_slider_user_move(self, pos):
        self.player.setPosition(pos)

    def stop_audio(self):
        if self.player:
            self.player.stop()
            self.play_btn.setText("播放")

    def closeEvent(self, event):
        self.stop_audio()
        event.accept()


class FileManagerPage(QWidget):
    def __init__(self, root_path, parent_window):
        super().__init__()
        self.root_path = root_path
        self.main_win = parent_window
        self.clip_path = None
        self.is_cut = False
        self.main_win.project_path = root_path

        self.fs_model = QFileSystemModel()
        self.fs_model.setRootPath(root_path)
        self.fs_model.setFilter(QDir.AllEntries | QDir.NoDotAndDotDot)

        self.tree_view = QTreeView()
        self.tree_view.setModel(self.fs_model)
        self.tree_view.setRootIndex(self.fs_model.index(root_path))
        self.tree_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree_view.customContextMenuRequested.connect(self.tree_right_menu)

        self.list_view = QListView()
        self.list_view.setModel(self.fs_model)
        self.list_view.setRootIndex(self.fs_model.index(root_path))
        self.list_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_view.customContextMenuRequested.connect(self.list_right_menu)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.tree_view)
        splitter.addWidget(self.list_view)
        splitter.setStretchFactor(1, 2)

        self.path_label = QLabel(root_path)
        self.path_label.setObjectName("PathBarLabel")
        self.path_label.setFixedHeight(30)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.path_label)
        main_layout.addWidget(splitter)

        self.tree_view.setAttribute(Qt.WA_StyledBackground, True)
        self.tree_view.viewport().setAttribute(Qt.WA_StyledBackground, True)
        self.list_view.setAttribute(Qt.WA_StyledBackground, True)
        self.list_view.viewport().setAttribute(Qt.WA_StyledBackground, True)

        self.tree_view.selectionModel().selectionChanged.connect(self.on_tree_select)
        self.list_view.selectionModel().selectionChanged.connect(self.on_list_select)

    def get_selected_path(self, view):
        idx = view.currentIndex()
        if not idx.isValid():
            return None
        return self.fs_model.filePath(idx)

    def on_tree_select(self):
        path = self.get_selected_path(self.tree_view)
        if path and os.path.isdir(path):
            self.list_view.setRootIndex(self.fs_model.index(path))
            self.path_label.setText(path)

    def on_list_select(self):
        path = self.get_selected_path(self.list_view)
        if path and os.path.isfile(path):
            self.main_win.open_preview_tab(path)

    def tree_right_menu(self, pos: QPoint):
        index = self.tree_view.indexAt(pos)
        self._build_menu(pos, index, self.tree_view)

    def list_right_menu(self, pos: QPoint):
        index = self.list_view.indexAt(pos)
        self._build_menu(pos, index, self.list_view)

    def _build_menu(self, pos: QPoint, index, view):
        menu = QMenu()

        current_dir = self.fs_model.filePath(index) if index.isValid() else self.root_path
        if not os.path.isdir(current_dir):
            current_dir = os.path.dirname(current_dir)

        act_new_folder = QAction("新建文件夹", self)
        act_new_folder.triggered.connect(lambda _, d=current_dir: self.new_folder(d))
        menu.addAction(act_new_folder)

        act_new_dialog = QAction("新建对话剧本", self)
        act_new_dialog.triggered.connect(lambda _, d=current_dir: self.create_dialog_file(d))
        menu.addAction(act_new_dialog)

        act_new_script = QAction("新建脚本", self)
        act_new_script.triggered.connect(lambda _, d=current_dir: self.create_cfg_file(d))
        menu.addAction(act_new_script)

        act_new_python_script = QAction("新建Python脚本", self)
        act_new_python_script.triggered.connect(lambda _, d=current_dir: self.create_new_python_script(d))
        menu.addAction(act_new_python_script)

        if index.isValid():
            sel_path = self.fs_model.filePath(index)

            act_rename = QAction("重命名", self)
            act_rename.triggered.connect(lambda _, p=sel_path: self.rename_file(p))
            menu.addAction(act_rename)

            act_del = QAction("删除", self)
            act_del.triggered.connect(lambda _, p=sel_path: self.delete_file(p))
            menu.addAction(act_del)

            if os.path.isfile(sel_path):
                act_preview = QAction("文件预览", self)
                act_preview.triggered.connect(lambda _, p=sel_path: self.main_win.open_preview_tab(p))
                menu.addAction(act_preview)

                if sel_path.endswith(".cfg"):
                    act_edit_script = QAction("脚本编辑", self)
                    act_edit_script.triggered.connect(lambda _, p=sel_path: self.main_win.script_editor_tab(p))
                    menu.addAction(act_edit_script)

                if sel_path.endswith(".json"):
                    try:
                        with open(sel_path, "r", encoding="utf-8") as f:
                            dd = json.load(f)
                        if "dialogs" in dd:
                            act_edit_dialog = QAction("对话剧本编辑", self)
                            act_edit_dialog.triggered.connect(lambda _, p=sel_path: self.main_win.dialogue_editor_tab(p, self.main_win))
                            menu.addAction(act_edit_dialog)
                    except Exception:
                        pass
                if sel_path.endswith(".py"):
                    act_edit_script = QAction("Python编辑", self)
                    act_edit_script.triggered.connect(lambda _, p=sel_path: self.main_win.python_editor_tab(p, self.main_win))
                    menu.addAction(act_edit_script)

        if self.clip_path:
            act_paste = QAction("粘贴", self)
            act_paste.triggered.connect(lambda _, d=current_dir: self.paste_file(d))
            menu.addAction(act_paste)

        menu.exec(view.viewport().mapToGlobal(pos))

    def new_folder(self, parent_dir):
        name, ok = QInputDialog.getText(self, "新建文件夹", "文件夹名称：")
        if ok and name.strip():
            new_path = os.path.join(parent_dir, name.strip())
            try:
                os.mkdir(new_path)
            except Exception as e:
                QMessageBox.warning(self, "错误", f"创建失败：{str(e)}")

    def rename_file(self, old_path):
        base_dir = os.path.dirname(old_path)
        old_name = os.path.basename(old_path)
        new_name, ok = QInputDialog.getText(self, "重命名", "新名称：", text=old_name)
        if ok and new_name.strip() and new_name != old_name:
            new_path = os.path.join(base_dir, new_name.strip())
            try:
                os.rename(old_path, new_path)
                self.main_win.update_preview_tab_path(old_path, new_path)
            except Exception as e:
                QMessageBox.warning(self, "错误", f"重命名失败：{str(e)}")

    def copy_file(self, path):
        self.clip_path = path
        self.is_cut = False

    def cut_file(self, path):
        self.clip_path = path
        self.is_cut = True

    def paste_file(self, target_dir):
        if not self.clip_path or not os.path.exists(self.clip_path):
            QMessageBox.information(self, "提示", "剪贴板为空或源文件不存在")
            return

        try:
            src_name = os.path.basename(self.clip_path)
            dst_path = os.path.join(target_dir, src_name)
            counter = 1
            while os.path.exists(dst_path):
                name, ext = os.path.splitext(src_name)
                dst_path = os.path.join(target_dir, f"{name}_{counter}{ext}")
                counter += 1

            if os.path.isdir(self.clip_path):
                if self.is_cut:
                    shutil.move(self.clip_path, dst_path)
                else:
                    shutil.copytree(self.clip_path, dst_path)
            else:
                if self.is_cut:
                    shutil.move(self.clip_path, dst_path)
                else:
                    shutil.copy2(self.clip_path, dst_path)

            if self.is_cut:
                self.main_win.close_tab_by_path(self.clip_path)
                self.clip_path = None
                self.is_cut = False

            QMessageBox.information(self, "成功", "粘贴完成")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"粘贴失败：{str(e)}")

    def delete_file(self, path):
        ret = QMessageBox.question(self, "确认删除", f"确定删除 {os.path.basename(path)}？", QMessageBox.Yes | QMessageBox.No)
        if ret == QMessageBox.Yes:
            try:
                self.main_win.close_tab_by_path(path)
                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)
            except Exception as e:
                QMessageBox.warning(self, "错误", f"删除失败：{str(e)}")

    def import_file(self, target_dir):
        files, _ = QFileDialog.getOpenFileNames(self, "选择要导入的文件")
        if not files:
            return
        try:
            for f in files:
                dst = os.path.join(target_dir, os.path.basename(f))
                if os.path.exists(dst):
                    name, ext = os.path.splitext(os.path.basename(f))
                    dst = os.path.join(target_dir, f"{name}_copy{ext}")
                shutil.copy2(f, dst)
            QMessageBox.information(self, "导入完成", f"共导入{len(files)}个文件")
        except Exception as e:
            QMessageBox.warning(self, "导入失败", str(e))

    def export_file(self, src_path):
        save_path, _ = QFileDialog.getSaveFileName(self, "导出文件", os.path.basename(src_path))
        if not save_path:
            return
        try:
            shutil.copy2(src_path, save_path)
            QMessageBox.information(self, "导出成功", f"已保存至：{save_path}")
        except Exception as e:
            QMessageBox.warning(self, "导出失败", str(e))

    def create_dialog_file(self, path):
        dialog_file_name, ok = QInputDialog.getText(self, "创建剧本", "输入剧本文件名：")
        if ok and dialog_file_name.strip():
            dialog_id, ok = QInputDialog.getText(self, "剧本ID", "输入剧本ID：")
            if ok and dialog_id.strip():
                dialog_file_path = os.path.join(path, f"{dialog_file_name.strip()}.json")
                if os.path.exists(dialog_file_path):
                    QMessageBox.warning(self, "错误", "文件已存在")
                    return
                dialog_file = {
                    "id": dialog_id.strip(),
                    "dialogs": []
                }
                with open(dialog_file_path, "w", encoding="utf-8") as f:
                    json.dump(dialog_file, f, ensure_ascii=False, indent=4)

    def create_cfg_file(self, path):
        script_name, ok = QInputDialog.getText(self, "新建脚本", "脚本文件名（不需要后缀）：")
        if ok and script_name.strip():
            script_path = os.path.join(path, f"{script_name.strip()}.cfg")
            if os.path.exists(script_path):
                QMessageBox.warning(self, "错误", "文件已存在")
                return
            open(script_path, "w", encoding="utf-8").close()

    def create_new_python_script(self,path):
        script_name, ok = QInputDialog.getText(self, "新建Python脚本", "脚本文件名（不需要后缀）：")
        if ok and script_name.strip():
            script_path = os.path.join(path, f"{script_name.strip()}.py")
            if os.path.exists(script_path):
                QMessageBox.warning(self, "错误", "文件已存在")
                return
            shutil.copyfile("res/python_script_template.txt", script_path)


class MainEditorWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        with open("config/editor.json", "r", encoding="utf-8") as f:
            self.editor_config = json.load(f)

        if "theme" not in self.editor_config:
            self.editor_config["theme"] = "light"

        self.setWindowIcon(QIcon("res/AoiStudio.png"))
        self.resize(1024, 640)

        if not os.path.exists("caches"):
            os.makedirs("caches")
            with open("caches/player_path.txt", "w", encoding="utf-8") as f:
                f.write(os.path.abspath("bin/AoiStudio_Player.exe"))
            with open("caches/build_tool_path.txt", "w", encoding="utf-8") as f:
                f.write(os.path.abspath("bin/AoiStudioBuildTool.exe"))
            with open("caches/debug_player_path.txt", "w", encoding="utf-8") as f:
                f.write(os.path.abspath("bin/AoiStudio_Player_debug.exe"))
            with open("caches/debugger_path.txt", "w", encoding="utf-8") as f:
                f.write(os.path.abspath("bin/AoiStudio_Debugger.exe"))

        debug_player_path = open("caches/debug_player_path.txt", encoding="utf-8").read().strip()
        if not os.path.exists(debug_player_path):
            self.setWindowTitle(
                f"AoiStudio Editor {self.editor_config['platform']['name']} {self.editor_config['version']['editor_ui']} - Not installed"
            )
        else:
            self.setWindowTitle(
                f"AoiStudio Editor {self.editor_config['platform']['name']} {self.editor_config['version']['editor_ui']} - {self.editor_config['version']['player']}"
            )

        self.project_path = ""
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.on_tab_close)
        self.setCentralWidget(self.tab_widget)
        self.is_opening_project = False

        menubar = self.menuBar()

        file_menu = menubar.addMenu("文件")
        file_menu.addAction("退出", self.close)
        file_menu.addAction("构建剧本索引", self.build_id_file)
        file_menu.addAction("编辑角色", self.edit_character)

        view_menu = menubar.addMenu("项目")
        open_fm_act = QAction("打开项目", self)
        open_fm_act.triggered.connect(lambda: self.open_file_manager_tab())
        view_menu.addAction(open_fm_act)

        create_prj_act = QAction("创建项目", self)
        create_prj_act.triggered.connect(self.create_new_project)
        view_menu.addAction(create_prj_act)

        project_setings_act = QAction("项目设置", self)
        project_setings_act.triggered.connect(self.open_project_settings)
        view_menu.addAction(project_setings_act)

        project_main_menu_settings_act = QAction("主菜单设置", self)
        project_main_menu_settings_act.triggered.connect(self.open_project_main_menu_settings)
        view_menu.addAction(project_main_menu_settings_act)

        project_build_act = QAction("打包项目", self)
        project_build_act.triggered.connect(self.project_build)
        view_menu.addAction(project_build_act)

        preview_menu = menubar.addMenu("预览")
        preview_game = QAction("预览游戏", self)
        preview_game.triggered.connect(self.preview_game)
        preview_menu.addAction(preview_game)

        aoi_studio_menu = menubar.addMenu("AoiStudio")
        aoi_studio_menu.addAction("安装扩展", self.install_aoi_file)
        aoi_studio_menu.addAction("文档", self.show_documentation)

        theme_submenu = aoi_studio_menu.addMenu("主题")
        act_theme_light = QAction("浅色主题", self)
        act_theme_light.triggered.connect(lambda: self.switch_theme("light"))
        act_theme_dark = QAction("暗色主题", self)
        act_theme_dark.triggered.connect(lambda: self.switch_theme("dark"))
        theme_submenu.addAction(act_theme_light)
        theme_submenu.addAction(act_theme_dark)

        self.apply_theme(self.editor_config["theme"])

    def apply_theme(self, theme_name):
        app = QApplication.instance()
        if theme_name == "dark":
            app.setStyleSheet(DARK_THEME_QSS)
        else:
            app.setStyleSheet(LIGHT_THEME_QSS)

    def switch_theme(self, theme_name):
        self.editor_config["theme"] = theme_name
        with open("config/editor.json", "w", encoding="utf-8") as f:
            json.dump(self.editor_config, f, ensure_ascii=False, indent=4)
        self.apply_theme(theme_name)

    def safe_decode(self,b: bytes) -> str:
        """兼容Windows GBK / UTF‑8 日志解码，不会抛出异常"""
        if not b:
            return ""
        try:
            return b.decode("utf-8")
        except UnicodeDecodeError:
            try:
                return b.decode("gbk")
            except UnicodeDecodeError:
                return b.decode("utf-8", errors="replace")

    def preview_game(self):
        try:
            debug_player_path = open("caches/debug_player_path.txt", encoding="utf-8").read().strip()
        except Exception:
            QMessageBox.warning(self, "错误", "读取播放器路径缓存失败")
            return

        if not os.path.exists(debug_player_path):
            QMessageBox.warning(self, "播放器缺失", "请先安装游戏播放器")
            return
        if not self.is_opening_project:
            QMessageBox.warning(self, "错误", "请先打开项目")
            return

        if check_game_file_full.check_game_file_full(self.project_path) != check_game_file_full.NOT_MISS:
            ret = QMessageBox.question(self, "构建剧本索引", "检测到资源缺失，是否构建剧本索引？",
                                       QMessageBox.Yes | QMessageBox.No)
            if ret == QMessageBox.Yes:
                self.build_id_file()
            else:
                return

        try:
            self.debugger_path = open("caches/debugger_path.txt", encoding="utf-8").read().strip()
        except Exception:
            self.debugger_path = ""

        # 保存进程对象，用于后续关闭预览
        self._preview_game_proc = None
        threading.Thread(target=self.preview_game_thread, daemon=True).start()
        threading.Thread(target=self.preview_game_debugger, daemon=True).start()

    def preview_game_thread(self):
        player_path = open("caches/debug_player_path.txt", encoding="utf-8").read().strip()
        project_cwd = self.project_path

        try:
            self._preview_game_proc = subprocess.Popen(
                [player_path],
                cwd=project_cwd,  # ✅子进程单独工作目录，不再用os.chdir！
                bufsize=0,
                creationflags=subprocess.CREATE_NEW_CONSOLE  # ✅子进程不创建控制台窗口，避免干扰编辑器UI
            )
            # 循环读取stdout日志
            while True:
                raw = self._preview_game_proc.stdout.readline()
                if not raw:
                    break
                text = self.safe_decode(b=raw)
                # 这里text就是引擎输出的日志，你可以emit信号给到编辑器UI日志面板
                # self.sig_log.emit(text)

            # 读取stderr
            while True:
                raw_err = self._preview_game_proc.stderr.readline()
                if not raw_err:
                    break
                text_err = self.safe_decode(raw_err)

            self._preview_game_proc.wait()
        except Exception as e:
            print(f"[预览启动异常] {e}")
        self._preview_game_proc = None

    def preview_game_debugger(self):
        dp = self.debugger_path.strip()
        if not dp or not os.path.exists(dp):
            return
        try:
            subprocess.Popen([dp],creationflags=subprocess.CREATE_NO_WINDOW)
        except Exception as e:
            print(f"[调试器启动失败] {e}")

    def pause_all_audio(self, exclude=None):
        for i in range(self.tab_widget.count()):
            w = self.tab_widget.widget(i)
            if isinstance(w, PreviewPage) and w != exclude and w.player:
                w.player.pause()
                w.play_btn.setText("播放")

    def open_file_manager_tab(self, path=None):
        if path is None:
            root_dir = QFileDialog.getExistingDirectory(self, "选择项目目录")
        else:
            root_dir = path
        if not root_dir:
            return
        fm_page = FileManagerPage(root_dir, self)
        title = f"资源管理器 - {os.path.basename(root_dir)}"
        self.tab_widget.addTab(fm_page, title)
        self.tab_widget.setCurrentWidget(fm_page)
        self.is_opening_project = True

    def open_file_manager_tab_by_path(self, path):
        fm_page = FileManagerPage(path, self)
        title = f"资源管理器 - {os.path.basename(path)}"
        self.tab_widget.addTab(fm_page, title)
        self.tab_widget.setCurrentWidget(fm_page)
        self.is_opening_project = True

    def open_preview_tab(self, file_path):
        if not isinstance(file_path, (str, os.PathLike)) or not file_path:
            print(f"[open_preview_tab] 非法路径: {repr(file_path)}")
            return

        for i in range(self.tab_widget.count()):
            widget = self.tab_widget.widget(i)
            if isinstance(widget, PreviewPage) and widget.file_path == file_path:
                self.tab_widget.setCurrentIndex(i)
                return

        preview = PreviewPage(file_path)
        tab_name = os.path.basename(file_path)
        self.tab_widget.addTab(preview, tab_name)
        self.tab_widget.setCurrentWidget(preview)

    def update_preview_tab_path(self, old_path, new_path):
        if not isinstance(old_path, str) or not isinstance(new_path, str):
            return

        for i in range(self.tab_widget.count()):
            w = self.tab_widget.widget(i)
            if isinstance(w, PreviewPage) and w.file_path == old_path:
                w.file_path = new_path
                self.tab_widget.setTabText(i, os.path.basename(new_path))

    def close_tab_by_path(self, target_path):
        if not isinstance(target_path, str) or not target_path:
            return

        to_close = []
        for i in range(self.tab_widget.count()):
            w = self.tab_widget.widget(i)
            if isinstance(w, PreviewPage) and w.file_path == target_path:
                to_close.append(i)

        for idx in reversed(to_close):
            self.tab_widget.removeTab(idx)

    def on_tab_close(self, index):
        widget = self.tab_widget.widget(index)

        if hasattr(widget, "can_switch_out"):
            ok = widget.can_switch_out()
            if not ok:
                return

        if isinstance(widget, PreviewPage):
            widget.stop_audio()

        self.tab_widget.removeTab(index)

    def script_editor_tab(self, file_path):
        if not isinstance(file_path, str) or not file_path:
            print(f"[script_editor_tab] 非法路径: {repr(file_path)}")
            return

        editor = editor_script.CFGCommandEditor(file_path=file_path)
        tab_name = f"脚本编辑 - {os.path.basename(file_path)}"
        self.tab_widget.addTab(editor, tab_name)
        self.tab_widget.setCurrentWidget(editor)

    def dialogue_editor_tab(self, file_path, main_win):
        if not isinstance(file_path, str) or not file_path:
            print(f"[dialogue_editor_tab] 非法路径: {repr(file_path)}")
            return

        try:
            editor = editor_dialog.DialogJsonEditor(file_path=file_path, main_win=main_win)
            tab_name = f"剧本编辑 - {os.path.basename(file_path)}"
            self.tab_widget.addTab(editor, tab_name)
            self.tab_widget.setCurrentWidget(editor)
        except Exception as e:
            traceback.print_exc()
            QMessageBox.warning(self, "错误", f"打开剧本编辑器失败：{str(e)}")

    def python_editor_tab(self, file_path, main_win):
        if not isinstance(file_path, str) or not file_path:
            print(f"[dialogue_editor_tab] 非法路径: {repr(file_path)}")
            return

        try:
            editor = editor_python_edit.PyScriptEditor(file_path=file_path)
            tab_name = f"Python 代码编辑 - {os.path.basename(file_path)}"
            self.tab_widget.addTab(editor, tab_name)
            self.tab_widget.setCurrentWidget(editor)
        except Exception as e:
            traceback.print_exc()
            QMessageBox.warning(self, "错误", f"打开剧本编辑器失败：{str(e)}")

    def create_new_project(self):
        base_dir = QFileDialog.getExistingDirectory(self, "选择存放位置")
        if not base_dir:
            return

        project_name, ok = QInputDialog.getText(self, "创建新项目", "项目文件夹名称：")
        if not (ok and project_name.strip()):
            return

        target_prj_path = os.path.join(base_dir, project_name.strip())

        if os.path.exists(target_prj_path):
            QMessageBox.warning(self, "错误", "目标文件夹已存在！")
            return

        try:
            shutil.copytree("res/project_example", target_prj_path)

            game_cfg_path = os.path.join(target_prj_path, "config", "Game.json")
            with open(game_cfg_path, "w", encoding="utf-8") as f:
                json.dump({
                    "name": project_name.strip(),
                    "game_size": [1200, 768],
                    "splash_screen": True,
                    "show_studio_logo": True,
                    "show_made_with_engine": True,
                    "engine_version": self.editor_config["version"]["player"]
                }, f, indent=4, ensure_ascii=False)

            self.open_file_manager_tab_by_path(target_prj_path)

        except Exception as e:
            traceback.print_exc()
            QMessageBox.warning(self, "创建项目失败", str(e))

    def open_project_settings(self):
        if not self.is_opening_project:
            QMessageBox.warning(self, "错误", "请先打开项目")
            return

        project_settings_win = editor_project_settings.ProjectConfigEditor(self, self.project_path)
        project_settings_win.show()

    def open_project_main_menu_settings(self):
        if not self.is_opening_project:
            QMessageBox.warning(self, "错误", "请先打开项目")
            return

        try:
            json_path = os.path.join(self.project_path, "config", "main_menu.json")
            project_main_menu_settings_win = editor_main_menu_settings.ConfigPopupWindow(self)
            project_main_menu_settings_win.load_json(path=json_path)
            project_main_menu_settings_win.show()
        except Exception as e:
            traceback.print_exc()
            QMessageBox.warning(self, "错误", f"打开主菜单设置失败：{str(e)}")

    def project_build(self):
        build_tool_path = open("caches/build_tool_path.txt", encoding="utf-8").read().strip()
        player_path = open("caches/player_path.txt", encoding="utf-8").read().strip()
        debug_player_path = open("caches/debug_player_path.txt", encoding="utf-8").read().strip()

        if not os.path.exists(build_tool_path):
            QMessageBox.warning(self, "ABT缺失", "请先安装AoiStudioBuildTool扩展")
            return
        if not os.path.exists(debug_player_path):
            QMessageBox.warning(self, "播放器缺失", "请先安装播放器扩展")
            return
        if not self.is_opening_project:
            QMessageBox.warning(self, "错误", "请先打开项目")
            return

        output_path = QFileDialog.getExistingDirectory(self, "选择打包输出目录")
        if output_path:
            threading.Thread(
                target=lambda: self.project_build_thread(output_path, build_tool_path, player_path),
                daemon=True
            ).start()

    def project_build_thread(self, output_path, abt_path, pl_path):
        cmd = [abt_path, self.project_path, output_path, pl_path]
        subprocess.Popen(cmd, creationflags=subprocess.CREATE_NEW_CONSOLE)

    def edit_character(self):
        if not self.is_opening_project:
            QMessageBox.warning(self, "错误", "请先打开项目")
            return

        try:
            char_path = os.path.join(self.project_path, "config", "characters.json")
            char_editor = editor_character.CharacterEditorWidget(self, char_path)
            char_editor.show()
        except Exception as e:
            traceback.print_exc()
            QMessageBox.warning(self, "错误", f"打开角色编辑器失败：{str(e)}")

    def build_id_file(self):
        if not self.is_opening_project:
            QMessageBox.warning(self, "错误", "请先打开项目")
            return

        res_dir = os.path.join(self.project_path, "res")
        out_index = os.path.join(self.project_path, "config", "dialog_index.json")
        tool_id_builder.build_dialog_index(res_dir, out_index)

    def install_aoi_file(self):
        res = QFileDialog.getOpenFileName(self, "选择扩展包", "", "AoiStudio扩展包 (*.aoi)")
        aoi_file_path = res[0]
        if not aoi_file_path:
            return

        temp_dir = "temp"

        try:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            os.makedirs(temp_dir, exist_ok=True)

            with zipfile.ZipFile(aoi_file_path, "r") as zf:
                zf.extractall(temp_dir)

            info_path = os.path.join(temp_dir, "info.json")
            file_info = json.load(open(info_path, "r", encoding="utf-8"))

            if file_info["type"] == "player":
                shutil.copyfile(
                    os.path.join(temp_dir, "player.exe"),
                    open("caches/player_path.txt", "r", encoding="utf-8").read()
                )
                shutil.copyfile(
                    os.path.join(temp_dir, "debug_player.exe"),
                    open("caches/debug_player_path.txt", "r", encoding="utf-8").read()
                )

                cfg = json.load(open("config/editor.json", "r", encoding="utf-8"))
                cfg["version"]["player"] = file_info["version"]
                with open("config/editor.json", "w", encoding="utf-8") as f:
                    json.dump(cfg, f, indent=4)

                self.editor_config = cfg
                self.setWindowTitle(
                    f"AoiStudio Editor {self.editor_config['platform']['name']} {self.editor_config['version']['editor_ui']} - {self.editor_config['version']['player']}"
                )
                QMessageBox.information(self, "成功", "播放器扩展安装完成")

            elif file_info["type"] == "abt":
                shutil.copyfile(
                    os.path.join(temp_dir, "abt.exe"),
                    open("caches/build_tool_path.txt", "r", encoding="utf-8").read()
                )

                cfg = json.load(open("config/editor.json", "r", encoding="utf-8"))
                cfg["version"]["abt"] = file_info["version"]
                with open("config/editor.json", "w", encoding="utf-8") as f:
                    json.dump(cfg, f, indent=4)

                QMessageBox.information(self, "成功", "ABT打包工具安装完成")

            elif file_info["type"] == "debugger":
                shutil.copyfile(
                    os.path.join(temp_dir, "debugger.exe"),
                    open("caches/debugger_path.txt", "r", encoding="utf-8").read()
                )
                QMessageBox.information(self, "成功", "调试器安装完成")

            elif file_info["type"] == "plugin":
                if not self.is_opening_project:
                    QMessageBox.warning(self, "错误", "安装插件请先打开项目")
                    shutil.rmtree(temp_dir)
                    return

                plugin_info = json.load(open(os.path.join(temp_dir, "plugin_info.json"), "r", encoding="utf-8"))
                plugin_target_folder = os.path.join(self.project_path, "plugins")
                os.makedirs(plugin_target_folder, exist_ok=True)
                dst_plugin = os.path.join(plugin_target_folder, f"{plugin_info['name']}.aoi")
                shutil.copyfile(aoi_file_path, dst_plugin)
                QMessageBox.information(self, "成功", "插件安装完成")

            else:
                QMessageBox.warning(self, "错误", "不识别的扩展类型")

            shutil.rmtree(temp_dir)

        except Exception as e:
            traceback.print_exc()
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            QMessageBox.warning(self, "安装扩展失败", str(e))

    def show_documentation(self):
        doc_win = editor_doc_view.DocViewerWindow(self)
        doc_win.show()


if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        win = MainEditorWindow()
        win.show()
        if len(sys.argv) >= 2:
            win.open_file_manager_tab(sys.argv[1])
        app.exec()
    except Exception:
        tb = traceback.format_exc()
        AoiStudioCrasher.main(tb)