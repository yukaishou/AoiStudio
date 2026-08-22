import tkinter as tk
from tkinter import ttk
import subprocess
import os
import sys
import urllib.parse
import webbrowser
import hashlib


class BugReporter:
    def __init__(self):
        self.enable = os.getenv("AUTO_REPORT_BUG", "1") == "1"
        self.repo_slug = "yukaishou/AoiStudio"
        self._reported = set()

    def open_github_issue(self, title: str, body: str):
        """
        外部已经构建好标题、正文字符串，直接传入
        :param title: issue标题字符串
        :param body: issue完整body字符串
        """
        if not self.enable:
            return

        # 简单去重：用标题+body前200字符做指纹
        fp_raw = f"{title}:{body[:200]}"
        fp = hashlib.md5(fp_raw.encode("utf-8")).hexdigest()
        if fp in self._reported:
            return
        self._reported.add(fp)

        base_url = f"https://github.com/{self.repo_slug}/issues/new"
        params = {
            "title": title,
            "body": body
        }
        query = urllib.parse.urlencode(params)
        final_url = f"{base_url}?{query}"

        print("\n======== 打开GitHub Issue编辑页面 ========")
        print(f"仓库: {self.repo_slug}")
        webbrowser.open(final_url)


reporter = BugReporter()


def play_crash_sound():
    """播放跨平台崩溃提示音"""
    try:
        if sys.platform == "win32":
            # Windows：系统错误提示音（MessageBeep）
            import winsound
            winsound.MessageBeep(winsound.MB_ICONHAND)  # 错误/停止音
        elif sys.platform == "darwin":
            # MacOS：播放系统错误提示音 Sosumi
            subprocess.run(
                ["afplay", "/System/Library/Sounds/Sosumi.aiff"],
                check=False,
                capture_output=True
            )
        elif sys.platform.startswith("linux"):
            # Linux：优先用 paplay（PulseAudio，主流桌面）， fallback 到 aplay
            try:
                subprocess.run(
                    ["paplay", "/usr/share/sounds/freedesktop/stereo/dialog-error.oga"],
                    check=False,
                    capture_output=True
                )
            except FileNotFoundError:
                # 备选：播放终端 BEL 蜂鸣（如果系统开启）
                print("\a", end="", flush=True)
    except Exception:
        # 任何播放失败都静默，不影响崩溃报告
        pass
class UE4LikeErrorWindow:
    def __init__(self, root,error_msg):
        play_crash_sound()
        self.is_editor = False
        self.root = root
        self.root.title("AoiStudio --- EngineError")
        # 窗口大小
        self.root.geometry("950x700")
        # 窗口图标
        try:
            self.root.iconbitmap("icons/Engine.png")
            # 顶部标题标签
            title_label = tk.Label(
                root,
                text="Engine have problem , please copy error massage to send developer",
                bg="#ffffff",
                fg="#d02020",
                font=("Microsoft YaHei", 12, "bold")
            )
            title_label.pack(pady=10, padx=15, anchor="w")
        except:
            # 顶部标题标签
            title_label = tk.Label(
                root,
                text="Editor have problem , please copy error massage to send developer",
                bg="#ffffff",
                fg="#d02020",
                font=("Microsoft YaHei", 12, "bold")
            )
            title_label.pack(pady=10, padx=15, anchor="w")
            self.root.iconbitmap("res/AoiStudio.png")
            self.is_editor = True
        # 整体白色背景
        self.root.configure(bg="#ffffff")



        # 分割线
        sep = ttk.Separator(root, orient="horizontal")
        sep.pack(fill="x", padx=10)

        # 文本框+滚动条容器
        frame_text = tk.Frame(root, bg="#ffffff")
        frame_text.pack(fill="both", expand=True, padx=10, pady=10)

        scrollbar = tk.Scrollbar(frame_text)
        scrollbar.pack(side="right", fill="y")

        # 白色背景文本域，等宽字体模拟堆栈日志
        self.text_log = tk.Text(
            frame_text,
            bg="#ffffff",
            fg="#222222",
            font=("Consolas", 10),
            yscrollcommand=scrollbar.set,
            wrap="none"
        )
        self.text_log.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.text_log.yview)

        crash_content = error_msg
        self.text_log.insert(tk.END, crash_content)
        self.text_log.config(state="disabled")

        # 底部按钮容器
        frame_btn = tk.Frame(root, bg="#ffffff")
        frame_btn.pack(fill="x", padx=10, pady=12)

        btn_copy = tk.Button(frame_btn, text="Send error massage to issue", command=self.on_send_error_massage)
        btn_copy.pack(side="right", padx=5)

        btn_copy = tk.Button(frame_btn, text="Copy error massage", command=self.on_copy)
        btn_copy.pack(side="right", padx=5)

        btn_close = tk.Button(frame_btn, text="Close", command=self.root.destroy)
        btn_close.pack(side="right", padx=5)

    def on_copy(self):
        """复制全部日志到剪贴板"""
        self.root.clipboard_clear()
        text = self.text_log.get("1.0", tk.END)
        self.root.clipboard_append(text)

    def on_send_error_massage(self):
        """发送错误信息到GitHub"""
        if not self.is_editor:
            reporter.open_github_issue("AoiStudio Engine Fatal Error", self.text_log.get("1.0", tk.END))
        else:
            reporter.open_github_issue("AoiStudio Editor Fatal Error", self.text_log.get("1.0", tk.END))
def main(msg=""):
    win = tk.Tk()
    app = UE4LikeErrorWindow(win,msg)
    win.mainloop()

if __name__ == "__main__":
    main()