import sys
import json
import os
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QSplitter, QListWidget, QListWidgetItem, QTextEdit, QPushButton,
                             QGroupBox, QLabel, QScrollArea, QFrame, QMessageBox, QSizePolicy)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

# 路径配置
DOC_ROOT = "res\\docs"
DOC_LIST_PATH = os.path.join(DOC_ROOT, "docs_list.json")


def load_docs_index():
    if not os.path.exists(DOC_LIST_PATH):
        QMessageBox.critical(None, "错误", f"找不到文档索引：{DOC_LIST_PATH}")
        return None
    with open(DOC_LIST_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_single_doc(file_name):
    full_path = os.path.join(DOC_ROOT, file_name)
    if not os.path.exists(full_path):
        QMessageBox.critical(None, "错误", f"文档不存在 {full_path}")
        return None
    with open(full_path, "r", encoding="utf-8") as f:
        return json.load(f)


class DocViewerWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("帮助")
        self.resize(920, 680)
        self.index_data = load_docs_index()
        self.current_doc = None

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(8,4,8,4)
        main_layout.setSpacing(4)

        # ========== 彻底修复标题宽度问题 ==========
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0,0,0,2)
        header_layout.setSpacing(0)

        self.title_label = QLabel("帮助文档")
        f = QFont()
        f.setPointSize(15)
        f.setBold(True)
        self.title_label.setFont(f)

        # 关键！！！
        # 强制最小宽度为0，关闭QLabel内部默认的最小宽度膨胀
        self.title_label.setMinimumWidth(0)
        # sizePolicy：水平不扩张，只取sizeHint文字本身大小
        sp = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        sp.setHorizontalStretch(0)
        self.title_label.setSizePolicy(sp)

        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        main_layout.addLayout(header_layout)

        splitter = QSplitter(Qt.Horizontal)

        # 左侧：文档列表，来自docs_list.json索引
        self.list_widget = QListWidget()
        self.list_widget.setFixedWidth(220)
        self.fill_doc_list()
        self.list_widget.currentRowChanged.connect(self.on_select_doc)

        # 右侧：渲染区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        self.render_container = QWidget()
        self.render_layout = QVBoxLayout(self.render_container)
        self.render_layout.setContentsMargins(2,2,2,2)
        self.render_layout.setSpacing(6)
        scroll_area.setWidget(self.render_container)

        splitter.addWidget(self.list_widget)
        splitter.addWidget(scroll_area)
        splitter.setStretchFactor(1, 1)
        main_layout.addWidget(splitter)

    def fill_doc_list(self):
        self.list_widget.clear()
        if self.index_data is None:
            return
        for doc_meta in self.index_data["document_list"]:
            item = QListWidgetItem(doc_meta["display_name"])
            item.setData(Qt.UserRole, doc_meta)
            self.list_widget.addItem(item)

    def clear_render_panel(self):
        for i in reversed(range(self.render_layout.count())):
            w = self.render_layout.itemAt(i).widget()
            if w:
                w.setParent(None)

    def on_select_doc(self, row):
        self.clear_render_panel()
        item = self.list_widget.item(row)
        if not item:
            return
        meta = item.data(Qt.UserRole)
        doc_data = load_single_doc(meta["file_name"])
        if doc_data is None:
            return
        self.current_doc = doc_data
        self.title_label.setText(f"{doc_data['title']}  {doc_data['version']}")
        self.render_blocks(doc_data["blocks"])

    def render_blocks(self, block_list):
        bold_font = QFont()
        bold_font.setBold(True)

        for blk in block_list:
            btype = blk["type"]
            if btype == "paragraph":
                lb = QLabel(blk["content"])
                lb.setWordWrap(True)
                self.render_layout.addWidget(lb)

            elif btype == "warning":
                group = QGroupBox("⚠️ 警告")
                gl = QVBoxLayout(group)
                gl.addWidget(QLabel(blk["content"]))
                self.render_layout.addWidget(group)

            elif btype == "code_block":
                te = QTextEdit()
                te.setReadOnly(True)
                te.setPlainText(blk["content"])
                te.setMaximumHeight(140)
                self.render_layout.addWidget(te)

            elif btype == "item_entry":
                gbox = QGroupBox(f"【{blk['name']}】")
                glayout = QVBoxLayout(gbox)

                lab_sum = QLabel("说明：")
                lab_sum.setFont(bold_font)
                glayout.addWidget(lab_sum)
                glayout.addWidget(QLabel(blk['summary']))

                lab_usage = QLabel("语法：")
                lab_usage.setFont(bold_font)
                glayout.addWidget(lab_usage)
                glayout.addWidget(QLabel(blk['usage']))

                detail_text = "\n".join(blk["details"])
                te_detail = QTextEdit()
                te_detail.setReadOnly(True)
                te_detail.setPlainText(detail_text)
                te_detail.setMaximumHeight(200)
                glayout.addWidget(te_detail)

                lab_ex = QLabel("示例：")
                lab_ex.setFont(bold_font)
                glayout.addWidget(lab_ex)

                te_example = QTextEdit()
                te_example.setReadOnly(True)
                te_example.setPlainText(blk["example"])
                te_example.setMaximumHeight(90)
                glayout.addWidget(te_example)

                btn_copy = QPushButton("复制示例")
                def make_cb(txt):
                    return lambda: QApplication.clipboard().setText(txt)
                btn_copy.clicked.connect(make_cb(blk["example"]))
                glayout.addWidget(btn_copy)

                self.render_layout.addWidget(gbox)

            sep = QFrame()
            sep.setFrameShape(QFrame.HLine)
            sep.setContentsMargins(0,4,0,4)
            self.render_layout.addWidget(sep)

        self.render_layout.addStretch()


def show_doc_viewer(parent=None):
    win = DocViewerWindow(parent)
    if parent is not None:
        win.setWindowModality(Qt.ApplicationModal)
    win.show()
    return win


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    w = DocViewerWindow()
    w.show()
    sys.exit(app.exec())