import sys
import json
import socket
import time
import threading

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, QLineEdit, QHBoxLayout,
                             QSplitter, QTextEdit, QTabWidget, QLabel, QSpinBox, QListWidget, QListWidgetItem,
                             QGroupBox, QFormLayout)
from PyQt5.QtCore import Qt, QObject, pyqtSignal, QThread, QTimer


class TcpClientWorker(QObject):
    sig_recv_response = pyqtSignal(dict)
    sig_log = pyqtSignal(str)
    sig_conn_lost = pyqtSignal()
    sig_conn_ok = pyqtSignal()

    def __init__(self, host="127.0.0.1", port=8877):
        super().__init__()
        self.host = host
        self.port = port
        self.sock = None
        self._connected = False
        self._alive = False
        self._recv_buf = b""
        self._io_thread = None

        self.ping_timer = QTimer()
        self.ping_timer.setInterval(250)
        self.ping_timer.timeout.connect(self._do_ping)

    @property
    def is_connected(self):
        return self._alive

    def _thread_entry(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(None)
            self.sock.connect((self.host, self.port))
            self._connected = True
            self._alive = True
            self._recv_buf = b""
            self.sig_conn_ok.emit()
            self.sig_log.emit(f"[GUI] 已连接调试服务 {self.host}:{self.port}")
        except Exception as e:
            self.sig_log.emit(f"[GUI] 连接失败: {e}")
            self.sig_conn_lost.emit()
            return

        while self._alive and self.sock is not None:
            try:
                chunk = self.sock.recv(4096)
                if not chunk:
                    break
                self._recv_buf += chunk
                while b"\n" in self._recv_buf:
                    line, self._recv_buf = self._recv_buf.split(b"\n", 1)
                    if not line.strip():
                        continue
                    try:
                        resp = json.loads(line.decode("utf-8"))
                        self.sig_recv_response.emit(resp)
                    except json.JSONDecodeError:
                        self.sig_log.emit(f"[GUI] json解析失败: {line}")
            except OSError:
                break
            except Exception as e:
                self.sig_log.emit(f"[GUI] recv exception {e}")
                break
        self._mark_disconnect()

    def connect_server(self):
        self._io_thread = threading.Thread(target=self._thread_entry, daemon=True)
        self._io_thread.start()

    def _do_ping(self):
        if not self._alive:
            return
        try:
            ping_payload = (json.dumps({"cmd": "ping"}) + "\n").encode("utf-8")
            self.sock.sendall(ping_payload)
            runtime_payload = (json.dumps({"cmd": "get_runtime", "params": {}}) + "\n").encode("utf-8")
            self.sock.sendall(runtime_payload)
        except Exception:
            self._mark_disconnect()

    def _mark_disconnect(self):
        self._alive = False
        self._connected = False
        self.ping_timer.stop()
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None
        self.sig_conn_lost.emit()

    def send_command(self, cmd_obj: dict):
        if not self.is_connected:
            self.sig_log.emit("[GUI] 未连接服务，无法发送指令")
            return
        try:
            payload = (json.dumps(cmd_obj, ensure_ascii=False)+"\n").encode("utf-8")
            self.sock.sendall(payload)
        except Exception as e:
            self.sig_log.emit(f"[GUI] send error: {e}")
            self._mark_disconnect()

    def close_socket(self):
        self._mark_disconnect()


class DebuggerGuiWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AoiStudio 调试器")
        try:
            self.setWindowIcon(QIcon(f"{sys._MEIPASS}/icons/AoiStudio.png"))
        except Exception:
            self.setWindowIcon(QIcon("AoiStudio.png"))
        self.resize(1050, 700)
        self._snapshot = None

        self.tcp_thread = QThread()
        self.tcp_client = TcpClientWorker(host="127.0.0.1", port=8877)
        self.tcp_client.moveToThread(self.tcp_thread)
        self.tcp_thread.started.connect(self.tcp_client.connect_server)
        self.tcp_client.sig_log.connect(self._append_log)
        self.tcp_client.sig_recv_response.connect(self._on_response)
        self.tcp_client.sig_conn_lost.connect(self._on_conn_lost)
        self.tcp_client.sig_conn_ok.connect(self._on_conn_ok)
        self.tcp_client.sig_conn_ok.connect(self.tcp_client.ping_timer.start)
        self.tcp_thread.start()

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        self.conn_status_label = QLabel("🔴 未连接服务器")
        main_layout.addWidget(self.conn_status_label)

        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        btn_layout = QHBoxLayout()
        btn_reset = QPushButton("重置全部状态")
        btn_refresh = QPushButton("手动刷新快照")
        btn_reset.clicked.connect(lambda: self._send_cmd({"cmd": "reset_all", "params": {}}))
        btn_refresh.clicked.connect(lambda: self._send_cmd({"cmd": "get_runtime", "params": {}}))
        btn_layout.addWidget(btn_reset)
        btn_layout.addWidget(btn_refresh)
        left_layout.addLayout(btn_layout)
        left_layout.addStretch()
        splitter.addWidget(left_widget)

        self.tab_widget = QTabWidget()
        splitter.addWidget(self.tab_widget)
        splitter.setSizes([180, 870])

        self._create_tab_scene_readonly()
        self._create_tab_variables()
        self._create_tab_flags()
        self._create_tab_dialogue_history()
        self._create_tab_runtime_preview()

        log_group = QGroupBox("日志 / TCP输出")
        log_layout = QVBoxLayout(log_group)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        main_layout.addWidget(log_group)
        main_layout.setStretch(0, 1)
        main_layout.setStretch(1, 8)
        main_layout.setStretch(2, 2)

    def _create_tab_scene_readonly(self):
        """场景信息：纯只读展示，无任何编辑控件"""
        w = QWidget()
        lay = QFormLayout(w)
        self.tab_widget.addTab(w, "场景信息")

        self.lbl_bg = QLabel("-")
        self.lbl_bgm = QLabel("-")
        lay.addRow("当前背景:", self.lbl_bg)
        lay.addRow("当前BGM:", self.lbl_bgm)

        self.list_scene_char = QListWidget()
        self.list_scene_char.setSelectionMode(QListWidget.NoSelection)
        lay.addRow("场景角色列表", self.list_scene_char)

    def _create_tab_variables(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        self.tab_widget.addTab(w, "好感度变量")
        form = QFormLayout()
        lay.addLayout(form)
        self.le_char_name = QLineEdit()
        self.le_char_name.setPlaceholderText("角色名称，例如：千绘莉")
        self.sp_affect = QSpinBox()
        self.sp_affect.setRange(-999, 999)
        form.addRow("角色名称", self.le_char_name)
        form.addRow("好感度数值", self.sp_affect)
        btn_layout = QHBoxLayout()
        btn_set_aff = QPushButton("设置好感度")
        btn_del_aff = QPushButton("删除该项")
        btn_set_aff.clicked.connect(self._ui_set_affection)
        btn_del_aff.clicked.connect(self._ui_del_affection)
        btn_layout.addWidget(btn_set_aff)
        btn_layout.addWidget(btn_del_aff)
        form.addRow("", btn_layout)
        self.list_affection = QListWidget()
        lay.addWidget(QLabel("characters_affection 列表"))
        lay.addWidget(self.list_affection)

    def _create_tab_flags(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        self.tab_widget.addTab(w, "标记 Flags")
        hlay = QHBoxLayout()
        self.le_flag = QLineEdit()
        self.le_flag.setPlaceholderText("输入标记字符串")
        btn_add_flag = QPushButton("添加")
        btn_remove_flag = QPushButton("删除选中")
        btn_add_flag.clicked.connect(self._ui_add_flag)
        btn_remove_flag.clicked.connect(self._ui_remove_flag)
        hlay.addWidget(self.le_flag)
        hlay.addWidget(btn_add_flag)
        hlay.addWidget(btn_remove_flag)
        lay.addLayout(hlay)
        self.list_flags = QListWidget()
        lay.addWidget(self.list_flags)

    def _create_tab_dialogue_history(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        self.tab_widget.addTab(w, "对话历史")
        self.list_history = QListWidget()
        lay.addWidget(self.list_history)

    def _create_tab_runtime_preview(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        self.tab_widget.addTab(w, "完整运行快照")
        self.text_runtime_preview = QTextEdit()
        self.text_runtime_preview.setReadOnly(True)
        lay.addWidget(self.text_runtime_preview)

    def _send_cmd(self, cmd_obj: dict):
        self.tcp_client.send_command(cmd_obj)

    def _on_response(self, resp: dict):
        if resp.get("reply") == "pong":
            return
        if resp.get("status") == "ok" and "data" in resp:
            self._snapshot = resp["data"]
            self._refresh_ui_from_snapshot()
        self._append_log(f"[RECV] {resp}")

    def _on_conn_ok(self):
        self.conn_status_label.setText("🟢 已连接服务器")

    def _on_conn_lost(self):
        self.conn_status_label.setText("🔴 断开服务器")
        self._append_log("[GUI] 与调试服务断开连接")
        sys.exit()

    def _append_log(self, text: str):
        self.log_text.append(text)

    def _refresh_ui_from_snapshot(self):
        snap = self._snapshot
        if snap is None:
            return

        # 只读场景展示
        self.lbl_bg.setText(snap["scene"]["now_background"])
        self.lbl_bgm.setText(snap["scene"]["bgm"])
        self.list_scene_char.clear()
        for c in snap["scene"]["characters"]:
            QListWidgetItem(f"{c['image_path']} | 位置:{c['position']}", self.list_scene_char)

        # 可修改变量
        self.list_affection.clear()
        for k, v in snap["variables"]["characters_affection"].items():
            QListWidgetItem(f"{k} = {v}", self.list_affection)
        self.list_flags.clear()
        for f in snap["flags"]:
            QListWidgetItem(f, self.list_flags)

        # 只读对话历史
        self.list_history.clear()
        for h in snap["history_text"]:
            spk = h.get("speaker", "")
            txt = h.get("text", "")
            QListWidgetItem(f"[{spk}] {txt}", self.list_history)

        self.text_runtime_preview.setPlainText(json.dumps(snap, ensure_ascii=False, indent=2))

    def _ui_set_affection(self):
        cname = self.le_char_name.text().strip()
        val = self.sp_affect.value()
        if cname:
            self._send_cmd({"cmd": "set_affection", "params": {"char_name": cname, "value": val}})

    def _ui_del_affection(self):
        row = self.list_affection.currentRow()
        if row >= 0:
            txt = self.list_affection.item(row).text()
            cname = txt.split("=")[0].strip()
            self._send_cmd({"cmd": "del_affection", "params": {"char_name": cname}})

    def _ui_add_flag(self):
        f = self.le_flag.text().strip()
        if f:
            self._send_cmd({"cmd": "add_flag", "params": {"flag": f}})
            self.le_flag.clear()

    def _ui_remove_flag(self):
        row = self.list_flags.currentRow()
        if row >= 0:
            txt = self.list_flags.item(row).text()
            self._send_cmd({"cmd": "remove_flag", "params": {"flag": txt}})

    def closeEvent(self, event):
        self.tcp_client.close_socket()
        self.tcp_thread.quit()
        self.tcp_thread.wait()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = DebuggerGuiWindow()
    win.show()
    sys.exit(app.exec_())