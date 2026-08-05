import json
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QFormLayout,
                             QLineEdit, QSpinBox, QCheckBox, QPushButton,
                             QHBoxLayout, QVBoxLayout, QFileDialog, QMessageBox)
from PyQt5.QtCore import Qt

# ===================== 配置文件路径常量（请勿修改） =====================
GAME_CONFIG_PATH = "config/game.json"
DIALOG_CONFIG_PATH = "config/dialog.json"
# =======================================================================

# 默认配置模板
DEFAULT_GAME_CONFIG = {
    "name": "AoiStudio",
    "game_size": [1200, 768],
    "splash_screen": True,
    "show_studio_logo": True,
    "show_made_with_engine": True
}

DEFAULT_DIALOG_CONFIG = {
    "startFrom": "file:dialogs/dialog_editor_test.json",
    "startBG": "file:backgrounds/WebPicture_1.png ",
    "startBGM": "None"
}


class ProjectConfigEditor(QMainWindow):
    """项目配置编辑器窗口，可直接在其他PyQt程序中实例化show()"""
    def __init__(self, parent=None,project_path=None):
        super().__init__(parent)
        self.setWindowTitle("项目设置")
        self.resize(620, 460)

        # 内存缓存配置
        self.game_config = {}
        self.dialog_config = {}
        self.project_path = project_path or os.getcwd()

        self.init_ui()
        self.load_all_config()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # ========== Game 配置区域 ==========
        form_game = QFormLayout()
        self.edit_game_name = QLineEdit()
        self.spin_width = QSpinBox()
        self.spin_width.setRange(320, 4096)
        self.spin_height = QSpinBox()
        self.spin_height.setRange(240, 2160)
        self.check_splash = QCheckBox("启用")
        self.check_logo = QCheckBox("启用")
        self.check_made_engine = QCheckBox("启用")

        form_game.addRow("项目名称(name):", self.edit_game_name)
        size_layout = QHBoxLayout()
        size_layout.addWidget(self.spin_width)
        size_layout.addWidget(QLineEdit("×"))
        size_layout.addWidget(self.spin_height)
        form_game.addRow("窗口尺寸(game_size):", size_layout)
        form_game.addRow("启动画面(splash_screen):", self.check_splash)
        form_game.addRow("显示工作室logo(show_studio_logo):", self.check_logo)
        form_game.addRow("显示引擎标识(show_made_with_engine):", self.check_made_engine)

        # ========== Dialog 配置区域 ==========
        form_dialog = QFormLayout()
        self.edit_start_from = QLineEdit()
        self.edit_start_bg = QLineEdit()
        self.edit_start_bgm = QLineEdit()

        form_dialog.addRow("初始对话文件(startFrom):", self.edit_start_from)
        form_dialog.addRow("初始背景图(startBG):", self.edit_start_bg)
        form_dialog.addRow("初始背景音乐(startBGM):", self.edit_start_bgm)

        # 按钮区
        btn_layout = QHBoxLayout()
        self.btn_load = QPushButton("重新加载配置")
        self.btn_save = QPushButton("保存配置")
        self.btn_reset = QPushButton("恢复默认值")
        btn_layout.addWidget(self.btn_load)
        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_reset)

        # 组装布局
        main_layout.addLayout(form_game)
        main_layout.addSpacing(16)
        main_layout.addLayout(form_dialog)
        main_layout.addStretch()
        main_layout.addLayout(btn_layout)

        # 绑定信号
        self.btn_load.clicked.connect(self.load_all_config)
        self.btn_save.clicked.connect(self.save_all_config)
        self.btn_reset.clicked.connect(self.restore_default)

    def load_json(self, filepath, default_cfg):
        """读取JSON，不存在/损坏返回默认配置"""
        if not os.path.exists(filepath):
            return default_cfg.copy()
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            QMessageBox.warning(self, "警告", f"{filepath} 读取失败，使用默认配置！")
            return default_cfg.copy()

    def save_json(self, filepath, data):
        """写入JSON文件"""
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"{filepath}\n{str(e)}")
            return False

    def load_all_config(self):
        self.game_config = self.load_json(f"{self.project_path}/{GAME_CONFIG_PATH}", DEFAULT_GAME_CONFIG)
        self.dialog_config = self.load_json(f"{self.project_path}/{DIALOG_CONFIG_PATH}", DEFAULT_DIALOG_CONFIG)
        self.refresh_ui_from_config()

    def refresh_ui_from_config(self):
        # Game配置写入UI
        self.edit_game_name.setText(self.game_config.get("name", ""))
        w, h = self.game_config.get("game_size", [1200, 768])
        self.spin_width.setValue(w)
        self.spin_height.setValue(h)
        self.check_splash.setChecked(self.game_config.get("splash_screen", True))
        self.check_logo.setChecked(self.game_config.get("show_studio_logo", True))
        self.check_made_engine.setChecked(self.game_config.get("show_made_with_engine", True))

        # Dialog配置写入UI
        self.edit_start_from.setText(self.dialog_config.get("startFrom", ""))
        self.edit_start_bg.setText(self.dialog_config.get("startBG", ""))
        self.edit_start_bgm.setText(self.dialog_config.get("startBGM", ""))

    def collect_ui_to_config(self):
        """从界面读取数据到配置字典"""
        # Game
        self.game_config["name"] = self.edit_game_name.text()
        self.game_config["game_size"] = [self.spin_width.value(), self.spin_height.value()]
        self.game_config["splash_screen"] = self.check_splash.isChecked()
        self.game_config["show_studio_logo"] = self.check_logo.isChecked()
        self.game_config["show_made_with_engine"] = self.check_made_engine.isChecked()

        # Dialog
        self.dialog_config["startFrom"] = self.edit_start_from.text()
        self.dialog_config["startBG"] = self.edit_start_bg.text()
        self.dialog_config["startBGM"] = self.edit_start_bgm.text()

    def save_all_config(self):
        self.collect_ui_to_config()
        ok1 = self.save_json(f"{self.project_path}/{GAME_CONFIG_PATH}", self.game_config)
        ok2 = self.save_json(f"{self.project_path}/{DIALOG_CONFIG_PATH}", self.dialog_config)
        if ok1 and ok2:
            QMessageBox.information(self, "成功", "所有配置已保存！")

    def restore_default(self):
        reply = QMessageBox.question(self, "确认", "确定要恢复全部默认配置吗？当前修改会丢失！")
        if reply == QMessageBox.Yes:
            self.game_config = DEFAULT_GAME_CONFIG.copy()
            self.dialog_config = DEFAULT_DIALOG_CONFIG.copy()
            self.refresh_ui_from_config()

# ==================== 调用示例 ====================
if __name__ == "__main__":
    app = QApplication([])
    window = ProjectConfigEditor()
    window.show()
    app.exec_()

# ==================== 在你现有程序中如何调用 ====================
"""
# 在你的其他PyQt窗口内，点击按钮弹出编辑器示例
def open_config_editor():
    editor = ProjectConfigEditor(self)
    # 模态窗口（阻塞）
    # editor.exec_()
    # 非模态窗口（不阻塞主线程，推荐）
    editor.show()
"""