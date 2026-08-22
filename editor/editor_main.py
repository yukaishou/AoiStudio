import os
import shutil
import sys
import threading
import time
import traceback

from PySide6.QtWidgets import (QApplication, QMainWindow, QTreeView, QListView,
                             QSplitter, QMenu, QInputDialog, QFileDialog,
                             QMessageBox, QWidget, QVBoxLayout, QHBoxLayout, QFileSystemModel, QLabel,
                             QTabWidget, QTextEdit, QScrollArea, QPushButton, QSlider)
from PySide6.QtCore import (Qt, QMimeData, QPoint,
                          QDir, QFileInfo, QUrl)
from PySide6.QtGui import QIcon, QPixmap, QAction
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from common import AoiStudioCrasher
import json
from editor import editor_dialog
from editor import editor_script
from editor import editor_project_settings
from editor import tool_id_builder
from editor import  editor_character
from editor import editor_main_menu_settings
from editor import editor_doc_view
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
/* 修复：viewport画布背景，解决白色块 */
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
/* 修复：viewport画布背景，解决暗色下白色内容区域 */
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
    """毫秒转为 00:00 格式"""
    sec = ms // 1000
    m = sec // 60
    s = sec % 60
    return f"{m:02d}:{s:02d}"


# 预览页面组件（独立顶层标签）
class PreviewPage(QWidget):
    def __init__(self, file_path):
        super().__init__()
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
            self.audio_output.setVolume(80)


            # 标题
            audio_label = QLabel(f"🎵 {os.path.basename(file_path)}")
            audio_label.setAlignment(Qt.AlignCenter)
            font = audio_label.font()
            font.setPointSize(11)
            audio_label.setFont(font)

            # 进度条 + 时间
            self.slider = QSlider(Qt.Horizontal)
            self.slider.setRange(0, 0)
            self.slider.setMinimumWidth(400)

            self.time_label = QLabel("00:00 / 00:00")
            self.time_label.setAlignment(Qt.AlignCenter)

            # 按钮行
            btn_layout = QHBoxLayout()
            self.play_btn = QPushButton("播放")
            self.play_btn.clicked.connect(self.toggle_play)
            btn_layout.addStretch()
            btn_layout.addWidget(self.play_btn)
            btn_layout.addStretch()

            # 音量行
            vol_layout = QHBoxLayout()
            vol_layout.addWidget(QLabel("音量"))
            self.vol_slider = QSlider(Qt.Horizontal)
            self.vol_slider.setRange(0, 100)
            self.vol_slider.setValue(80)
            self.vol_slider.setMaximumWidth(200)
            self.vol_slider.valueChanged.connect(self.on_volume_change)
            vol_layout.addWidget(self.vol_slider)
            vol_layout.addStretch()

            # 信号绑定
            self.player.durationChanged.connect(self.on_duration_change)
            self.player.positionChanged.connect(self.on_position_change)
            self.slider.sliderMoved.connect(self.on_slider_moved)
            self.player.playbackStateChanged.connect(self.on_play_state_changed)

            # 组装
            layout.addWidget(audio_label)
            layout.addSpacing(12)
            layout.addWidget(self.slider)
            layout.addWidget(self.time_label)
            layout.addSpacing(12)
            layout.addLayout(btn_layout)
            layout.addSpacing(8)
            layout.addLayout(vol_layout)

        else:
            tip = QLabel(f"暂不支持预览：{os.path.basename(file_path)}\n后缀：{ext}")
            tip.setAlignment(Qt.AlignCenter)
            layout.addWidget(tip)

    def toggle_play(self):
        if not self.player:
            return
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            # 通知主窗口暂停其他所有音频
            win = self.window()
            if hasattr(win, "pause_all_audio"):
                win.pause_all_audio(exclude=self)
            self.player.play()

    def on_play_state_changed(self, state):
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.play_btn.setText("暂停")
        else:
            self.play_btn.setText("播放")

    def on_duration_change(self, dur):
        self.slider.setRange(0, dur)
        total = ms_to_time(dur)
        cur = ms_to_time(self.player.position())
        self.time_label.setText(f"{cur} / {total}")

    def on_position_change(self, pos):
        self.slider.setValue(pos)
        cur = ms_to_time(pos)
        total = ms_to_time(self.player.duration())
        self.time_label.setText(f"{cur} / {total}")
        # 播放结束自动回到开头
        if pos >= self.player.duration() and self.player.duration() > 0:
            self.player.setPosition(0)
            self.player.pause()

    def on_slider_moved(self, pos):
        self.player.setPosition(pos)

    def on_volume_change(self, val):
        val = val/100
        self.audio_output.setVolume(val)

    def stop_audio(self):
        if self.player:
            self.player.stop()

    def closeEvent(self, event):
        if self.player:
            self.player.stop()
        event.accept()


# 文件管理器页面（独立顶层标签）
class FileManagerPage(QWidget):
    def __init__(self, root_path, parent_window):
        super().__init__()
        self.root_path = root_path
        self.main_win = parent_window  # 持有主窗口，用来新建预览标签
        self.clip_path = None
        self.is_cut = False
        self.main_win.project_path = root_path

        # 文件系统模型
        self.fs_model = QFileSystemModel()
        self.fs_model.setRootPath(root_path)
        self.fs_model.setFilter(QDir.AllEntries | QDir.NoDotAndDotDot)

        # 左侧目录树
        self.tree_view = QTreeView()
        self.tree_view.setModel(self.fs_model)
        self.tree_view.setRootIndex(self.fs_model.index(root_path))
        self.tree_view.setColumnHidden(1, True)
        self.tree_view.setColumnHidden(2, True)
        self.tree_view.setColumnHidden(3, True)
        self.tree_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree_view.customContextMenuRequested.connect(self.tree_right_menu)

        # 右侧文件列表
        self.list_view = QListView()
        self.list_view.setModel(self.fs_model)
        self.list_view.setRootIndex(self.fs_model.index(root_path))
        self.list_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_view.customContextMenuRequested.connect(self.list_right_menu)

        # ========== 修复顽固白色背景：强制QSS绘制背景，不使用原生系统绘制 ==========
        self.tree_view.setAttribute(Qt.WA_StyledBackground, True)
        self.tree_view.viewport().setAttribute(Qt.WA_StyledBackground, True)
        self.list_view.setAttribute(Qt.WA_StyledBackground, True)
        self.list_view.viewport().setAttribute(Qt.WA_StyledBackground, True)

        # 拖拽
        self.tree_view.setDragEnabled(True)
        self.tree_view.setAcceptDrops(True)
        self.tree_view.setDropIndicatorShown(True)
        self.list_view.setDragEnabled(True)
        self.list_view.setAcceptDrops(True)
        self.list_view.setDropIndicatorShown(True)

        # 选择联动
        self.tree_view.selectionModel().selectionChanged.connect(self.on_tree_select)
        self.list_view.selectionModel().selectionChanged.connect(self.on_list_select)

        # 路径栏
        self.path_label = QLabel(root_path)
        self.path_label.setObjectName("PathBarLabel")
        self.path_label.setAlignment(Qt.AlignCenter)
        self.path_label.setFixedHeight(30)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.tree_view)
        splitter.addWidget(self.list_view)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.path_label)
        layout.addWidget(splitter)

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

    # 右键菜单
    def tree_right_menu(self, pos: QPoint):
        index = self.tree_view.indexAt(pos)
        menu = QMenu()
        self.build_context_menu(menu, index, self.tree_view)
        menu.exec(self.tree_view.viewport().mapToGlobal(pos))

    def list_right_menu(self, pos: QPoint):
        index = self.list_view.indexAt(pos)
        menu = QMenu()
        self.build_context_menu(menu, index, self.list_view)
        menu.exec(self.list_view.viewport().mapToGlobal(pos))

    def build_context_menu(self, menu, index, view):
        path = self.fs_model.filePath(index) if index.isValid() else self.fs_model.filePath(view.rootIndex())

        act_new_folder = QAction("新建文件夹", self)
        act_new_folder.triggered.connect(lambda: self.new_folder(path if os.path.isdir(path) else os.path.dirname(path)))
        menu.addAction(act_new_folder)

        act_new_dialog = QAction("新建对话", self)
        act_new_dialog.triggered.connect(lambda: self.create_dialog_file(path))
        menu.addAction(act_new_dialog)

        act_new_script = QAction("新建脚本", self)
        act_new_script.triggered.connect(lambda: self.create_cfg_script(path))
        menu.addAction(act_new_script)
        if index.isValid():
            act_rename = QAction("重命名", self)
            act_rename.triggered.connect(lambda: self.rename_file(path))
            menu.addAction(act_rename)

            act_copy = QAction("复制", self)
            act_copy.triggered.connect(lambda: self.copy_file(path))
            menu.addAction(act_copy)

            act_cut = QAction("剪切", self)
            act_cut.triggered.connect(lambda: self.cut_file(path))
            menu.addAction(act_cut)

            act_del = QAction("删除", self)
            act_del.triggered.connect(lambda: self.delete_file(path))
            menu.addAction(act_del)


            if os.path.isfile(path):
                act_open_preview = QAction("文件预览", self)
                act_open_preview.triggered.connect(lambda: self.main_win.open_preview_tab(path))
                menu.addAction(act_open_preview)
                if path.endswith(".cfg"):
                    # 为脚本文件
                    act_open_preview = QAction("脚本编辑", self)
                    act_open_preview.triggered.connect(lambda: self.main_win.script_editor_tab(path))
                    menu.addAction(act_open_preview)
                if path.endswith(".json"):
                    try:
                        data = json.load(open(path, encoding="utf-8"))
                        # 如果拥有dialogs数组
                        if "dialogs" in data:
                            act_open_preview = QAction("对话编辑", self)
                            act_open_preview.triggered.connect(lambda: self.main_win.dialogue_editor_tab(file_path=path,main_win=self.main_win))
                            menu.addAction(act_open_preview)
                    except:
                        pass

        if self.clip_path:
            act_paste = QAction("粘贴", self)
            act_paste.triggered.connect(lambda: self.paste_file(path if os.path.isdir(path) else os.path.dirname(path)))
            menu.addAction(act_paste)

        menu.addSeparator()

        act_import = QAction("导入文件", self)
        act_import.triggered.connect(lambda: self.import_file(path if os.path.isdir(path) else os.path.dirname(path)))
        menu.addAction(act_import)

        if index.isValid() and os.path.isfile(path):
            act_export = QAction("导出文件", self)
            act_export.triggered.connect(lambda: self.export_file(path))
            menu.addAction(act_export)

    # 文件操作
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
        new_name, ok = QInputDialog.getText(self, "重命名", "输入新名称：", text=old_name)
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
                shutil.copytree(self.clip_path, dst_path)
                if self.is_cut:
                    self.main_win.close_tab_by_path(self.clip_path)
                    shutil.rmtree(self.clip_path)
                    self.clip_path = None
            else:
                shutil.copy2(self.clip_path, dst_path)
                if self.is_cut:
                    self.main_win.close_tab_by_path(self.clip_path)
                    os.remove(self.clip_path)
                    self.clip_path = None
            QMessageBox.information(self, "成功", "粘贴完成")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"粘贴失败：{str(e)}")

    def delete_file(self, path):
        ret = QMessageBox.question(self, "确认删除", f"确定删除 {os.path.basename(path)}？",
                                    QMessageBox.Yes | QMessageBox.No)
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
        dialog_file_name,ok  = QInputDialog.getText(self, "创建剧本", "输入剧本名称：")
        if ok:
            dialog_id,ok = QInputDialog.getText(self, "创建剧本", "输入剧本ID：")
            if ok:
                dialog_file_path = os.path.join(path, f"{dialog_file_name}.json")
                if os.path.exists(dialog_file_path):
                    QMessageBox.warning(self, "错误", "文件已存在")
                    return
                dialog_file = {
                    "id": dialog_id,
                    "dialogs": []
                }
                with open(dialog_file_path, "w", encoding="utf-8") as f:
                    json.dump(dialog_file, f, ensure_ascii=False, indent=4)

    def create_cfg_script(self,path):
        script_name,ok = QInputDialog.getText(self, "创建脚本", "输入脚本文件名称：")
        if ok:
            script_file_path = os.path.join(path, f"{script_name}.cfg")
            if os.path.exists(script_file_path):
                QMessageBox.warning(self, "错误", "文件已存在")
                return
            open(script_file_path, "w", encoding="utf-8")


# 主窗口，唯一一层全局标签
class MainEditorWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.editor_config = json.load(open("config/editor.json",encoding="utf-8"))
        # 如果配置没有theme字段，默认light
        if "theme" not in self.editor_config:
            self.editor_config["theme"] = "light"

        self.setWindowIcon(QIcon("res/AoiStudio.png"))
        self.resize(800, 540)

        if not os.path.exists("caches"):
            os.mkdir("caches")
            with open("caches/player_path.txt", "w", encoding="utf-8") as f:
                f.write(f"{os.path.abspath("bin/AoiStudio_Player.exe")}")
            with open("caches/build_tool_path.txt", "w", encoding="utf-8") as f:
                f.write(f"{os.path.abspath("bin/AoiStudioBuildTool.exe")}")
            with open("caches/debug_player_path.txt", "w", encoding="utf-8") as f:
                f.write(f"{os.path.abspath("bin/AoiStudio_Player_debug.exe")}")
            with open("caches/debugger_path.txt", "w", encoding="utf-8") as f:
                f.write(f"{os.path.abspath("bin/AoiStudio_Debugger.exe")}")
        if not os.path.exists(open("caches/debug_player_path.txt", encoding="utf-8").read()):
            self.setWindowTitle(
                f"AoiStudio Editor {self.editor_config['platform']['name']} {self.editor_config['version']['editor_ui']} - Not installed")
        else:
            self.setWindowTitle(
                f"AoiStudio Editor {self.editor_config['platform']['name']} {self.editor_config['version']['editor_ui']} - {self.editor_config['version']['player']}")
        self.project_path = ""

        # 唯一一层标签栏，所有页面平级
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.on_tab_close)
        self.setCentralWidget(self.tab_widget)
        self.is_opening_project = False

        # 菜单栏
        menubar = self.menuBar()

        file_menu = menubar.addMenu("文件")
        file_menu.addAction("退出", self.close)
        file_menu.addAction("构建剧本索引", self.build_id_file)
        file_menu.addAction("编辑角色", self.edit_character)

        view_menu = menubar.addMenu("项目")
        open_fm_act = QAction("打开项目", self)
        open_fm_act.triggered.connect(lambda :self.open_file_manager_tab())
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

        # ========== 新增主题子菜单 ==========
        theme_submenu = aoi_studio_menu.addMenu("主题")
        act_theme_light = QAction("浅色主题", self)
        act_theme_light.triggered.connect(lambda:self.switch_theme("light"))
        act_theme_dark = QAction("暗色主题", self)
        act_theme_dark.triggered.connect(lambda:self.switch_theme("dark"))
        theme_submenu.addAction(act_theme_light)
        theme_submenu.addAction(act_theme_dark)

        # 启动加载保存的主题
        self.apply_theme(self.editor_config["theme"])


    def apply_theme(self, theme_name):
        """应用主题样式"""
        app = QApplication.instance()
        if theme_name == "dark":
            app.setStyleSheet(DARK_THEME_QSS)
        else:
            app.setStyleSheet(LIGHT_THEME_QSS)

    def switch_theme(self, theme_name):
        """切换主题并保存配置"""
        self.editor_config["theme"] = theme_name
        # 保存到editor.json
        with open("config/editor.json","w",encoding="utf-8") as f:
            json.dump(self.editor_config,f,ensure_ascii=False,indent=4)
        self.apply_theme(theme_name)

    def preview_game(self):
        if not os.path.exists(open("caches/debug_player_path.txt",encoding="utf-8").read()):
             QMessageBox.warning(self, "播放器缺失", "请先安装游戏播放器")
             return
        else:
            pass
        if self.is_opening_project:
            print("正在预览中...")
            # 异步预览
            self.debugger_path = open("caches/debugger_path.txt", encoding="utf-8").read()

            threading.Thread(target=lambda: self.preview_game_thread()).start()
            threading.Thread(target=lambda: self.preview_game_debugger()).start()
        else:
            QMessageBox.warning(self, "错误", "请先打开项目")

    def preview_game_thread(self):
        o_path = os.getcwd()
        player_path = open("caches/debug_player_path.txt",encoding="utf-8").read()
        os.chdir(self.project_path)
        os.system(player_path)
        os.chdir(o_path)

    def preview_game_debugger(self):
        time.sleep(5)
        if os.path.exists(self.debugger_path):
            os.system(self.debugger_path)

    def pause_all_audio(self, exclude=None):
        """暂停所有音频预览，切换播放时互斥"""
        for i in range(self.tab_widget.count()):
            w = self.tab_widget.widget(i)
            if isinstance(w, PreviewPage) and w != exclude and w.player:
                w.player.pause()

    def open_file_manager_tab(self,path=None):
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
        root_dir = path
        fm_page = FileManagerPage(root_dir, self)
        title = f"资源管理器 - {os.path.basename(root_dir)}"
        self.tab_widget.addTab(fm_page, title)
        self.tab_widget.setCurrentWidget(fm_page)
        self.is_opening_project = True

    def open_preview_tab(self, file_path):
        # 查找是否已经打开该预览
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
        for i in range(self.tab_widget.count()):
            w = self.tab_widget.widget(i)
            if isinstance(w, PreviewPage) and w.file_path == old_path:
                w.file_path = new_path
                self.tab_widget.setTabText(i, os.path.basename(new_path))

    def close_tab_by_path(self, target_path):
        to_close = []
        for i in range(self.tab_widget.count()):
            w = self.tab_widget.widget(i)
            if isinstance(w, PreviewPage) and w.file_path == target_path:
                to_close.append(i)
        for idx in reversed(to_close):
            self.tab_widget.removeTab(idx)

    def on_tab_close(self, index):
        self.tab_widget.removeTab(index)

    def script_editor_tab(self, file_path):
        editor = editor_script.CFGCommandEditor(file_path=file_path)
        tab_name = f"脚本编辑 - {os.path.basename(f"{file_path}")}"
        self.tab_widget.addTab(editor, tab_name)
        self.tab_widget.setCurrentWidget(editor)

    def dialogue_editor_tab(self, file_path,main_win):
        try:
            editor = editor_dialog.DialogJsonEditor(file_path=file_path,main_win=main_win)
            tab_name = f"剧本编辑 - {os.path.basename(f"{file_path}")}"
            self.tab_widget.addTab(editor, tab_name)
            self.tab_widget.setCurrentWidget(editor)
        except Exception as e:
            QMessageBox.warning(self, "错误", f"打开失败：{str(e)}")

    def create_new_project(self):
        project_path = QFileDialog.getExistingDirectory(self, "选择项目目录", "")
        if not project_path:
            return
        project_name, ok = QInputDialog.getText(self, "创建项目", "输入项目名：")
        if ok:
            shutil.copytree("res/project_example", os.path.join(project_path, project_name))
            try:
                with open(f"{project_path}/{project_name}/config/Game.json", "w", encoding="utf-8") as f:
                    json.dump(
                        {
                            "name": f"{project_name}",
                            "game_size": [1200, 768],
                            "splash_screen": True,
                            "show_studio_logo": True,
                            "show_made_with_engine": True,
                            "engine_version":self.editor_config["version"]["player"]
                        }
                        , f, indent=4
                    )
                self.open_file_manager_tab_by_path(f"{project_path}/{project_name}")
            except Exception as e:
                QMessageBox.warning(self, "错误", f"创建失败：{str(e)}")

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
            project_main_menu_settings_win = editor_main_menu_settings.ConfigPopupWindow(self)
            project_main_menu_settings_win.load_json(path=f"{self.project_path}/config/main_menu.json")
            project_main_menu_settings_win.show()
        except Exception as e:
            print(e)
            QMessageBox.warning(self, "错误", f"打开失败：{str(e)}")

    def project_build(self):
        if not os.path.exists(open("caches/build_tool_path.txt",encoding="utf-8").read()):
             QMessageBox.warning(self, "ABT缺失", "请先安装ABT")
             return
        if not os.path.exists(open("caches/debug_player_path.txt",encoding="utf-8").read()):
             QMessageBox.warning(self, "播放器缺失", "请先安装游戏播放器")
             return
        if not self.is_opening_project:
            QMessageBox.warning(self, "错误", "请先打开项目")
            return
        output_path = QFileDialog.getExistingDirectory(self, "选择输出目录", "")
        if output_path:
            threading.Thread(target=lambda :self.project_build_thread(output_path)).start()


    def project_build_thread(self,output_path):
        aoi_build_tool_path = open("caches/build_tool_path.txt",encoding="utf-8").read()
        player_path = open("caches/player_path.txt",encoding="utf-8").read()
        os.system(f"{aoi_build_tool_path} {self.project_path} {output_path} {player_path}")

    def edit_character(self):
        try:
            if self.is_opening_project:
                char_editor = editor_character.CharacterEditorWidget(self, f"{self.project_path}/config/characters.json")
                char_editor.show()
            else:
                QMessageBox.warning(self, "错误", "请先打开项目")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"打开失败：{str(e)}")

    def build_id_file(self):
        if not self.is_opening_project:
            QMessageBox.warning(self, "错误", "请先打开项目")
            return
        tool_id_builder.build_dialog_index(f"{self.project_path}/res",f"{self.project_path}/config/dialog_index.json")

    def install_aoi_file(self):
        path = QFileDialog.getOpenFileName(self, "选择扩展文件", "", "扩展文件 (*.aoi)")
        if path[0]:
            print(path[0])
            try:
                aoi_file_path = str(path[0])
                with zipfile.ZipFile(aoi_file_path, "r") as zip_file:
                    zip_file.extractall("temp/")
                file_info = json.load(open("temp/info.json", "r", encoding="utf-8"))
                if file_info["type"] == "player":
                    shutil.copyfile("temp/player.exe", open("caches/player_path.txt", "r", encoding="utf-8").read())
                    shutil.copyfile("temp/debug_player.exe",
                                    open("caches/debug_player_path.txt", "r", encoding="utf-8").read())
                    editor_config = json.load(open("config/editor.json", "r", encoding="utf-8"))
                    editor_config["version"]["player"] = file_info["version"]
                    with open("config/editor.json", "w", encoding="utf-8") as f:
                        json.dump(editor_config, f, indent=4)
                    shutil.rmtree("temp")
                    self.editor_config = json.load(open("config/editor.json", "r", encoding="utf-8"))
                    self.setWindowTitle(
                        f"AoiStudio Editor {self.editor_config['platform']['name']} {self.editor_config['version']['editor_ui']} - {self.editor_config['version']['player']}")
                    QMessageBox.information(self,"安装扩展", "播放器安装成功")
                    return
                if file_info["type"] == "abt":
                    shutil.copyfile("temp/abt.exe", open("caches/build_tool_path.txt", "r", encoding="utf-8").read())
                    shutil.rmtree("temp")
                    editor_config = json.load(open("config/editor.json", "r", encoding="utf-8"))
                    editor_config["version"]["abt"] = file_info["version"]
                    with open("config/editor.json", "w", encoding="utf-8") as f:
                        json.dump(editor_config, f, indent=4)
                    QMessageBox.information(self ,"安装扩展", "ABT安装成功")
                    return
                if file_info["type"] == "debugger":
                    shutil.copyfile("temp/debugger.exe", open("caches/debugger_path.txt", "r", encoding="utf-8").read())
                    shutil.rmtree("temp")
                    QMessageBox.information(self, "安装扩展", "调试器安装成功")
                    return
                if file_info["type"] == "plugin":
                    if not self.is_opening_project:
                        QMessageBox.warning(self, "错误", "安装插件请先打开项目")
                        return
                    plugin_info = json.load(open("temp/plugin_info.json", "r", encoding="utf-8"))
                    shutil.copyfile(aoi_file_path,f"{self.project_path}/plugins/{plugin_info['name']}.aoi")
                    QMessageBox.information(self, "安装扩展", "插件安装成功")
                    return
                QMessageBox.warning(self, "错误", "未知的扩展类型")
            except Exception as e:
                traceback_ext = traceback.format_exc()
                print(traceback_ext)
                QMessageBox.warning(self, "错误", f"安装失败：{str(e)}")

    def show_documentation(self):
        doc_win = editor_doc_view.DocViewerWindow(self)
        doc_win.show()

if __name__ == "__main__":
    try:
        app = QApplication([])
        win = MainEditorWindow()
        win.show()
        if len(sys.argv) >= 2:
            win.open_file_manager_tab(sys.argv[1])
        app.exec()
    except Exception as e:
        traceback_ext = traceback.format_exc()
        AoiStudioCrasher.main(traceback_ext)