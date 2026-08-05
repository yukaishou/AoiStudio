import os
import pygame
import importlib.util
import json
import zipfile
from pathlib import Path
from engine_src.engine.resource import assets_bundle


class AssetManager:
    def __init__(self, engine):
        self.engine = engine
        paks_path = f"paks"
        if os.path.exists(paks_path):
            self.pak_finder = assets_bundle.FileQuery(
                f"{paks_path}/package_list.json"
            )
        else:
            self.pak_finder = None

        # 资源缓存
        self._image_cache = {}
        self._sound_cache = {}
        self._model_cache = {}
        self._file_cache = {}
        self._text_cache = {}    # 新增：文本缓存
        self._json_cache = {}    # 新增：json缓存

        # 缓存统计
        self.cache_stats = {
            'hits': 0,
            'misses': 0
        }

    def _get_asset_base_paths(self):
        """获取资产基础路径"""
        managed_path = f"mgd\\"
        resource_path = f"res\\"
        return managed_path, resource_path

    def load_model(self, path, name):
        """
        加载模型文件（支持 .py 和 .pyc 文件，带缓存）

        Args:
            path: 模型相对路径
            name: 模块名称

        Returns:
            Module or None if failed to load
        """
        cache_key = f"{path}_{name}"

        # 检查缓存
        if cache_key in self._model_cache:
            self.cache_stats['hits'] += 1
            return self._model_cache[cache_key]

        self.cache_stats['misses'] += 1

        managed_path, _ = self._get_asset_base_paths()

        # 尝试加载 .py 文件
        py_path = os.path.join(managed_path, f"{path}.py")
        # 尝试加载 .pyc 文件
        pyc_path = f"{py_path}c"

        # 确定最终要加载的路径
        final_path = self._find_existing_path(py_path, pyc_path)
        if final_path is None:
            print(f"ERROR: Model {py_path} and {pyc_path} not found")
            return None

        # 获取绝对路径并加载模块
        abs_path = os.path.abspath(final_path)
        print(f"INFO: Loading model: {abs_path}")

        try:
            spec = importlib.util.spec_from_file_location(name, abs_path)
            if spec is None:
                print(f"ERROR: Could not create spec for {abs_path}")
                return None

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # 缓存结果
            self._model_cache[cache_key] = module
            return module
        except Exception as e:
            print(f"ERROR: Failed to load model {abs_path}: {e}")
            return None

    def _find_existing_path(self, *paths):
        """查找存在的路径"""
        for path in paths:
            if os.path.exists(path):
                return path
        return None

    def load_image(self, path):
        """
        加载图像文件（带缓存）

        Args:
            path: 图像相对路径

        Returns:
            pygame.Surface or None if failed to load
        """
        # 检查缓存
        if path in self._image_cache:
            self.cache_stats['hits'] += 1
            return self._image_cache[path]

        self.cache_stats['misses'] += 1
        image = self._load_asset_from_source_or_package(
            path,
            lambda p: pygame.image.load(p),
            "image"
        )

        # 缓存结果
        if image is not None:
            self._image_cache[path] = image

        return image

    def load_sound(self, path):
        """
        加载声音文件（带缓存）

        Args:
            path: 声音相对路径

        Returns:
            pygame.mixer.Sound or None if failed to load
        """
        # 检查缓存
        if path in self._sound_cache:
            self.cache_stats['hits'] += 1
            return self._sound_cache[path]

        self.cache_stats['misses'] += 1
        sound = self._load_asset_from_source_or_package(
            path,
            lambda p: pygame.mixer.Sound(p),
            "sound"
        )

        # 缓存结果
        if sound is not None:
            self._sound_cache[path] = sound

        return sound

    def load_music(self, path):
        """
        加载声音文件（带缓存）

        Args:
            path: 声音相对路径

        Returns:
            pygame.mixer.Sound or None if failed to load
        """
        # 检查缓存
        if path in self._sound_cache:
            self.cache_stats['hits'] += 1
            return self._sound_cache[path]

        self.cache_stats['misses'] += 1
        sound = self._load_asset_from_source_or_package(
            path,
            lambda p: pygame.mixer.music.load(p),
            "music"
        )

        # 缓存结果
        if sound is not None:
            self._sound_cache[path] = sound
        return sound


    def _load_text_from_package(self, path: str, encoding: str = "utf-8") -> str | None:
        """从 pak 包中加载文本文件"""
        try:
            package_info = self.pak_finder.find_file_by_relative_path(path)
            if not package_info or not package_info[0].get("package"):
                print(f"ERROR: Text file {path} not found in any package")
                return None

            pak_file_name = package_info[0]["package"]
            pak_path = f"paks/{pak_file_name}"

            with zipfile.ZipFile(pak_path, 'r') as zip_io:
                with zip_io.open(path) as source_file:
                    content = source_file.read().decode(encoding)

            print(f"INFO: Load text {path} from package {pak_file_name}")
            return content
        except KeyError:
            print(f"ERROR: Text file {path} not found in package")
        except Exception as e:
            print(f"ERROR: Failed to load text file {path} from package: {e}")
        return None

    def _load_asset_from_source_or_package(self, path, loader_func, asset_type):
        """
        从源文件或包中加载资源的通用方法

        Args:
            path: 资源相对路径
            loader_func: 加载资源的函数
            asset_type: 资源类型 ("image" 或 "sound")

        Returns:
            加载的资源对象或None
        """
        _, resource_path = self._get_asset_base_paths()
        source_path = os.path.join(resource_path, path)

        # 如果存在源文件目录，则从源文件加载
        if os.path.exists(source_path):
            # print(f"INFO: Load {asset_type} {path} from source files")
            try:
                return loader_func(source_path)
            except pygame.error as e:
                print(f"ERROR: Failed to load {asset_type} from source {source_path}: {e}")
                return None
        # 否则从包中加载
        elif self.pak_finder is not None:
            pack_result = self._load_asset_from_package(path, loader_func, asset_type)
            if pack_result and pack_result[0]:
                result, package_name = pack_result
                print(f"INFO: Load {asset_type} {path} from package {package_name}")
                return result
        else:
            print(f"ERROR: No source directory or pak finder available for {asset_type} {path}")

        return None

    def _load_asset_from_package(self, path, loader_func, asset_type):
        """
        从包中加载资源的通用方法

        Args:
            path: 资源相对路径
            loader_func: 加载资源的函数
            asset_type: 资源类型

        Returns:
            (资源对象, 包名) 或 None
        """
        try:
            # 获取包信息
            package_info = self.pak_finder.find_file_by_relative_path(path)
            if not package_info or not package_info[0].get("package"):
                print(f"ERROR: {asset_type.capitalize()} file {path} not found in any package")
                return None

            pak_file_name = package_info[0]["package"]
            pak_path = f"paks/{pak_file_name}"

            # 提取文件扩展名并创建临时文件名
            ext = path.split('.')[-1]
            tmp_filename = f"tmp_{asset_type}.{ext}"

            with zipfile.ZipFile(pak_path, 'r') as zip_io:
                # 提取到临时文件
                with zip_io.open(path) as source_file:
                    with open(tmp_filename, 'wb') as target_file:
                        target_file.write(source_file.read())

                # 加载资源
                asset = loader_func(tmp_filename)

            # 清理临时文件
            self._cleanup_temp_file(tmp_filename)

            return asset, pak_file_name

        except FileNotFoundError:
            print(f"ERROR: Package file not found for {asset_type} {path}")
        except KeyError:
            print(f"ERROR: {asset_type.capitalize()} file {path} not found in package")
        except pygame.error as e:
            print(f"ERROR: Failed to load {asset_type} after extraction {path}: {e}")
        except Exception as e:
            print(f"ERROR: Unexpected error loading {asset_type} {path}: {e}")
        finally:
            # 确保临时文件被删除
            self._cleanup_temp_file_locals(locals())

        return None

    def _cleanup_temp_file(self, filename):
        """清理单个临时文件"""
        if os.path.exists(filename):
            try:
                os.remove(filename)
            except OSError as e:
                # 打印错误信息
                print(f"ERROR: {e}")
                print(f"ERROR: Failed to delete temporary file {filename}")

    def _cleanup_temp_file_locals(self, local_vars):
        """从局部变量中清理临时文件"""
        if 'tmp_filename' in local_vars and os.path.exists(local_vars['tmp_filename']):
            try:
                os.remove(local_vars['tmp_filename'])
            except OSError:
                pass  # 忽略删除失败的情况

    def get_cache_stats(self):
        """获取缓存统计信息"""
        total_requests = self.cache_stats['hits'] + self.cache_stats['misses']
        hit_rate = (self.cache_stats['hits'] / total_requests * 100) if total_requests > 0 else 0

        return {
            'hits': self.cache_stats['hits'],
            'misses': self.cache_stats['misses'],
            'hit_rate': round(hit_rate, 2),
            'cached_images': len(self._image_cache),
            'cached_sounds': len(self._sound_cache),
            'cached_models': len(self._model_cache),
            'cached_text': len(self._text_cache),
            'cached_json': len(self._json_cache)
        }

    def clear_cache(self):
        """清空所有缓存"""
        self._image_cache.clear()
        self._sound_cache.clear()
        self._model_cache.clear()
        self._file_cache.clear()
        self._text_cache.clear()
        self._json_cache.clear()
        self.cache_stats = {'hits': 0, 'misses': 0}

    def __del__(self):
        """析构函数，清理资源"""
        self.clear_cache()

    def load_file_buffer(self, path: str):
        """
        读取原始二进制文件流（优先源目录，再pak包）
        path：不带 res/ 的相对路径
        Returns: bytes / None
        """
        _, resource_path = self._get_asset_base_paths()
        # 统一拼接资源根目录
        src_path = self._normalize_asset_path(path)

        if src_path.startswith("res"):
            src_path = "res/"+src_path
            src_path = self._normalize_asset_path(src_path)
        if os.path.exists(src_path):

            try:

                with open(src_path, 'rb') as f:
                    return f.read()
            except Exception as e:
                print(f"ERROR read source file {src_path}: {e}")
                return None

        if self.pak_finder is None:
            print(f"ERROR: pak finder not ready, cannot load {path}")
            return None
        try:
            src_path = src_path.replace("res/", "")  # 去除res前缀
            package_info = self.pak_finder.find_file_by_relative_path(src_path)
            if not package_info:
                return None
            pak_name = package_info[0]["package"]
            pak_path = os.path.join("paks", pak_name)
            with zipfile.ZipFile(pak_path, "r") as zf:
                with zf.open(src_path) as fp:
                    return fp.read()
        except Exception as e:
            print(f"ERROR load buffer {path}: {e}")
            return None

    def find_file_by_relative_path(self, path: str):
        """
        根据相对路径查找文件
        Returns: (真实路径/None, 来源标签: Source / Package / None)
        """
        src_path = f"{path}"
        if os.path.exists(src_path):
            return src_path, "Source"
        if self.pak_finder is None:
            return None, None
        try:
            package_info = self.pak_finder.find_file_by_relative_path(path)
            if package_info and package_info[0].get("package"):
                return package_info[0]["package"], "Package"
        except Exception as e:
            print(f"ERROR: Failed to find file {path}: {e}")
        return None, None

    # ====================== 新增接口 ======================
    def load_text_file(self, path: str, encoding="utf-8"):
        """
        加载文本文件，带缓存
        :param path: 资源相对路径
        :param encoding: 文件编码
        :return: 文本字符串 / None
        """
        if path in self._text_cache:
            self.cache_stats["hits"] += 1
            return self._text_cache[path]
        self.cache_stats["misses"] += 1
       # 从源文件加载文本文件
        path = f"res/{path}"
        raw_data = self.load_file_buffer(path)
        if raw_data is None:
            print(f"ERROR: Text file {path} load failed")
            return None
        try:
            text = raw_data.decode(encoding)
            self._text_cache[path] = text
            return text
        except Exception as e:
            print(f"ERROR decode text {path}: {e}")
            return None

    def load_json_file(self, path: str, encoding="utf-8"):
        """
        加载json文件，自动解析dict/list，带缓存
        :param path: 资源相对路径
        :param encoding: 文件编码
        :return: 解析后的json对象 / None
        """
        _ ,path_ = self._get_asset_base_paths()
        path = path_ +path

        if path in self._json_cache:
            self.cache_stats["hits"] += 1
            return self._json_cache[path]
        self.cache_stats["misses"] += 1

        text = self.load_text_file(path, encoding)
        if text is None:
            return None
        try:
            data = json.loads(text)
            self._json_cache[path] = data
            return data
        except Exception as e:
            print(f"ERROR parse json {path}: {e}")
            return None

    def _normalize_asset_path(self, path: str) -> str:
        """
        路径标准化：
        1. 统一转为正斜杠
        2. 如果开头携带 res/ 自动剥离（兼容上层错误传参）
        返回：不带res前缀的内部相对路径
        """
        p = path.replace("\\", "/").strip()
        prefix = "res/"
        #如果拥有2个以上的res前缀，自动剥离
        if p.startswith(prefix) and len(p.split(prefix)) > 2:
            p = p[len(prefix):]

        return p