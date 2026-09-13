import json
import os
from pathlib import Path
from typing import List, Dict, Optional, Union

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