import sys
import os
import struct

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication, QDialog, QWidget, QSplitter, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QLabel, QFileDialog, QTreeWidget, QTreeWidgetItem,
    QGroupBox, QHeaderView, QMessageBox, QStatusBar, QSizePolicy
)
from PySide6.QtCore import Qt, QThread, Signal

# ========== 资源包底层解析逻辑 ==========
MAGIC_CBRESB = b"AOIP"
BUNDLE_VERSION = 1


def read_bundle_entries(bundle_path: str) -> list[dict]:
    """只读取索引，不读取资源数据，用于预览列表"""
    with open(bundle_path, "rb") as f:
        magic = f.read(4)
        if magic != MAGIC_CBRESB:
            raise Exception("不是有效的aoipackage资源包")
        ver = struct.unpack("<H", f.read(2))[0]
        if ver != BUNDLE_VERSION:
            raise Exception(f"版本不支持 {ver}")
        entry_count = struct.unpack("<I", f.read(4))[0]

        entries = []
        for _ in range(entry_count):
            name_len = struct.unpack("<H", f.read(2))[0]
            res_name = f.read(name_len).decode("utf-8")
            offset = struct.unpack("<Q", f.read(8))[0]
            size = struct.unpack("<Q", f.read(8))[0]
            entries.append({
                "name": res_name,
                "offset": offset,
                "size": size,
            })
    return entries


def unpack_selected_bundle(bundle_path: str, out_dir: str, selected_names: list[str], log_callback):
    """只提取选中名字的资源"""
    os.makedirs(out_dir, exist_ok=True)
    with open(bundle_path, "rb") as f:
        magic = f.read(4)
        ver = struct.unpack("<H", f.read(2))[0]
        entry_count = struct.unpack("<I", f.read(4))[0]

        entries = []
        for _ in range(entry_count):
            name_len = struct.unpack("<H", f.read(2))[0]
            res_name = f.read(name_len).decode("utf-8")
            offset = struct.unpack("<Q", f.read(8))[0]
            size = struct.unpack("<Q", f.read(8))[0]
            entries.append({"name": res_name, "offset": offset, "size": size})

        data_start_pos = f.tell()
        for e in entries:
            if e["name"] not in selected_names:
                continue
            f.seek(data_start_pos + e["offset"])
            res_data = f.read(e["size"])
            out_path = os.path.join(out_dir, e["name"])
            # 自动创建子文件夹（如果资源名带路径）
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            with open(out_path, "wb") as fw:
                fw.write(res_data)
            log_callback(f"📄 提取：{e['name']}")
    log_callback(f"✅ 资源导入完成，输出目录: {out_dir}")


# ========== 后台解包线程 ==========
class UnpackThread(QThread):
    log_signal = Signal(str)
    finish_signal = Signal(bool)

    def __init__(self, bundle_path, out_dir, selected_names):
        super().__init__()
        self.bundle_path = bundle_path
        self.out_dir = out_dir
        self.selected_names = selected_names

    def run(self):
        try:
            unpack_selected_bundle(self.bundle_path, self.out_dir, self.selected_names, self.log_callback)
            self.finish_signal.emit(True)
        except Exception as e:
            self.log_signal(f"❌ 导入异常：{str(e)}")
            self.finish_signal.emit(False)

    def log_callback(self, msg):
        self.log_signal.emit(msg)


# ========== Unity风格【Import Package】模态对话框 ==========
class AoiPackageImportDialog(QDialog):
    def __init__(self, bundle_path: str, entries: list[dict],project_path: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("导入包")
        self.setWindowIcon(QIcon("res/AoiStudio.png"))
        self.resize(400, 540)
        self.setModal(True)
        self.bundle_path = bundle_path
        self.entries = entries
        self.selected_entry: dict | None = None
        self._ignore_check_event = False  # 防止勾选事件递归循环
        self.project_path = project_path

        # 主布局：设置边距，避免贴边
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10,10,10,10)
        main_layout.setSpacing(8)

        # ========== 顶部信息栏（固定垂直尺寸，不拉伸） ==========
        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(0,0,0,0)
        top_layout.setSpacing(6)
        lbl_title = QLabel("资源包路径:")
        lbl_title.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.label_bundle_path = QLabel(os.path.basename(bundle_path))
        self.label_bundle_path.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        top_layout.addWidget(lbl_title)
        top_layout.addWidget(self.label_bundle_path)
        top_layout.addStretch(1)
        # 把这个布局加入主布局，不允许垂直拉伸
        top_container = QWidget()
        top_container.setLayout(top_layout)
        top_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        main_layout.addWidget(top_container)

        # 中间分割区域 左侧树列表，右侧详情面板
        splitter = QSplitter(Qt.Horizontal)
        splitter.setContentsMargins(0,0,0,0)

        # ========== 左侧：资源树 ==========
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0,0,0,0)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["资源"])
        self.tree.header().setSectionResizeMode(QHeaderView.Stretch)
        self.tree.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        left_layout.addWidget(self.tree)
        splitter.addWidget(left_widget)

        # ========== 右侧：选中资源详情面板 ==========
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(4,0,0,0)
        detail_group = QGroupBox("资源详情")
        detail_layout = QVBoxLayout(detail_group)
        detail_layout.setSpacing(6)
        self.detail_name = QLabel("文件名：-")
        self.detail_size = QLabel("大小：-")
        self.detail_type = QLabel("类型：-")
        detail_layout.addWidget(self.detail_name)
        detail_layout.addWidget(self.detail_size)
        detail_layout.addWidget(self.detail_type)
        right_layout.addWidget(detail_group)
        right_layout.addStretch(1)
        splitter.addWidget(right_widget)

        # ========== 分割比例适配400宽度窗口 ==========
        splitter.setSizes([240,140])
        splitter.setStretchFactor(0,3)
        splitter.setStretchFactor(1,1)
        splitter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        main_layout.addWidget(splitter)

        # ========== 输出目录栏 ==========
        out_layout = QHBoxLayout()
        out_layout.setSpacing(6)
        out_layout.addWidget(QLabel("导入到目录:"))
        self.edit_outdir = QLineEdit(os.getcwd())
        btn_browse = QPushButton("浏览")
        btn_browse.setFixedWidth(80)
        out_layout.addWidget(self.edit_outdir)
        out_layout.addWidget(btn_browse)
        out_container = QWidget()
        out_container.setLayout(out_layout)
        out_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        main_layout.addWidget(out_container)

        # ========== 底部按钮栏 ==========
        btn_bar = QHBoxLayout()
        btn_bar.addStretch()
        self.btn_import = QPushButton("导入")
        self.btn_import.setFixedWidth(100)
        self.btn_cancel = QPushButton("取消")
        self.btn_cancel.setFixedWidth(100)
        btn_bar.addWidget(self.btn_import)
        btn_bar.addWidget(self.btn_cancel)
        btn_container = QWidget()
        btn_container.setLayout(btn_bar)
        btn_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        main_layout.addWidget(btn_container)

        # ========== 底部状态栏 ==========
        self.status_bar = QStatusBar()
        self.status_bar.setMaximumHeight(22)
        self.status_bar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        main_layout.addWidget(self.status_bar)

        # 填充树
        self.fill_tree()

        # 绑定事件
        self.tree.itemSelectionChanged.connect(self.on_tree_select)
        self.tree.itemChanged.connect(self.on_tree_item_check_changed)
        btn_browse.clicked.connect(self.select_outdir)
        self.btn_import.clicked.connect(self.do_import)
        self.btn_cancel.clicked.connect(self.reject)

        if not project_path == "":
            self.edit_outdir.setText(project_path)


    def fill_tree(self):
        """构建资源树，根节点是包，子节点每个资源，带复选框，默认勾选"""
        root = QTreeWidgetItem(self.tree, [os.path.basename(self.bundle_path)])
        root.setFlags(root.flags() | Qt.ItemIsUserCheckable)
        root.setCheckState(0, Qt.Checked)

        for entry in self.entries:
            item = QTreeWidgetItem(root, [entry["name"]])
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(0, Qt.Checked)
            # 挂载资源数据到item
            item.setData(0, Qt.UserRole, entry)
        root.setExpanded(True)

    def on_tree_item_check_changed(self, item: QTreeWidgetItem, column: int):
        """勾选联动逻辑，Unity原版行为"""
        if self._ignore_check_event:
            return
        self._ignore_check_event = True

        # 父节点勾选，同步所有子节点
        if item.childCount() > 0:
            state = item.checkState(column)
            for child_idx in range(item.childCount()):
                child = item.child(child_idx)
                child.setCheckState(column, state)
        else:
            # 修改子节点，更新父节点状态（部分选中→半选）
            parent = item.parent()
            if parent is not None:
                all_checked = True
                all_unchecked = True
                for child_idx in range(parent.childCount()):
                    s = parent.child(child_idx).checkState(column)
                    if s != Qt.Checked:
                        all_checked = False
                    if s != Qt.Unchecked:
                        all_unchecked = False
                if all_checked:
                    parent.setCheckState(column, Qt.Checked)
                elif all_unchecked:
                    parent.setCheckState(column, Qt.Unchecked)
                else:
                    parent.setCheckState(column, Qt.PartiallyChecked)

        self._ignore_check_event = False

    def on_tree_select(self):
        items = self.tree.selectedItems()
        if not items:
            self.detail_name.setText("文件名：-")
            self.detail_size.setText("大小：-")
            self.detail_type.setText("类型：-")
            return
        item = items[0]
        entry = item.data(0, Qt.UserRole)
        if entry is None:
            self.detail_name.setText("文件名：(包根)")
            self.detail_size.setText("大小：-")
            self.detail_type.setText("类型：资源包")
            return
        self.selected_entry = entry
        self.detail_name.setText(f"文件名：{entry['name']}")
        size = entry["size"]
        if size < 1024:
            s_str = f"{size} B"
        elif size < 1024*1024:
            s_str = f"{size/1024:.2f} KB"
        else:
            s_str = f"{size/(1024*1024):.2f} MB"
        self.detail_size.setText(f"大小：{s_str}")
        ext = os.path.splitext(entry["name"])[1].lower()
        self.detail_type.setText(f"类型：{ext if ext else '无后缀'}")

    def select_outdir(self):
        d = QFileDialog.getExistingDirectory(self, "选择导入输出目录")
        if d:
            self.edit_outdir.setText(d)

    def collect_selected_names(self):
        """遍历树，收集勾选的资源文件名"""
        selected = []
        root = self.tree.invisibleRootItem().child(0)
        for i in range(root.childCount()):
            child_item = root.child(i)
            if child_item.checkState(0) == Qt.Checked:
                entry = child_item.data(0, Qt.UserRole)
                selected.append(entry["name"])
        return selected

    def do_import(self):
        selected_names = self.collect_selected_names()
        if len(selected_names) <= 0:
            QMessageBox.warning(self, "警告", "没有勾选任何资源！")
            return
        out_dir = self.edit_outdir.text().strip()
        if not out_dir:
            QMessageBox.warning(self, "警告", "请选择导入目录！")
            return
        self.btn_import.setEnabled(False)
        self.btn_cancel.setEnabled(False)
        self.status_bar.showMessage(f"正在导入，共选中 {len(selected_names)} 个资源...")

        self.thread = UnpackThread(self.bundle_path, out_dir, selected_names)
        self.thread.log_signal.connect(self.on_log)
        self.thread.finish_signal.connect(self.import_done)
        self.thread.start()

    def on_log(self, msg):
        self.status_bar.showMessage(msg)

    def import_done(self, ok: bool):
        self.btn_import.setEnabled(True)
        self.btn_cancel.setEnabled(True)
        if ok:
            QMessageBox.information(self, "完成", "资源导入成功！")
            self.accept()
        else:
            QMessageBox.critical(self, "失败", "资源导入失败！")


# ========== 主入口：先选包文件，弹出Unity Import Package对话框 ==========
if __name__ == "__main__":
    app = QApplication(sys.argv)
    # 先选择资源包
    fp, _ = QFileDialog.getOpenFileName(None, "打开AOI资源包", filter="AOI Package (*.aoipackage)")
    if not fp:
        sys.exit(0)
    try:
        entries = read_bundle_entries(fp)
    except Exception as e:
        QMessageBox.critical(None, "读取失败", str(e))
        sys.exit(0)
    # 弹出导入对话框（就是Unity导入Package那个弹窗）
    dlg = AoiPackageImportDialog(fp, entries)
    sys.exit(dlg.exec())