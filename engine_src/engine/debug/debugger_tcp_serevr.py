import json
import socket
import threading
import copy
import time


class DebugRuntimeState:
    def __init__(self,engine):
        self.dialogue_file_path = ""
        self.dialogue_index = 0
        self.characters_affection = {}
        self.flags = []
        self.now_background = ""
        self.scene_characters = []
        self.bgm = "None"
        self.history_text = []
        self.engine = engine

    def reset(self):
        self.dialogue_file_path = ""
        self.dialogue_index = 0
        self.characters_affection.clear()
        self.flags.clear()
        self.now_background = ""
        self.scene_characters.clear()
        self.bgm = "None"
        self.history_text.clear()

    def get_runtime_dict(self):
        return {
            "dialogue": {"file_path": self.dialogue_file_path, "index": self.dialogue_index},
            "variables": {"characters_affection": copy.deepcopy(self.characters_affection)},
            "flags": list(copy.deepcopy(self.flags)),
            "scene": {
                "now_background": self.now_background,
                "characters": copy.deepcopy(self.scene_characters),
                "bgm": self.bgm
            },
            "history_text": copy.deepcopy(self.history_text)
        }

    def change(self):
        """把state副本状态写回真实引擎对象，目前只同步dialog层；scene相关字段这里还没做同步"""
        print("[DEBUG_SERVER] runtime state changed")
        self.engine.dialog.characters_affection = self.characters_affection.copy()
        self.engine.dialog.flags = self.flags.copy()
        # 注意：now_background / scene_characters / bgm / dialogue指针 / history 目前不会同步到engine！
        # 如果想要GUI调试器真正修改画面，需要在这里补充对 self.engine.scene 的修改逻辑

    def get_state(self):
        # 从真实引擎读取最新状态，覆盖到state副本
        self.dialogue_file_path = self.engine.dialog.dialogue_file_path
        self.dialogue_index = self.engine.dialog.current_dialogue_index
        self.characters_affection = self.engine.dialog.characters_affection.copy()
        self.flags = self.engine.dialog.flags.copy()
        if len(self.engine.scene.backgrounds) > 0:
            self.now_background = self.engine.scene.backgrounds[0].image_path
        else:
            self.now_background = "None"
        if len(self.engine.scene.bgm) > 0:
            self.bgm = self.engine.scene.bgm[0].path
        else:
            self.bgm = "None"
        self.history_text = self.engine.dialog.history_text
        self.scene_characters.clear()
        for chr in self.engine.scene.characters:
            self.scene_characters.append({"image_path": chr.image_path, "position": chr.logic_target_position})


class DebuggerAPI:
    def __init__(self, state: DebugRuntimeState, server_ref):
        self.state = state
        self.server = server_ref
        self.engine = state.engine  # 从 state 中获取 engine 引用

    def set_background(self, bg_path: str):
        self.state.now_background = bg_path
        self.state.change()
        return {"ok": True}

    def set_bgm(self, bgm_name: str):
        self.state.bgm = bgm_name
        self.state.change()
        return {"ok": True}

    def add_scene_char(self, image_path: str, pos: list):
        self.state.scene_characters.append({"image_path": image_path, "position": pos})
        self.state.change()
        return {"ok": True}

    def remove_scene_char(self, index: int):
        if 0 <= index < len(self.state.scene_characters):
            self.state.scene_characters.pop(index)
            self.state.change()   # 修复：成功删除也要调用change
            return {"ok": True}
        return {"ok": False, "msg": "索引超出范围"}

    def set_affection(self, char_name: str, value: int):
        self.state.characters_affection[char_name] = value
        self.state.change()
        return {"ok": True}

    def del_affection(self, char_name: str):
        if char_name in self.state.characters_affection:
            del self.state.characters_affection[char_name]
        self.state.change()
        return {"ok": True}

    def add_flag(self, flag: str):
        if flag not in self.state.flags:
            self.state.flags.append(flag)
        self.state.change()
        return {"ok": True}

    def remove_flag(self, flag: str):
        if flag in self.state.flags:
            self.state.flags.remove(flag)
        self.state.change()
        return {"ok": True}

    def set_dialogue_ptr(self, file_path: str, index: int):
        self.state.dialogue_file_path = file_path
        self.state.dialogue_index = index
        self.state.change()
        return {"ok": True}

    def append_history(self, hist_item: dict):
        self.state.history_text.append(hist_item)
        self.state.change()
        return {"ok": True}

    def clear_history(self):
        self.state.history_text.clear()
        self.state.change()
        return {"ok": True}

    def get_runtime_snapshot(self):
        self.state.get_state()
        # 删掉错误的 self.state.change()，读状态不需要写回引擎
        return {"status": "ok", "data": self.state.get_runtime_dict()}

    def get_hierarchy(self):
        """获取 GameObject 层级结构"""
        objects = []
        for go in self.engine.g_o_manager.game_objects:
            obj_info = {
                "name": go.name,
                "active": go.active,
                "components": [c["name"] for c in go.components]
            }
            objects.append(obj_info)
        return {"status": "ok", "objects": objects}

    def get_component_detail(self, go_name: str, comp_name: str):
        """获取指定对象的组件详情"""
        go = self.engine.g_o_manager.get_game_object(go_name)
        if not go:
            return {"status": "error", "msg": f"GameObject '{go_name}' not found"}
        
        comp_data = go.get_component(comp_name)
        
        # 兼容处理：如果返回的是字典，按原逻辑；如果直接是对象，则直接使用
        if isinstance(comp_data, dict):
            comp_instance = comp_data.get("object")
            is_active = comp_data.get("active", True)
        else:
            comp_instance = comp_data
            # 尝试从 GameObject 的 components 列表中查找激活状态
            is_active = True
            for c in go.components:
                if c["name"] == comp_name:
                    is_active = c["active"]
                    break

        if not comp_instance:
            return {"status": "error", "msg": f"Component '{comp_name}' not found on '{go_name}'"}
        
        detail = {
            "name": comp_name,
            "active": is_active,
            "properties": comp_instance.get_save_data(),
            "type": type(comp_instance).__name__
        }
        return {"status": "ok", "detail": detail}

    def reset_all(self):
        self.state.reset()
        self.state.change()
        return {"ok": True}

    def dispatch_command(self, cmd_obj: dict):
        cmd = cmd_obj.get("cmd", "")
        params = cmd_obj.get("params", {})
        self.state.get_state()
        try:
            if cmd == "ping":
                return {"status": "ok", "reply": "pong"}
            elif cmd == "get_client_list":
                return {"status":"ok", "clients": self.server.get_online_clients()}
            elif cmd == "set_background":
                return self.set_background(**params)
            elif cmd == "set_bgm":
                return self.set_bgm(**params)
            elif cmd == "add_scene_char":
                return self.add_scene_char(**params)
            elif cmd == "remove_scene_char":
                return self.remove_scene_char(**params)
            elif cmd == "set_affection":
                return self.set_affection(**params)
            elif cmd == "del_affection":
                return self.del_affection(**params)
            elif cmd == "add_flag":
                return self.add_flag(**params)
            elif cmd == "remove_flag":
                return self.remove_flag(**params)
            elif cmd == "set_dialogue_ptr":
                return self.set_dialogue_ptr(**params)
            elif cmd == "append_history":
                return self.append_history(**params)
            elif cmd == "clear_history":
                return self.clear_history()
            elif cmd == "get_runtime":
                return self.get_runtime_snapshot()
            elif cmd == "inspector_get_hierarchy":
                return self.get_hierarchy()
            elif cmd == "inspector_get_component":
                # 兼容两种传参方式：直接在根目录或在 params 中
                go_name = cmd_obj.get("go_name") or params.get("go_name")
                comp_name = cmd_obj.get("comp_name") or params.get("comp_name")
                
                if not go_name or not comp_name:
                    return {"status": "error", "msg": "missing go_name or comp_name"}
                    
                return self.get_component_detail(go_name, comp_name)
            elif cmd == "reset_all":
                return self.reset_all()
            else:
                return {"status": "error", "msg": f"unknown cmd:{cmd}"}

        except Exception as e:
            return {"status": "error", "msg": str(e)}


class ClientSession:
    def __init__(self, conn: socket.socket, addr):
        self.conn = conn
        self.addr = addr
        self.last_active = time.time()
        self.is_invalid = False


class TcpDebugServer:
    def __init__(self, api: DebuggerAPI, host="127.0.0.1", port=8877):
        self.api = api
        self.host = host
        self.port = port
        self._running = False
        self.sock = None
        self.sessions: list[ClientSession] = []
        self._lock = threading.Lock()
        self.CLIENT_TIMEOUT = 5.0

    def start(self):
        self._running = True
        clean_th = threading.Thread(target=self._clean_loop, daemon=True)
        clean_th.start()

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.host, self.port))
        self.sock.listen(4)
        print(f"[DEBUG_SERVER] Debug server listening {self.host}:{self.port}")
        while self._running:
            try:
                conn, addr = self.sock.accept()
                sess = ClientSession(conn, addr)
                with self._lock:
                    self.sessions.append(sess)
                print(f"[DEBUG_SERVER] new client connect {addr}, online={len(self.sessions)}")
                t = threading.Thread(target=self._client_handle, args=(sess,), daemon=True)
                t.start()
            except Exception:
                break

    def stop(self):
        self._running = False
        if self.sock:
            self.sock.close()
        with self._lock:
            for s in self.sessions:
                try:
                    s.conn.close()
                except Exception:
                    pass
            self.sessions.clear()
        print("[DEBUG_SERVER] TcpDebugServer stopped")

    def _clean_loop(self):
        while self._running:
            time.sleep(1.0)
            now = time.time()
            to_remove = []
            with self._lock:
                for sess in self.sessions:
                    if now - sess.last_active > self.CLIENT_TIMEOUT:
                        sess.is_invalid = True
                        to_remove.append(sess)
                for s in to_remove:
                    try:
                        s.conn.close()
                    except Exception:
                        pass
                    self.sessions.remove(s)
                    print(f"[DEBUG_SERVER] client timeout disconnect {s.addr}, online={len(self.sessions)}")

    def get_online_clients(self):
        with self._lock:
            return [s.addr for s in self.sessions]

    def _client_handle(self, sess: ClientSession):
        conn = sess.conn
        addr = sess.addr
        buf = b""
        with conn:
            while True:
                try:
                    r = conn.recv(4096)
                    if not r:
                        break
                    buf += r
                    sess.last_active = time.time()
                    while b"\n" in buf:
                        line, buf = buf.split(b"\n", 1)
                        try:
                            j = json.loads(line.decode("utf-8"))
                            #print(f"[DEBUG_SERVER][{addr}] recv: {j}")
                            res = self.api.dispatch_command(j)
                            try:
                                out = (json.dumps(res, ensure_ascii=False, default=str) + "\n").encode("utf-8")
                                conn.sendall(out)
                            except Exception as se:
                                # 如果序列化失败，发送错误信息而不是直接断开
                                err_msg = {"status": "error", "msg": f"serialization error: {str(se)}"}
                                conn.sendall((json.dumps(err_msg) + "\n").encode("utf-8"))
                        except json.JSONDecodeError:
                            err = json.dumps({"status":"error","msg":"json parse fail"})+"\n"
                            conn.sendall(err.encode())
                except OSError as e:
                    if e.winerror != 10053:
                        print(f"[DEBUG_SERVER][{addr}] exception: {e}")
                    break
                except Exception as e:
                    print(f"[DEBUG_SERVER][{addr}] exception: {e}")
                    break
        with self._lock:
            if not sess.is_invalid and sess in self.sessions:
                self.sessions.remove(sess)
        if not sess.is_invalid:
            print(f"[DEBUG_SERVER] client closed {addr}, online={len(self.sessions)}")


class DebugServerMain:
    def __init__(self,engine):
        self.state = DebugRuntimeState(engine)
        self.api = DebuggerAPI(self.state, None)
        self.server = TcpDebugServer(self.api, host="127.0.0.1", port=8877)
        self.api.server = self.server

    def start(self):
        try:
            self.server.start()
        except KeyboardInterrupt:
            self.server.stop()
            print("[DEBUG_SERVER] exited")

    def stop(self):
        self.server.stop()
        print("[DEBUG_SERVER] exited")