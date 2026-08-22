import datetime
import json
import shutil
import sys
import zipfile
import os
import threading
import tempfile
from pathlib import Path

# 注意 pyc_compiler 为你原有模块
import pyc_compiler
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                               QPushButton, QLineEdit, QTextEdit, QFileDialog, QLabel,
                               QListWidget, QListWidgetItem, QStackedWidget, QFormLayout,
                               QGroupBox, QSpinBox, QCheckBox, QFrame, QScrollArea, QMessageBox)
from PySide6.QtCore import Qt, QObject, Signal, QSize
from PySide6.QtGui import QFont, QColor, QPalette


# -------------------------- 跨线程信号桥 --------------------------
class ConsoleBridge(QObject):
    sig_show_ui = Signal()
    sig_exit = Signal()


# -------------------------- 数据模型：最近项目、构建历史 --------------------------
HISTORY_FILE = Path("./build_history.json")


class HistoryManager:
    """管理最近项目、构建历史持久化"""
    def __init__(self):
        self.recent_projects: list[str] = []
        self.build_records: list[dict] = []
        self.load()

    def load(self):
        if HISTORY_FILE.exists():
            try:
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    d = json.load(f)
                self.recent_projects = d.get("recent_projects", [])
                self.build_records = d.get("build_records", [])
            except Exception:
                pass

    def save(self):
        data = {
            "recent_projects": self.recent_projects,
            "build_records": self.build_records
        }
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def add_recent_project(self, path: str):
        path = str(Path(path).resolve())
        if path in self.recent_projects:
            self.recent_projects.remove(path)
        self.recent_projects.insert(0, path)
        self.recent_projects = self.recent_projects[:12]
        self.save()

    def add_build_record(self, proj_dir: str, out_aoi: str, success: bool):
        rec = {
            "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "project_dir": proj_dir,
            "output_aoi": out_aoi,
            "success": success
        }
        self.build_records.insert(0, rec)
        self.build_records = self.build_records[:50]
        self.save()


# -------------------------- 页面组件 --------------------------
class SideNav(QWidget):
    """左侧导航栏，仿UnityHub侧边按钮"""
    sig_switch_page = Signal(int)

    def __init__(self):
        super().__init__()
        self.setFixedWidth(140)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4,8,4,8)
        layout.setSpacing(6)

        self.btn_new = QPushButton("新建插件项目")
        self.btn_open = QPushButton("打开已有项目")
        self.btn_build = QPushButton("构建 .aoi 包")
        self.btn_history = QPushButton("构建历史")
        self.btn_setting = QPushButton("设置")

        for idx, btn in enumerate([self.btn_new, self.btn_open, self.btn_build, self.btn_history, self.btn_setting]):
            btn.setFixedHeight(36)
            layout.addWidget(btn)

        layout.addStretch()
        self.btn_new.clicked.connect(lambda:self.sig_switch_page.emit(0))
        self.btn_open.clicked.connect(lambda:self.sig_switch_page.emit(1))
        self.btn_build.clicked.connect(lambda:self.sig_switch_page.emit(2))
        self.btn_history.clicked.connect(lambda:self.sig_switch_page.emit(3))
        self.btn_setting.clicked.connect(lambda:self.sig_switch_page.emit(4))


class PageNewProject(QWidget):
    """新建插件项目向导页面"""
    sig_create = Signal(dict)

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        form_layout = QFormLayout(inner)
        form_layout.setSpacing(10)

        self.edt_save_dir = QLineEdit()
        self.edt_plugin_name = QLineEdit()
        self.edt_version = QLineEdit("1.0.0")
        self.edt_desc = QLineEdit("AoiStudio 插件")

        form_layout.addRow("保存父目录", self._wrap_hbox(self.edt_save_dir, self._make_browse_btn(self.on_browse_save_dir)))
        form_layout.addRow("插件名称", self.edt_plugin_name)
        form_layout.addRow("版本号", self.edt_version)
        form_layout.addRow("描述", self.edt_desc)

        scroll.setWidget(inner)
        layout.addWidget(scroll)

        btn_layout = QHBoxLayout()
        btn_create = QPushButton("创建插件项目")
        btn_create.clicked.connect(self.on_click_create)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_create)
        layout.addLayout(btn_layout)

    def _wrap_hbox(self, w1, w2):
        box = QHBoxLayout()
        box.addWidget(w1)
        box.addWidget(w2)
        return box

    def _make_browse_btn(self, cb):
        btn = QPushButton("浏览...")
        btn.clicked.connect(cb)
        btn.setFixedWidth(80)
        return btn

    def on_browse_save_dir(self):
        d = QFileDialog.getExistingDirectory(self, "选择保存位置")
        if d:
            self.edt_save_dir.setText(d)

    def on_click_create(self):
        cfg = {
            "parent_dir": self.edt_save_dir.text().strip(),
            "plugin_name": self.edt_plugin_name.text().strip(),
            "version": self.edt_version.text().strip(),
            "description": self.edt_desc.text().strip()
        }
        self.sig_create.emit(cfg)


class PageOpenProject(QWidget):
    """打开已有项目，展示最近项目卡片列表"""
    sig_open_project = Signal(str)

    def __init__(self, history: HistoryManager):
        super().__init__()
        self.history = history
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.addWidget(QLabel("<h3>最近插件项目</h3>"))

        self.list_widget = QListWidget()
        self.list_widget.setSpacing(4)
        layout.addWidget(self.list_widget)

        btn_layout = QHBoxLayout()
        btn_manual = QPushButton("手动浏览打开项目目录")
        btn_manual.clicked.connect(self.on_manual_open)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_manual)
        layout.addLayout(btn_layout)

        self.list_widget.itemDoubleClicked.connect(self.on_item_double_click)
        self.refresh_ui()

    def refresh_ui(self):
        self.list_widget.clear()
        for p in self.history.recent_projects:
            if os.path.isdir(p):
                item = QListWidgetItem(os.path.basename(p))
                item.setToolTip(p)
                item.setData(Qt.UserRole, p)
                item.setSizeHint(QSize(0,40))
                self.list_widget.addItem(item)

    def on_item_double_click(self, item:QListWidgetItem):
        path = item.data(Qt.UserRole)
        self.sig_open_project.emit(path)

    def on_manual_open(self):
        d = QFileDialog.getExistingDirectory(self, "选择插件源目录（内含plugin_info.json）")
        if d:
            self.sig_open_project.emit(d)


class PageBuild(QWidget):
    """构建aoi包页面，原GUI功能迁移过来"""
    sig_do_build = Signal(str, str)

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        group_src = QGroupBox("插件源目录")
        src_layout = QHBoxLayout(group_src)
        self.edt_src = QLineEdit()
        btn_src = QPushButton("选择目录")
        btn_src.clicked.connect(self.select_src)
        src_layout.addWidget(self.edt_src)
        src_layout.addWidget(btn_src)

        group_out = QGroupBox("输出 .aoi 文件")
        out_layout = QHBoxLayout(group_out)
        self.edt_out = QLineEdit()
        btn_out = QPushButton("选择输出")
        btn_out.clicked.connect(self.select_out)
        out_layout.addWidget(self.edt_out)
        out_layout.addWidget(btn_out)

        btn_row = QHBoxLayout()
        self.btn_build = QPushButton("执行构建 .aoi")
        self.btn_build.clicked.connect(self.on_build_click)
        self.btn_open_folder = QPushButton("打开输出文件夹")
        self.btn_clear_log = QPushButton("清空日志")
        btn_row.addWidget(self.btn_build)
        btn_row.addWidget(self.btn_open_folder)
        btn_row.addStretch()
        btn_row.addWidget(self.btn_clear_log)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)

        layout.addWidget(group_src)
        layout.addWidget(group_out)
        layout.addLayout(btn_row)
        layout.addWidget(self.log_text)

        self.btn_clear_log.clicked.connect(self.log_text.clear)
        self.btn_open_folder.clicked.connect(self.on_open_output_folder)

    def set_project_path(self, path:str):
        self.edt_src.setText(path)

    def log(self, msg:str):
        self.log_text.append(msg)

    def select_src(self):
        d = QFileDialog.getExistingDirectory(self, "插件源目录")
        if d:
            self.edt_src.setText(d)

    def select_out(self):
        fp,_ = QFileDialog.getSaveFileName(self, "保存插件包", "", "Aoi插件包(*.aoi)")
        if fp:
            self.edt_out.setText(fp)

    def on_build_click(self):
        src = self.edt_src.text().strip()
        out = self.edt_out.text().strip()
        self.sig_do_build.emit(src, out)

    def on_open_output_folder(self):
        p = self.edt_out.text().strip()
        if not p:
            return
        folder = os.path.dirname(p)
        if os.path.isdir(folder):
            if sys.platform == "win32":
                os.startfile(folder)


class PageHistory(QWidget):
    """构建历史记录页面"""
    def __init__(self, history: HistoryManager):
        super().__init__()
        self.history = history
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<h3>构建历史记录</h3>"))
        self.list = QListWidget()
        layout.addWidget(self.list)
        self.refresh()

    def refresh(self):
        self.list.clear()
        for rec in self.history.build_records:
            status = "✅成功" if rec["success"] else "❌失败"
            text = f'{rec["time"]} | {status} | {os.path.basename(rec["output_aoi"])}'
            item = QListWidgetItem(text)
            item.setToolTip(f'项目:{rec["project_dir"]}\n输出:{rec["output_aoi"]}')
            self.list.addItem(item)


class PageSetting(QWidget):
    """设置页面"""
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<h3>工具设置</h3>"))
        layout.addWidget(QLabel("1. pyc编译器由外部 pyc_compiler 模块提供\n2. 历史记录保存在 build_history.json"))
        layout.addStretch()


# -------------------------- 主窗口 --------------------------
class AoiStudioPluginHub(QMainWindow):
    def __init__(self, console, history: HistoryManager):
        super().__init__()
        self.setWindowTitle("AoiStudio Plugin SDK GUI")
        self.resize(960,640)
        self.console = console
        self.history = history

        # 中心布局：侧边栏 + 堆叠页面
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0,0,0,0)
        main_layout.setSpacing(0)

        self.sidenav = SideNav()
        self.stack = QStackedWidget()

        # 创建全部页面
        self.page_new = PageNewProject()
        self.page_open = PageOpenProject(history)
        self.page_build = PageBuild()
        self.page_history = PageHistory(history)
        self.page_setting = PageSetting()

        self.stack.addWidget(self.page_new)
        self.stack.addWidget(self.page_open)
        self.stack.addWidget(self.page_build)
        self.stack.addWidget(self.page_history)
        self.stack.addWidget(self.page_setting)

        main_layout.addWidget(self.sidenav)
        line = QFrame()
        line.setFrameShape(QFrame.VLine)
        main_layout.addWidget(line)
        main_layout.addWidget(self.stack)

        # 信号绑定
        self.sidenav.sig_switch_page.connect(self.stack.setCurrentIndex)

        self.page_new.sig_create.connect(self.handle_create_project)
        self.page_open.sig_open_project.connect(self.handle_open_project)
        self.page_build.sig_do_build.connect(self.handle_do_build)

    def handle_create_project(self, cfg:dict):
        parent_dir = cfg["parent_dir"]
        plugin_name = cfg["plugin_name"]
        if not parent_dir or not plugin_name:
            QMessageBox.warning(self, "参数错误", "保存目录和插件名称不能为空")
            return
        full_path = os.path.join(parent_dir, plugin_name)
        if os.path.exists(full_path):
            QMessageBox.warning(self, "已存在", f"目录已经存在：{full_path}")
            return
        try:
            # 复用原有控制台的 create_project 逻辑
            base_path = full_path
            os.makedirs(base_path, exist_ok=False)
            plugin_info = {
                "name": plugin_name,
                "version": cfg["version"],
                "description": cfg["description"],
                "rely_ons": []
            }
            info_path = os.path.join(base_path, "plugin_info.json")
            with open(info_path, "w", encoding="utf-8") as f:
                json.dump(plugin_info, f, indent=4, ensure_ascii=False)

            plugin_py_path = os.path.join(base_path, "plugin.py")
            plugin_template = '''class PluginBase:
    #插件基类
    #插件主逻辑在下面的Plugin类里面写，不要所有逻辑堆在基类里

    def __init__(self,api,engine,name):
        self.api = api
        # WARNING: self.engine仅供调试，未来版本移除，请优先使用self.api
        self.engine = engine
        self.name = name

    # 工具方法
    def import_model(self,model_path,name):
        """导入插件目录下模块，不要带.py后缀"""
        return self.api.import_model(self.name,model_path,name)

    # ========== Runtime游戏生命周期 ==========
    def on_game_load(self):
        """插件加载进运行时，尚未启动游戏"""
        pass

    def on_game_unload(self):
        """插件被卸载"""
        pass

    def on_game_start(self):
        """游戏正式启动"""
        pass

    def on_game_end(self):
        """游戏结束退出"""
        pass

    def on_game_update(self):
        """每帧更新回调"""
        pass

    # ========== 编辑器生命周期(预留暂未启用) ==========
    def on_editor_load(self):
        pass
    def on_editor_unload(self):
        pass
    def on_editor_start(self):
        pass
    def on_editor_end(self):
        pass
    def on_editor_update(self):
        pass


class Plugin(PluginBase):
    """插件实现入口"""
    def __init__(self,api,engine,name):
        super().__init__(api,engine,name)

    def on_game_start(self):
        print(f"插件[{self.name}]已启动")
'''
            with open(plugin_py_path, "w", encoding="utf-8") as f:
                f.write(plugin_template)

            self.history.add_recent_project(base_path)
            QMessageBox.information(self, "创建成功", f"插件项目已创建:\n{base_path}")
            # 自动切到构建页面，填充源目录
            self.page_build.set_project_path(base_path)
            self.stack.setCurrentIndex(2)
            self.page_open.refresh_ui()
            if sys.platform == "win32":
                os.startfile(base_path)
        except Exception as e:
            QMessageBox.critical(self, "创建失败", str(e))

    def handle_open_project(self, proj_dir:str):
        self.history.add_recent_project(proj_dir)
        self.page_build.set_project_path(proj_dir)
        self.stack.setCurrentIndex(2)
        self.page_open.refresh_ui()

    def handle_do_build(self, src_dir:str, out_aoi:str):
        if not src_dir or not out_aoi:
            self.page_build.log("[错误] 源目录、输出路径不能为空")
            return
        self.page_build.log(f"开始构建：{src_dir} → {out_aoi}")
        ok, msg = AoiStudioPluginBuildToolConsole.build_project_core(src_dir, out_aoi)
        self.page_build.log(msg)
        self.history.add_build_record(src_dir, out_aoi, ok)
        self.page_history.refresh()


# -------------------------- 原有控制台逻辑保留 --------------------------
class AoiStudioPluginBuildToolConsole:
    def __init__(self, bridge: ConsoleBridge):
        self.bridge = bridge
        self.commands = {
            "exit": self.cmd_exit,
            "show_ui": self.cmd_show_ui,
            "create_project": self.cmd_create_project,
            "build_project": self.cmd_build_project
        }
        self.running = True

    def run_loop(self):
        print("==== AoiStudio PluginBuildTool Console ====")
        print("命令列表：exit | show_ui | create_project <path> <name> | build_project <project_path> <output_aoi>")
        while self.running:
            try:
                line = input("> ")
            except (EOFError, KeyboardInterrupt):
                print("\n收到中断，准备退出")
                self.running = False
                self.bridge.sig_exit.emit()
                break
            line = line.strip()
            if not line:
                continue
            parts = line.split(maxsplit=1)
            cmd = parts[0].lower()
            rest = parts[1] if len(parts) > 1 else ""
            if cmd in self.commands:
                self.commands[cmd](rest)
            else:
                print(f"未知命令: {cmd}")

    def cmd_show_ui(self, _rest):
        print("[控制台] 请求打开GUI窗口")
        self.bridge.sig_show_ui.emit()

    def cmd_exit(self, _rest):
        print("[控制台] 收到exit，准备退出")
        self.running = False
        self.bridge.sig_exit.emit()

    def cmd_create_project(self, rest:str):
        tokens = rest.split(maxsplit=1)
        if len(tokens) < 2:
            print("用法: create_project <输出父目录> <插件名称>")
            return
        parent_path, plugin_name = tokens
        base_path = os.path.join(parent_path, plugin_name)
        try:
            os.makedirs(base_path, exist_ok=False)
            plugin_info = {
                "name": plugin_name,
                "version": "1.0.0",
                "description": "",
                "rely_ons": []
            }
            info_path = os.path.join(base_path, "plugin_info.json")
            with open(info_path, "w", encoding="utf-8") as f:
                json.dump(plugin_info, f, indent=4, ensure_ascii=False)
            plugin_py_path = os.path.join(base_path, "plugin.py")
            plugin_template = '''class PluginBase:
    def __init__(self,api,engine,name):
        self.api = api
        self.engine = engine
        self.name = name
    def import_model(self,model_path,name):
        return self.api.import_model(self.name,model_path,name)
    def on_game_load(self):pass
    def on_game_unload(self):pass
    def on_game_start(self):pass
    def on_game_end(self):pass
    def on_game_update(self):pass
    def on_editor_load(self):pass
    def on_editor_unload(self):pass
    def on_editor_start(self):pass
    def on_editor_end(self):pass
    def on_editor_update(self):pass

class Plugin(PluginBase):
    def __init__(self,api,engine,name):
        super().__init__(api,engine,name)
    def on_game_start(self):
        print(f"插件[{self.name}]已启动")
'''
            with open(plugin_py_path, "w", encoding="utf-8") as f:
                f.write(plugin_template)
            abs_path = os.path.abspath(base_path)
            print(f"[成功] 插件脚手架已生成: {abs_path}")
            if sys.platform == "win32":
                os.startfile(abs_path)
        except Exception as e:
            print(f"[错误] create_project失败: {e}")

    def cmd_build_project(self, rest: str):
        tokens = rest.split(maxsplit=1)
        if len(tokens) < 2:
            print("用法: build_project <项目目录> <输出.aoi路径>")
            return
        proj_path, out_aoi = tokens
        ok, msg = self.build_project_core(proj_path, out_aoi)
        print(msg)

    @staticmethod
    def build_project_core(project_path: str, output_aoi: str) -> tuple[bool, str]:
        project_path = os.path.abspath(project_path)
        output_aoi = os.path.abspath(output_aoi)
        if not output_aoi.lower().endswith(".aoi"):
            output_aoi += ".aoi"

        plugin_info_json = os.path.join(project_path, "plugin_info.json")
        plugin_py = os.path.join(project_path, "plugin.py")
        if not os.path.isdir(project_path):
            return False, f"[错误] 项目目录不存在 {project_path}"
        if not os.path.exists(plugin_info_json):
            return False, "[错误] 缺少 plugin_info.json"
        if not os.path.exists(plugin_py):
            return False, "[错误] 缺少 plugin.py"

        tmp_dir = tempfile.TemporaryDirectory()
        tmp_root = tmp_dir.name
        pyc_out = os.path.join(tmp_root, "pyc_out")
        try:
            os.makedirs(pyc_out, exist_ok=True)
            pyc_compiler.compile_dir(project_path, pyc_out)

            pkg_info = {
                "type": "plugin",
                "build_time": f"{datetime.datetime.now().year}/{datetime.datetime.now().month}/{datetime.datetime.now().day}"
            }
            info_json_tmp = os.path.join(pyc_out, "info.json")
            with open(info_json_tmp, "w", encoding="utf-8") as f:
                json.dump(pkg_info, f, indent=4, ensure_ascii=False)

            shutil.copy2(plugin_info_json, os.path.join(pyc_out, "plugin_info.json"))

            with zipfile.ZipFile(output_aoi, "w", zipfile.ZIP_DEFLATED) as zf:
                for root, _, files in os.walk(pyc_out):
                    for fname in files:
                        full = os.path.join(root, fname)
                        arc = os.path.relpath(full, pyc_out)
                        arc = arc.replace(os.sep, "/")
                        zf.write(full, arc)

            folder_to_open = os.path.dirname(output_aoi)
            if sys.platform == "win32":
                os.startfile(folder_to_open)
            return True, f"[成功] 插件构建完成：{output_aoi}"
        except Exception as e:
            return False, f"[构建异常] {str(e)}"
        finally:
            tmp_dir.cleanup()


def set_dark_theme(app:QApplication):
    """仿UnityHub深色主题"""
    dark_palette = QPalette()
    c_bg = QColor(45,45,48)
    c_widget = QColor(60,60,64)
    c_text = QColor(220,220,220)
    c_highlight = QColor(60,120,180)

    dark_palette.setColor(QPalette.Window, c_bg)
    dark_palette.setColor(QPalette.WindowText, c_text)
    dark_palette.setColor(QPalette.Base, c_widget)
    dark_palette.setColor(QPalette.AlternateBase, c_bg)
    dark_palette.setColor(QPalette.ToolTipBase, c_bg)
    dark_palette.setColor(QPalette.ToolTipText, c_text)
    dark_palette.setColor(QPalette.Text, c_text)
    dark_palette.setColor(QPalette.Button, c_widget)
    dark_palette.setColor(QPalette.ButtonText, c_text)
    dark_palette.setColor(QPalette.BrightText, Qt.red)
    dark_palette.setColor(QPalette.Link, c_highlight)
    dark_palette.setColor(QPalette.Highlight, c_highlight)
    dark_palette.setColor(QPalette.HighlightedText, Qt.white)
    app.setPalette(dark_palette)


def main():
    app = QApplication(sys.argv)
    set_dark_theme(app)

    bridge = ConsoleBridge()
    ui_win: AoiStudioPluginHub | None = None
    history = HistoryManager()

    def on_show_ui():
        nonlocal ui_win
        if ui_win is None:
            cli = AoiStudioPluginBuildToolConsole(bridge)
            ui_win = AoiStudioPluginHub(cli, history)
        ui_win.show()
        ui_win.raise_()

    def on_exit():
        nonlocal ui_win
        if ui_win:
            ui_win.close()
        app.quit()

    bridge.sig_show_ui.connect(on_show_ui)
    bridge.sig_exit.connect(on_exit)

    cli = AoiStudioPluginBuildToolConsole(bridge)
    cli_thread = threading.Thread(target=cli.run_loop, daemon=True)
    cli_thread.start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()