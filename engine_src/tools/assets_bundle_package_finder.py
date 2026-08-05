import json
import os
from pathlib import Path
from typing import List, Dict, Optional, Union
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QLabel, QTextEdit, QFileDialog,
    QListWidget, QTabWidget, QGroupBox, QFormLayout
)
from PyQt5.QtCore import Qt
import fnmatch


class FileQuery:
    """
    文件查询器类
    用于查询分包后的文件信息和包信息
    """

    def __init__(self, package_list_path: str):
        """
        初始化查询器

        Args:
            package_list_path: package_list.json 文件路径
        """
        self.package_list_path = Path(package_list_path)
        self.data = self._load_package_list()

    def _load_package_list(self) -> Dict:
        """
        加载 package_list.json 文件

        Returns:
            JSON 数据字典
        """
        if not self.package_list_path.exists():
            raise FileNotFoundError(f"找不到文件: {self.package_list_path}")

        with open(self.package_list_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def get_all_packages(self) -> List[Dict]:
        """
        获取所有包的信息

        Returns:
            包信息列表
        """
        return self.data.get('packages', [])

    def get_package_by_name(self, package_name: str) -> Optional[Dict]:
        """
        根据包名获取包信息

        Args:
            package_name: 包名

        Returns:
            包信息字典，未找到返回 None
        """
        for package in self.data.get('packages', []):
            if package['name'] == package_name:
                return package
        return None

    def find_file_in_packages(self, filename: str) -> List[Dict]:
        """
        查找文件所在的包

        Args:
            filename: 要查找的文件名

        Returns:
            包含该文件的包信息列表
        """
        matching_packages = []
        for package in self.data.get('packages', []):
            if filename in package['files']:
                matching_packages.append({
                    'package': package['name'],
                    'file_path': str(Path(package['path']).parent / package['name']),
                    'file_info': filename
                })
        return matching_packages

    def find_file_by_relative_path(self, relative_path: str) -> List[Dict]:
        """
        根据相对路径查找文件

        Args:
            relative_path: 文件的相对路径

        Returns:
            包含该文件的包信息列表
        """
        matching_packages = []
        for package in self.data.get('packages', []):
            for file_path in package['files']:
                if file_path == relative_path or Path(file_path).name == Path(relative_path).name:
                    matching_packages.append({
                        'package': package['name'],
                        'file_path': file_path,
                        'package_info': package
                    })
        return matching_packages

    def get_file_count_by_extension(self) -> Dict[str, int]:
        """
        统计不同扩展名的文件数量

        Returns:
            扩展名及对应数量的字典
        """
        ext_count = {}
        for package in self.data.get('packages', []):
            for file_path in package['files']:
                ext = Path(file_path).suffix.lower()
                if ext:
                    ext_count[ext] = ext_count.get(ext, 0) + 1
                else:
                    ext_count['no_extension'] = ext_count.get('no_extension', 0) + 1
        return ext_count

    def get_total_files_count(self) -> int:
        """
        获取总文件数量

        Returns:
            总文件数量
        """
        return sum(pkg['file_count'] for pkg in self.data.get('packages', []))

    def get_total_size(self) -> int:
        """
        获取所有包的原始总大小

        Returns:
            总大小（字节）
        """
        return sum(pkg['total_size'] for pkg in self.data.get('packages', []))

    def get_compressed_size(self) -> int:
        """
        获取所有包的压缩后总大小

        Returns:
            压缩后总大小（字节）
        """
        return sum(pkg['compressed_size'] for pkg in self.data.get('packages', []))

    def search_files_by_pattern(self, pattern: str) -> List[Dict]:
        """
        根据模式搜索文件

        Args:
            pattern: 搜索模式（支持通配符）

        Returns:
            匹配的文件信息列表
        """
        import fnmatch

        results = []
        for package in self.data.get('packages', []):
            for file_path in package['files']:
                if fnmatch.fnmatch(file_path, pattern):
                    results.append({
                        'package': package['name'],
                        'file_path': file_path,
                        'package_info': package
                    })
        return results

    def get_largest_package(self) -> Optional[Dict]:
        """
        获取最大的包（按原始大小）

        Returns:
            最大的包信息
        """
        packages = self.data.get('packages', [])
        if not packages:
            return None
        return max(packages, key=lambda x: x['total_size'])

    def get_smallest_package(self) -> Optional[Dict]:
        """
        获取最小的包（按原始大小）

        Returns:
            最小的包信息
        """
        packages = self.data.get('packages', [])
        if not packages:
            return None
        return min(packages, key=lambda x: x['total_size'])

    def get_packages_by_size_range(self, min_size: int, max_size: int) -> List[Dict]:
        """
        根据大小范围筛选包

        Args:
            min_size: 最小大小（字节）
            max_size: 最大大小（字节）

        Returns:
            符合条件的包列表
        """
        result = []
        for package in self.data.get('packages', []):
            if min_size <= package['total_size'] <= max_size:
                result.append(package)
        return result

    def export_query_result(self, query_type: str, output_path: str) -> None:
        """
        导出查询结果到文件

        Args:
            query_type: 查询类型
            output_path: 输出文件路径
        """
        result = None
        if query_type == 'all_packages':
            result = self.get_all_packages()
        elif query_type == 'file_extensions':
            result = self.get_file_count_by_extension()
        elif query_type == 'largest_package':
            result = self.get_largest_package()
        elif query_type == 'smallest_package':
            result = self.get_smallest_package()

        if result is not None:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"查询结果已导出到: {output_path}")


class PackageFinderGUI(QMainWindow):
    """
    包查找器图形界面
    """

    def __init__(self):
        super().__init__()
        self.file_query = None
        self.init_ui()

    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle('Assets Bundle Package Finder')
        self.setGeometry(100, 100, 900, 700)

        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 创建主布局
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        # 创建选项卡
        tab_widget = QTabWidget()
        main_layout.addWidget(tab_widget)

        # 文件加载选项卡
        load_tab = self.create_load_tab()
        tab_widget.addTab(load_tab, "加载文件")

        # 文件查找选项卡
        search_tab = self.create_search_tab()
        tab_widget.addTab(search_tab, "文件查找")

        # 统计信息选项卡
        stats_tab = self.create_stats_tab()
        tab_widget.addTab(stats_tab, "统计信息")

        # 结果显示区域
        self.result_text = QTextEdit()
        self.result_text.setMaximumHeight(200)
        main_layout.addWidget(QLabel("查询结果:"))
        main_layout.addWidget(self.result_text)

    def create_load_tab(self):
        """创建加载选项卡"""
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)

        # 文件选择区域
        file_group = QGroupBox("选择package_list.json文件")
        file_layout = QVBoxLayout()

        self.file_path_input = QLineEdit()
        self.file_path_input.setPlaceholderText("点击按钮选择package_list.json文件")
        file_button = QPushButton("浏览...")
        file_button.clicked.connect(self.select_file)

        file_h_layout = QHBoxLayout()
        file_h_layout.addWidget(self.file_path_input)
        file_h_layout.addWidget(file_button)

        file_layout.addLayout(file_h_layout)
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)

        # 加载按钮
        load_button = QPushButton("加载数据")
        load_button.clicked.connect(self.load_data)
        layout.addWidget(load_button)

        layout.addStretch()
        return widget

    def create_search_tab(self):
        """创建搜索选项卡"""
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)

        # 文件名查找
        name_search_group = QGroupBox("按文件名查找")
        name_layout = QFormLayout()

        self.filename_input = QLineEdit()
        self.filename_input.setPlaceholderText("输入文件名，如: example.txt")
        name_layout.addRow("文件名:", self.filename_input)

        filename_search_btn = QPushButton("查找文件名")
        filename_search_btn.clicked.connect(self.search_by_filename)
        name_layout.addRow(filename_search_btn)

        name_search_group.setLayout(name_layout)
        layout.addWidget(name_search_group)

        # 相对路径查找
        path_search_group = QGroupBox("按相对路径查找")
        path_layout = QFormLayout()

        self.relative_path_input = QLineEdit()
        self.relative_path_input.setPlaceholderText("输入相对路径，如: folder/subfolder/file.txt")
        path_layout.addRow("相对路径:", self.relative_path_input)

        path_search_btn = QPushButton("查找相对路径")
        path_search_btn.clicked.connect(self.search_by_relative_path)
        path_layout.addRow(path_search_btn)

        path_search_group.setLayout(path_layout)
        layout.addWidget(path_search_group)

        # 模式查找
        pattern_search_group = QGroupBox("按模式查找")
        pattern_layout = QFormLayout()

        self.pattern_input = QLineEdit()
        self.pattern_input.setPlaceholderText("输入模式，如: *.png 或 folder/*.txt")
        pattern_layout.addRow("搜索模式:", self.pattern_input)

        pattern_search_btn = QPushButton("查找模式")
        pattern_search_btn.clicked.connect(self.search_by_pattern)
        pattern_layout.addRow(pattern_search_btn)

        pattern_search_group.setLayout(pattern_layout)
        layout.addWidget(pattern_search_group)

        layout.addStretch()
        return widget

    def create_stats_tab(self):
        """创建统计信息选项卡"""
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)

        # 统计信息展示
        stats_group = QGroupBox("统计信息")
        stats_layout = QVBoxLayout()

        self.stats_text = QTextEdit()
        self.stats_text.setReadOnly(True)
        stats_layout.addWidget(self.stats_text)

        refresh_stats_btn = QPushButton("刷新统计信息")
        refresh_stats_btn.clicked.connect(self.refresh_stats)
        stats_layout.addWidget(refresh_stats_btn)

        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)

        # 包列表
        packages_group = QGroupBox("包列表")
        packages_layout = QVBoxLayout()

        self.packages_list = QListWidget()
        packages_layout.addWidget(self.packages_list)

        refresh_packages_btn = QPushButton("刷新包列表")
        refresh_packages_btn.clicked.connect(self.refresh_packages)
        packages_layout.addWidget(refresh_packages_btn)

        packages_group.setLayout(packages_layout)
        layout.addWidget(packages_group)

        layout.addStretch()
        return widget

    def select_file(self):
        """选择package_list.json文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择package_list.json文件", "", "JSON Files (*.json)"
        )
        if file_path:
            self.file_path_input.setText(file_path)

    def load_data(self):
        """加载数据"""
        file_path = self.file_path_input.text()
        if not file_path:
            self.show_message("请选择一个文件")
            return

        try:
            self.file_query = FileQuery(file_path)
            self.show_message(f"成功加载: {file_path}\n共{self.file_query.data['total_packages']}个包")
            self.refresh_stats()
            self.refresh_packages()
        except Exception as e:
            self.show_message(f"加载失败: {str(e)}")

    def search_by_filename(self):
        """按文件名搜索"""
        if not self.file_query:
            self.show_message("请先加载数据")
            return

        filename = self.filename_input.text()
        if not filename:
            self.show_message("请输入文件名")
            return

        results = self.file_query.find_file_in_packages(filename)

        if results:
            result_str = f"找到 {len(results)} 个匹配项:\n"
            for result in results:
                result_str += f"- 包: {result['package']}, 文件: {result['file_info']}\n"
        else:
            result_str = f"未找到文件: {filename}"

        self.result_text.setText(result_str)

    def search_by_relative_path(self):
        """按相对路径搜索"""
        if not self.file_query:
            self.show_message("请先加载数据")
            return

        relative_path = self.relative_path_input.text()
        if not relative_path:
            self.show_message("请输入相对路径")
            return

        results = self.file_query.find_file_by_relative_path(relative_path)

        if results:
            result_str = f"找到 {len(results)} 个匹配项:\n"
            for result in results:
                result_str += f"- 包: {result['package']}, 路径: {result['file_path']}\n"
        else:
            result_str = f"未找到路径: {relative_path}"

        self.result_text.setText(result_str)

    def search_by_pattern(self):
        """按模式搜索"""
        if not self.file_query:
            self.show_message("请先加载数据")
            return

        pattern = self.pattern_input.text()
        if not pattern:
            self.show_message("请输入搜索模式")
            return

        results = self.file_query.search_files_by_pattern(pattern)

        if results:
            result_str = f"找到 {len(results)} 个匹配项:\n"
            for result in results:
                result_str += f"- 包: {result['package']}, 路径: {result['file_path']}\n"
        else:
            result_str = f"未找到匹配模式: {pattern}"

        self.result_text.setText(result_str)

    def refresh_stats(self):
        """刷新统计信息"""
        if not self.file_query:
            self.stats_text.setText("请先加载数据")
            return

        stats = self.file_query.data
        ext_stats = self.file_query.get_file_count_by_extension()

        stats_str = f"""基本信息:
- 总包数: {stats['total_packages']}
- 总文件数: {self.file_query.get_total_files_count()}
- 原始总大小: {self.file_query.get_total_size() / (1024*1024):.2f} MB
- 压缩后总大小: {self.file_query.get_compressed_size() / (1024*1024):.2f} MB

文件扩展名统计:"""

        for ext, count in sorted(ext_stats.items(), key=lambda x: x[1], reverse=True):
            stats_str += f"\n- {ext}: {count} 个文件"

        largest = self.file_query.get_largest_package()
        smallest = self.file_query.get_smallest_package()

        if largest:
            stats_str += f"\n\n最大包: {largest['name']} ({largest['total_size'] / (1024*1024):.2f} MB)"
        if smallest:
            stats_str += f"\n最小包: {smallest['name']} ({smallest['total_size'] / (1024*1024):.2f} MB)"

        self.stats_text.setText(stats_str)

    def refresh_packages(self):
        """刷新包列表"""
        if not self.file_query:
            self.packages_list.clear()
            return

        self.packages_list.clear()
        packages = self.file_query.get_all_packages()

        for package in packages:
            item_text = f"{package['name']} - {package['file_count']} 文件 - {package['total_size'] / (1024*1024):.2f} MB"
            self.packages_list.addItem(item_text)

    def show_message(self, message):
        """显示消息"""
        self.result_text.setText(message)


def main():
    """主函数"""
    app = QApplication([])
    window = PackageFinderGUI()
    window.show()
    app.exec_()


if __name__ == "__main__":
    main()

