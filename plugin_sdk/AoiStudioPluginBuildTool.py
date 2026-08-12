import datetime
import json
import shutil
import sys
import zipfile
import os
import threading
import pyc_compiler
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLineEdit, QTextEdit, QFileDialog, QLabel)
from PyQt5.QtCore import Qt, QObject, pyqtSignal


# 信号桥：子线程(控制台)向主线程发指令，Qt组件禁止跨线程操作
class ConsoleBridge(QObject):
    sig_show_ui = pyqtSignal()
    sig_exit = pyqtSignal()


class AoiStudioPluginBuildToolUI(QMainWindow):
    def __init__(self,console):
        super().__init__()
        self.setWindowTitle("AoiStudio 插件工具")
        self.resize(700, 500)
        self.console = console
        self.init_ui()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        src_layout = QHBoxLayout()
        self.src_edit = QLineEdit()
        self.src_edit.setPlaceholderText("插件源文件夹路径")
        btn_src = QPushButton("选择源目录")
        btn_src.clicked.connect(self.select_src_dir)
        src_layout.addWidget(QLabel("源目录:"))
        src_layout.addWidget(self.src_edit)
        src_layout.addWidget(btn_src)
        layout.addLayout(src_layout)

        out_layout = QHBoxLayout()
        self.out_edit = QLineEdit()
        self.out_edit.setPlaceholderText("输出插件zip文件路径")
        btn_out = QPushButton("选择输出文件")
        btn_out.clicked.connect(self.select_out_file)
        out_layout.addWidget(QLabel("输出文件:"))
        out_layout.addWidget(self.out_edit)
        out_layout.addWidget(btn_out)
        layout.addLayout(out_layout)

        btn_layout = QHBoxLayout()
        self.btn_build = QPushButton("执行打包")
        self.btn_build.clicked.connect(self.do_build)
        self.btn_clear = QPushButton("清空日志")
        self.btn_clear.clicked.connect(lambda: self.log_edit.clear())
        btn_layout.addWidget(self.btn_build)
        btn_layout.addWidget(self.btn_clear)
        layout.addLayout(btn_layout)

        self.log_edit = QTextEdit()
        self.log_edit.setReadOnly(True)
        layout.addWidget(self.log_edit)

    def log(self, msg):
        self.log_edit.append(msg)

    def select_src_dir(self):
        path = QFileDialog.getExistingDirectory(self, "选择插件源文件夹")
        if path:
            self.src_edit.setText(path)

    def select_out_file(self):
        path, _ = QFileDialog.getSaveFileName(self, "保存插件包", "", "Zip文件(*.zip)")
        if path:
            self.out_edit.setText(path)

    def do_build(self):
        src_dir = self.src_edit.text().strip()
        out_path = self.out_edit.text().strip()
        if not src_dir or not out_path:
            self.log("[错误] 请填写源目录和输出路径")
            return
        try:
            self.log(f"开始打包: {src_dir} -> {out_path}")
            with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for root, dirs, files in os.walk(src_dir):
                    for name in files:
                        full_path = os.path.join(root, name)
                        arcname = os.path.relpath(full_path, src_dir)
                        zf.write(full_path, arcname)
            self.log("[成功] 插件打包完成")
        except Exception as e:
            self.log(f"[异常] {str(e)}")


class AoiStudioPluginBuildToolConsole:
    def __init__(self, bridge: ConsoleBridge):
        self.bridge = bridge
        self.commands = {
            "exit": self.cmd_exit,
            "show_ui": self.cmd_show_ui,
            "create_project":self.create_project,
            "build_project":self.build_project
        }
        self.running = True

    def run_loop(self):
        print("AoiStudio PluginBuildTool Console")
        print("可用命令: exit, show_ui")
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
            if cmd in self.commands:
                args = parts[1:] if len(parts)>1 else []
                args = args[0].split(maxsplit=99999999)
                self.commands[cmd](args)
            else:
                print(f"未知命令: {cmd}。可用：exit, show_ui")

    def cmd_show_ui(self, args):
        print("[控制台] 请求打开GUI窗口")
        self.bridge.sig_show_ui.emit()

    def cmd_exit(self, args):
        print("[控制台] 收到exit命令，准备退出")
        self.running = False
        self.bridge.sig_exit.emit()

    def create_project(self,args):
        if not len(args) > 1:
            print("Usage: project_path project_name ")
            return

        path = args[0]
        name = args[1]
        base_path = f"{path}/{name}"
        print(base_path)
        os.mkdir(f"{base_path}")
        plugin_info_json = {
            "name":f"{name}",
            "version":"1.0.0",
            "description":"plugin_description",
            "rely_ons": [
            ]
        }
        with open(f"{base_path}/plugin_info.json" ,"w",encoding="utf-8") as f:
            json.dump(plugin_info_json,f,indent=4)
        with open(f"{base_path}/plugin.py","w",encoding="utf-8") as f:
            f.write(
                """
                class PluginBase:
    
    #插件基类
    #插件主逻辑在下面的Plugin类里面写，不要所有逻辑堆在基类里，不然你懂得
    
    def __init__(self,api,engine,name):
        self.api = api
        self.engine = engine
        self.name = name

    # 方法封装

    def import_model(self,model_path,name):
        
        #导入模块
        
        return self.api.import_model(self.name,model_path,name)

    # 事件回调

    def on_game_load(self):
        
        #插件加载时调用
        
        pass

    def on_game_unload(self):
        
        #插件卸载时调用
        
        pass

    def on_game_start(self):
        
        #游戏开始时调用
        
        pass

    def on_game_end(self):
        
        #游戏结束时调用
        
        pass

    def on_editor_load(self):
        
        #编辑器加载时调用
        
        pass

    def on_editor_unload(self):
        
        #编辑器卸载时调用
        
        pass

    def on_editor_start(self):
        
        #编辑器开始时调用
        
        pass

    def on_editor_end(self):
        
        #编辑器结束时调用
        
        pass

    def on_game_update(self):
        
        #游戏更新时调用
        
        pass

    def on_editor_update(self):
        
        #编辑器更新时调用
        
        pass



class Plugin(PluginBase):
    
    #插件类
    #主逻辑在这写
    
    def __init__(self,api,engine,name):
        super().__init__(api,engine,name)
            """
                    )
            # 资源管理器打开base_path目录
            base_path = os.path.abspath(base_path)
            os.startfile(base_path)

    def build_project(self,args):
        if not len(args) > 1:
            print("Usage: project_path output_path ")
            return
        project_path = args[0]
        output_path = args[1]
        project_path = os.path.abspath(project_path)
        output_path = os.path.abspath(output_path)
        if os.path.exists(project_path):
            if os.path.exists(project_path + "\\plugin_info.json"):
                if os.path.exists(project_path + "\\plugin.py"):
                    with open(f"{project_path}\\info.json","w",encoding="utf-8") as f:
                        package_info = {
                            "type":"plugin",
                            "build_time":f"{datetime.datetime.now().year}/{datetime.datetime.now().month}/{datetime.datetime.now().day}"
                        }
                        json.dump(package_info,f,indent=4)
                    os.mkdir("pyc_tmp")
                    pyc_compiler.compile_dir(project_path, "pyc_tmp")
                    with zipfile.ZipFile(output_path.replace(".aoi","")+".aoi", "w", zipfile.ZIP_DEFLATED) as zf:
                        zf.write(f"{project_path}\\plugin_info.json", "plugin_info.json")
                        zf.write(f"{project_path}\\info.json", "info.json")
                        # 把pyc_tmp的.pyc加目录文件打包到压缩包中
                        for root,dirs,files in os.walk("pyc_tmp"):
                            for name in files:
                                if os.path.exists(f"pyc_tmp/{name}"):
                                    zf.write(f"pyc_tmp/{name}", f"{name}")
                            for dir in dirs:
                                print(root+dir)
                                for root,dirs,files in os.walk(root+"/" + dir):
                                    for name in files:
                                        zf.write(f"pyc_tmp/{dir}/{name}", f"{dir}/{name}")


                    os.remove(f"{project_path}\\info.json")
                    shutil.rmtree("pyc_tmp")
                    print(f"[成功] 插件打包完成: {output_path}.aoi")
                    # 将output_path改为上一级目录的路径
                    output_path_ = os.path.dirname(output_path)
                    # 启动文件管理器
                    os.startfile(output_path_)
                    return
        print("[错误] 插件打包失败")

def main():
    app = QApplication(sys.argv)
    bridge = ConsoleBridge()
    ui_win: AoiStudioPluginBuildToolUI | None = None

    def on_show_ui():
        nonlocal ui_win
        if ui_win is None:
            ui_win = AoiStudioPluginBuildToolUI(cli)
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
    # input阻塞放到后台线程，主线程留给Qt事件循环
    cli_thread = threading.Thread(target=cli.run_loop, daemon=True)
    cli_thread.start()

    # 主线跑Qt事件循环，窗口不会未响应！
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()