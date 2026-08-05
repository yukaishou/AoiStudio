import os
import zipfile
import json
from typing import List, Dict, Any, Optional
from pathlib import Path
from tkinter import filedialog as fd
from datetime import datetime
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ZipPackageSplitter:
    """
    Zip 分包器类
    用于将文件夹压缩成多个 zip 包，并生成 JSON 列表记录打包结果
    支持根据配置文件进行灵活打包
    """

    def __init__(self, input_dir: str, output_dir: str, max_package_size: int = 100 * 1024 * 1024,
                 config: Optional[Dict[str, Any]] = None):
        """
        初始化分包器

        Args:
            input_dir: 输入目录路径
            output_dir: 输出目录路径
            max_package_size: 单个包的最大大小（字节），默认 100MB
            config: 打包配置字典，可从 EngineResourceBuildConfig.json 读取
        """
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.max_package_size = max_package_size
        self.packages_info = []  # 存储分包信息
        self.config = config or {}
        
        # 从配置中读取选项
        self.package_name_prefix = self.config.get('PackageName', '')
        self.text_assets_enabled = self.config.get('TextAssetsPackage', True)
        self.video_enabled = self.config.get('VideoPackage', True)
        self.folder_packages = self.config.get('FolderPackage', [])

        # 创建输出目录
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def get_all_files(self, directory: Path) -> List[Path]:
        """
        获取目录下所有文件的路径列表

        Args:
            directory: 目录路径

        Returns:
            文件路径列表
        """
        files = []
        for root, _, filenames in os.walk(directory):
            for filename in filenames:
                file_path =  Path(root) / filename
                files.append(file_path)
        return files

    def calculate_file_sizes(self, files: List[Path]) -> List[tuple]:
        """
        计算文件大小并排序

        Args:
            files: 文件路径列表

        Returns:
            (文件路径, 大小) 元组列表，按大小降序排列
        """
        file_sizes = []
        for file_path in files:
            size = file_path.stat().st_size
            file_sizes.append((file_path, size))

        # 按文件大小降序排列，优先处理大文件
        file_sizes.sort(key=lambda x: x[1], reverse=True)
        return file_sizes

    def classify_files_by_type(self, files_with_sizes: List[tuple]) -> Dict[str, List[tuple]]:
        """
        根据文件扩展名将文件分类

        Args:
            files_with_sizes: (文件路径, 大小) 元组列表

        Returns:
            按类型分类的文件字典
        """
        file_types = {
            "images": [".png", ".jpg", ".jpeg", ".bmp", ".gif"],
            "audios": [".mp3", ".wav", ".ogg", ".flac"],
            "videos": [".mp4", ".avi", ".mkv", ".mov"],
            "text_assets": [".json", ".xml", ".csv", ".txt", ".ini"],
            "scripts":[".py",".js",".cfg"],
            "other": []  # 未匹配的文件类型
        }

        classified_files = {key: [] for key in file_types}

        for file_path, size in files_with_sizes:
            ext = file_path.suffix.lower()
            matched = False
            for category, extensions in file_types.items():
                if ext in extensions:
                    classified_files[category].append((file_path, size))
                    matched = True
                    break
            if not matched:
                classified_files["other"].append((file_path, size))

        return classified_files

    def find_shared_files(self, classified_files: Dict[str, List[tuple]]) -> List[tuple]:
        """
        查找所有文件类型中重复的文件（文件名和大小相同）

        Args:
            classified_files: 按类型分类的文件字典

        Returns:
            共享文件列表 (文件路径, 大小)
        """
        shared_files = set()
        seen_files = {}

        for file_type, files in classified_files.items():
            for file_path, size in files:
                file_key = (file_path.name, size)  # 以文件名和大小作为唯一标识
                if file_key in seen_files:
                    shared_files.add(seen_files[file_key])
                    shared_files.add((file_path, size))
                else:
                    seen_files[file_key] = (file_path, size)

        return list(shared_files)

    def split_files_by_size(self, files_with_sizes: List[tuple]) -> List[List[tuple]]:
        """
        根据最大包大小分割文件列表

        Args:
            files_with_sizes: (文件路径, 大小) 元组列表

        Returns:
            分割后的文件列表组
        """
        packages = []
        current_package = []
        current_size = 0

        for file_path, size in files_with_sizes:
            # 如果单个文件就超过了最大大小限制，单独作为一个包
            if size > self.max_package_size:
                packages.append([(file_path, size)])
                continue

            # 如果当前包加上这个文件会超过限制，则开始新包
            if current_size + size > self.max_package_size and current_package:
                packages.append(current_package)
                current_package = [(file_path, size)]
                current_size = size
            else:
                # 否则添加到当前包
                current_package.append((file_path, size))
                current_size += size

        # 添加最后一个包
        if current_package:
            packages.append(current_package)

        return packages

    def create_zip_package(self, files_with_sizes: List[tuple], package_index: int, file_type: str, name_start_with="") -> Dict[str, Any]:
        """
        创建带类型前缀的 zip 包

        Args:
            files_with_sizes: (文件路径, 大小) 元组列表
            package_index: 包索引
            file_type: 文件类型

        Returns:
            包信息字典
        """
        package_name = f"{name_start_with}{file_type}_{package_index:03d}.pak"
        if file_type == "shared_assets":
            package_name = f"shared_assets_{package_index:03d}.pak"

        package_path = self.output_dir / package_name

        with zipfile.ZipFile(package_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path, _ in files_with_sizes:
                relative_path = file_path.relative_to(self.input_dir)
                zipf.write(file_path, relative_path)

        package_info = {
            "name": package_name,
            "path": str(package_path),
            "files": [str(f.relative_to(self.input_dir)) for f, _ in files_with_sizes],
            "file_count": len(files_with_sizes),
            "total_size": sum(size for _, size in files_with_sizes),
            "compressed_size": package_path.stat().st_size
        }

        return package_info

    def package(self, package_name_start_with="") -> bool:
        """
        执行打包操作

        Returns:
            打包是否成功
        """
        try:
            print(f"开始打包目录: {self.input_dir}")
            print(f"输出目录: {self.output_dir}")
            print(f"最大包大小: {self.max_package_size / (1024*1024):.2f} MB")

            # 获取所有文件
            all_files = self.get_all_files(self.input_dir)
            if not all_files:
                print("输入目录为空，没有文件需要打包")
                return True

            print(f"找到 {len(all_files)} 个文件")

            # 计算文件大小并排序
            files_with_sizes = self.calculate_file_sizes(all_files)

            # 按类型分类文件
            classified_files = self.classify_files_by_type(files_with_sizes)

            # 查找共享文件
            shared_files = self.find_shared_files(classified_files)
            if shared_files:
                print(f"发现 {len(shared_files)} 个共享文件，正在打包到 shared_assets...")
                shared_package_info = self.create_zip_package(shared_files, 1, "shared_assets", name_start_with=package_name_start_with)
                self.packages_info.append(shared_package_info)
                print(f"  - 包名: {shared_package_info['name']}")
                print(f"  - 文件数: {shared_package_info['file_count']}")
                print(f"  - 原始大小: {shared_package_info['total_size'] / (1024*1024):.2f} MB")
                print(f"  - 压缩后大小: {shared_package_info['compressed_size'] / (1024*1024):.2f} MB")

                # 从分类文件中移除共享文件
                for file_type in classified_files:
                    classified_files[file_type] = [
                        f for f in classified_files[file_type] if f not in shared_files
                    ]

            # 对每种类型分别分包
            for file_type, files in classified_files.items():
                if not files:
                    continue
                print(f"\n处理 {file_type} 类型文件...")
                packages = self.split_files_by_size(files)
                for i, package_files in enumerate(packages):
                    print(f"正在创建第 {i+1}/{len(packages)} 个包...")
                    package_info = self.create_zip_package(package_files, i + 1, file_type, name_start_with=package_name_start_with)
                    self.packages_info.append(package_info)

                    print(f"  - 包名: {package_info['name']}")
                    print(f"  - 文件数: {package_info['file_count']}")
                    print(f"  - 原始大小: {package_info['total_size'] / (1024*1024):.2f} MB")
                    print(f"  - 压缩后大小: {package_info['compressed_size'] / (1024*1024):.2f} MB")

            # 生成 JSON 列表
            self.generate_json_list()

            print(f"打包完成！共创建了 {len(self.packages_info)} 个包")
            return True

        except Exception as e:
            print(f"打包过程中出现错误: {e}")
            return False

    def generate_json_list(self) -> None:
        """
        生成 JSON 列表文件
        """
        json_data = {
            "input_directory": str(self.input_dir),
            "output_directory": str(self.output_dir),
            "max_package_size": self.max_package_size,
            "total_packages": len(self.packages_info),
            "packages": self.packages_info,
            "timestamp": datetime.now().isoformat()
        }

        json_path = self.output_dir / "package_list.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)

        print(f"JSON 列表已保存到: {json_path}")


def main():
    """
    主函数 - 示例用法
    """
    # 示例配置
    input_directory = fd.askdirectory(title="选择输入目录")
    output_directory = fd.askdirectory(title="选择输出目录")
    max_size = 100 * 1024 * 1024  # 最大包大小 100MB

    # 创建分包器实例
    splitter = ZipPackageSplitter(
        input_dir=input_directory,
        output_dir=output_directory,
        max_package_size=max_size
    )

    # 执行打包
    success = splitter.package()

    if success:
        print("打包任务完成！")
    else:
        print("打包任务失败！")


if __name__ == "__main__":
    main()
