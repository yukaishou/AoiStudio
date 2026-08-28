import sys
import json

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, QLineEdit, QHBoxLayout,
                             QSplitter, QTextEdit, QTabWidget, QLabel, QSpinBox, QListWidget, QListWidgetItem,
                             QGroupBox, QFormLayout, QMessageBox)
from PySide6.QtCore import Qt, QObject, Signal, QThread, QTimer, QMutex, QMutexLocker
from PySide6.QtNetwork import QTcpSocket, QAbstractSocket


class TcpClientWorker(QObject):
    sig_recv_response = Signal(dict)
    sig_log = Signal(str)
    sig_conn_lost = Signal()
    sig_conn_ok = Signal()
    sig_quit_app = Signal()

    def __init__(self):
        super().__init__()
        self.host = "127.0.0.1"
        self.port = 8877
        self.sock: QTcpSocket = None
        self._mutex = QMutex()
        self._alive = False
        self._recv_buf = b""

        # 是否曾经成功建立过连接
        self._has_ever_connected = False

        self.ping_timer = QTimer(self)
        self.ping_timer.setInterval(1000)
        self.ping_timer.timeout.connect(self._do_ping)

        self.retry_timer = QTimer(self)
        self.retry_timer.setInterval(2500)
        self.retry_timer.timeout.connect(self._try_reconnect)
        self.retry_max_count = 5
        self.retry_counter = 0

    @property
    def is_connected(self):
        with QMutexLocker(self._mutex):
            return self._alive

    def connect_server(self):
        self.sock = QTcpSocket(self)
        self.sock.connected.connect(self._on_socket_connected)
        self.sock.disconnected.connect(self._on_socket_disconnected)
        self.sock.readyRead.connect(self._on_socket_read)
        self.sock.errorOccurred.connect(self._on_socket_error)
        self._recv_buf = b""
        self.sock.connectToHost(self.host, self.port)

    def _on_socket_connected(self):
        with QMutexLocker(self._mutex):
            self._alive = True
        self.retry_timer.stop()
        self.retry_counter = 0
        self._has_ever_connected = True
        self.sig_conn_ok.emit()
        self.sig_log.emit(f"[GUI] 已连接本地调试服务 {self.host}:{self.port}")

    def _on_socket_disconnected(self):
        self.sig_log.emit("[GUI] socket断开事件")
        if not self._has_ever_connected:
            # 启动阶段：从未连上，允许重试
            self._handle_startup_fail()
        else:
            # 已经成功连接过，服务器断开 → 直接退出，不重试
            self.sig_log.emit("[GUI] 服务器主动关闭连接，准备退出")
            self._clean_socket()
            self.sig_quit_app.emit()

    def _on_socket_error(self, err):
        self.sig_log.emit(f"[GUI] socket错误: {self.sock.errorString()}")
        if not self._has_ever_connected:
            # 启动阶段连接失败，执行重试逻辑
            self._handle_startup_fail()
        else:
            # 运行时出错断开，直接退出
            self.sig_log.emit("[GUI] 运行时连接异常，准备退出")
            self._clean_socket()
            self.sig_quit_app.emit()

    def _on_socket_read(self):
        data = self.sock.readAll().data()
        self._recv_buf += data
        while b"\n" in self._recv_buf:
            line, self._recv_buf = self._recv_buf.split(b"\n", 1)
            if not line.strip():
                continue
            try:
                resp = json.loads(line.decode("utf-8"))
                self.sig_recv_response.emit(resp)
            except json.JSONDecodeError:
                self.sig_log.emit(f"[GUI] json解析失败: {line}")

    def _do_ping(self):
        if not self.is_connected:
            return
        try:
            self._send_raw({"cmd": "ping"})
            self._send_raw({"cmd": "get_runtime", "params": {}})
        except Exception:
            self.sig_log.emit("[GUI] ping发送失败，连接失效，准备退出")
            self._clean_socket()
            self.sig_quit_app.emit()

    def _send_raw(self, cmd_obj: dict):
        payload = (json.dumps(cmd_obj, ensure_ascii=False) + "\n").encode("utf-8")
        if self.sock and self.sock.state() == QAbstractSocket.SocketState.ConnectedState:
            self.sock.write(payload)
            self.sock.flush()

    def send_command(self, cmd_obj: dict):
        if not self.is_connected:
            self.sig_log.emit("[GUI] 未连接本地服务，无法发送指令")
            return
        try:
            self._send_raw(cmd_obj)
        except Exception as e:
            self.sig_log.emit(f"[GUI] send error: {e}")
            self._clean_socket()
            self.sig_quit_app.emit()

    def _clean_socket(self):
        """清理socket，不处理重试"""
        with QMutexLocker(self._mutex):
            self._alive = False
        self.ping_timer.stop()
        self.retry_timer.stop()
        if self.sock:
            self.sock.disconnectFromHost()
            #self.sock.deleteLater()
            self.sock = None
        self.sig_conn_lost.emit()

    def _handle_startup_fail(self):
        """只用于启动阶段（_has_ever_connected=False）的连接失败，做重试计数"""
        self._clean_socket()
        if self.retry_counter < self.retry_max_count:
            self.retry_counter += 1
            remain = self.retry_max_count - self.retry_counter
            self.sig_log.emit(f"[GUI] 2.5s后尝试初次连接，剩余重试:{remain}")
            self.retry_timer.start()
        else:
            self.sig_log.emit("[GUI] 启动阶段5次尝试全部失败，准备退出调试器")
            self.sig_quit_app.emit()

    def _try_reconnect(self):
        if self._has_ever_connected:
            self.retry_timer.stop()
            return
        self.connect_server()

    def close_socket(self):
        """用户手动关闭窗口"""
        self.retry_timer.stop()
        with QMutexLocker(self._mutex):
            self._alive = False
        self.ping_timer.stop()
        if self.sock:
            self.sock.disconnectFromHost()

class DebuggerGuiWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AoiStudio 本地调试器")
        self.resize(1050, 700)
        self._snapshot = None
        self._last_snapshot_raw = ""

        self.tcp_thread = QThread()
        self.tcp_client = TcpClientWorker()
        self.tcp_client.moveToThread(self.tcp_thread)
        self.tcp_thread.started.connect(self.tcp_client.connect_server)

        self.tcp_client.sig_log.connect(self._append_log)
        self.tcp_client.sig_recv_response.connect(self._on_response)
        self.tcp_client.sig_conn_lost.connect(self._on_conn_lost)
        self.tcp_client.sig_conn_ok.connect(self._on_conn_ok)
        self.tcp_client.sig_conn_ok.connect(self.tcp_client.ping_timer.start)
        self.tcp_client.sig_quit_app.connect(self._on_quit_request)

        self.tcp_thread.start()

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        self.conn_status_label = QLabel("🔴 未连接本地服务器")
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

    def _on_quit_request(self):
        #QMessageBox.warning(self, "调试器退出", "连接条件不满足，调试器即将关闭")
        self.close()

    def _create_tab_scene_readonly(self):
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
        self._append_log(f"[RECV] {resp}")

        if resp.get("status") == "ok" and "data" in resp:
            new_snap = resp["data"]
            new_raw = json.dumps(new_snap, ensure_ascii=False, sort_keys=True)
            if new_raw != self._last_snapshot_raw:
                self._snapshot = new_snap
                self._last_snapshot_raw = new_raw
                self._refresh_ui_from_snapshot()

    def _on_conn_ok(self):
        self.conn_status_label.setText("🟢 已连接本地服务器")

    def _on_conn_lost(self):
        self.conn_status_label.setText("🔴 断开本地服务器")
        self._append_log("[GUI] 与本地调试服务断开连接")

    def _append_log(self, text: str):
        self.log_text.append(text)

    def _refresh_ui_from_snapshot(self):
        snap = self._snapshot
        if snap is None:
            return

        self.lbl_bg.setText(snap["scene"]["now_background"])
        self.lbl_bgm.setText(snap["scene"]["bgm"])
        self.list_scene_char.clear()
        for c in snap["scene"]["characters"]:
            QListWidgetItem(f"{c['image_path']} | 位置:{c['position']}", self.list_scene_char)

        self.list_affection.clear()
        for k, v in snap["variables"]["characters_affection"].items():
            QListWidgetItem(f"{k} = {v}", self.list_affection)
        self.list_flags.clear()
        for f in snap["flags"]:
            QListWidgetItem(f, self.list_flags)

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
        self.tcp_thread.wait(2000)
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = DebuggerGuiWindow()
    win.show()
    sys.exit(app.exec())