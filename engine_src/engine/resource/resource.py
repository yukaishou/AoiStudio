import os
import pygame
import importlib.util
import json
import zipfile
from io import BytesIO
from pathlib import Path
from engine_src.engine.resource import assets_bundle
from engine_src.engine.core import log

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
        """获取资产基础路径，mgd保留占位，不再实际使用"""
        managed_path = f"mgd\\"
        resource_path = f"res\\"
        return managed_path, resource_path

    def load_model(self, path, name):
        """
        加载模型文件（支持 .py 和 .pyc 文件，带缓存）
        兼容两种输入：1.磁盘绝对路径(插件管理器) 2.相对路径；不再依赖mgd目录

        Args:
            path: 文件路径，可以是绝对磁盘路径 / 相对路径
            name: 模块名称

        Returns:
            Module or None if failed to load
        """
        cache_key = f"{path}_{name}"

        # 检查缓存
        if cache_key in self._model_cache:
            self.cache_stats['hits'] += 1
            log.log(3, f"[RES] model cache hit: {cache_key}")
            return self._model_cache[cache_key]

        self.cache_stats['misses'] += 1

        # 如果是绝对路径，直接使用，不再拼接mgd
        if os.path.isabs(path):
            final_path = path
        else:
            # 相对路径分支（旧逻辑保留，兼容老代码）
            managed_path, _ = self._get_asset_base_paths()
            py_path = f"{path}.py"
            pyc_path = f"{py_path}c"
            final_path = self._find_existing_path(py_path, pyc_path)
            if final_path is None:
                log.log(2, f"[RES] Model {py_path} and {pyc_path} not found")
                return None

        abs_path = os.path.abspath(final_path)
        log.log(0, f"[RES] Loading model: {abs_path}")

        try:
            spec = importlib.util.spec_from_file_location(name, abs_path)
            if spec is None:
                log.log(2, f"[RES] Could not create spec for {abs_path}")
                return None

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # 缓存结果
            self._model_cache[cache_key] = module
            return module
        except Exception as e:
            log.log(2, f"[RES] Failed to load model {abs_path}: {e}")
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
            log.log(3, f"[RES] image cache hit: {path}")
            return self._image_cache[path]

        self.cache_stats['misses'] += 1
        image = self._load_asset_from_source_or_package(
            path,
            lambda p: pygame.image.load(p),
            lambda data: pygame.image.load(BytesIO(data)),
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
            log.log(3, f"[RES] sound cache hit: {path}")
            return self._sound_cache[path]

        self.cache_stats['misses'] += 1
        sound = self._load_asset_from_source_or_package(
            path,
            lambda p: pygame.mixer.Sound(p),
            lambda data: pygame.mixer.Sound(BytesIO(data)),
            "sound"
        )

        # 缓存结果
        if sound is not None:
            self._sound_cache[path] = sound

        return sound

    def load_music(self, path):
        """
        加载背景音乐，mixer.music全局单例，**不进缓存**

        Args:
            path: 资源相对路径

        Returns:
            bool: True成功 / False失败
        """
        _, resource_path = self._get_asset_base_paths()
        src_full = os.path.join(resource_path, path)
        if os.path.exists(src_full):
            try:
                pygame.mixer.music.load(src_full)
                log.log(0, f"[RES] Load music {path} from source")
                return True
            except pygame.error as e:
                log.log(2, f"[RES] Failed to load music from source {src_full}: {e}")
                return False

        if self.pak_finder is not None:
            try:
                package_info = self.pak_finder.find_file_by_relative_path(path)
                if not package_info or not package_info[0].get("package"):
                    log.log(2, f"[RES] music {path} not found in any package")
                    return False
                pak_file_name = package_info[0]["package"]
                pak_path = f"paks/{pak_file_name}"
                with zipfile.ZipFile(pak_path, 'r') as zip_io:
                    raw_bytes = zip_io.read(path)
                # pygame.music不支持BytesIO，只能临时文件
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix=Path(path).suffix) as tf:
                    tf.write(raw_bytes)
                    tmp_music_path = tf.name
                pygame.mixer.music.load(tmp_music_path)
                os.unlink(tmp_music_path)
                log.log(0, f"[RES] Load music {path} from package {pak_file_name}")
                return True
            except Exception as e:
                log.log(2, f"[RES] Failed to load music from pak {path}: {e}")
                return False

        log.log(2, f"[RES] No source directory or pak finder available for music {path}")
        return False

    def _load_text_from_package(self, path: str, encoding: str = "utf-8") -> str | None:
        """从 pak 包中加载文本文件"""
        try:
            package_info = self.pak_finder.find_file_by_relative_path(path)
            if not package_info or not package_info[0].get("package"):
                log.log(2, f"[RES] Text file {path} not found in any package")
                return None

            pak_file_name = package_info[0]["package"]
            pak_path = f"paks/{pak_file_name}"

            with zipfile.ZipFile(pak_path, 'r') as zip_io:
                raw_bytes = zip_io.read(path)
                content = raw_bytes.decode(encoding)

            log.log(0, f"[RES] Load text {path} from package {pak_file_name}")
            return content
        except KeyError:
            log.log(2, f"[RES] Text file {path} not found in package")
        except Exception as e:
            log.log(2, f"[RES] Failed to load text file {path} from package: {e}")
        return None

    def _load_asset_from_source_or_package(self, path, loader_func, bytes_loader, asset_type):
        """
        从源文件或包中加载资源的通用方法

        Args:
            path: 资源相对路径
            loader_func: 传入磁盘路径加载函数
            bytes_loader: 传入bytes(BytesIO)内存加载函数
            asset_type: 资源类型 ("image" 或 "sound")

        Returns:
            加载的资源对象或None
        """
        _, resource_path = self._get_asset_base_paths()
        source_path = os.path.join(resource_path, path)

        # 如果存在源文件目录，则从源文件加载
        if os.path.exists(source_path):
            try:
                return loader_func(source_path)
            except pygame.error as e:
                log.log(2, f"[RES] Failed to load {asset_type} from source {source_path}: {e}")
                return None
        # 否则从包中加载
        elif self.pak_finder is not None:
            pack_result = self._load_asset_from_package_memory(path, bytes_loader, asset_type)
            if pack_result and pack_result[0]:
                result, package_name = pack_result
                log.log(0, f"[RES] Load {asset_type} {path} from package {package_name}")
                return result
        else:
            log.log(2, f"[RES] No source directory or pak finder available for {asset_type} {path}")

        return None

    def _load_asset_from_package_memory(self, path, bytes_loader, asset_type):
        """
        从pak包内存加载，**不再生成磁盘临时文件**
        Returns: (资源对象, 包名) 或 None
        """
        try:
            package_info = self.pak_finder.find_file_by_relative_path(path)
            if not package_info or not package_info[0].get("package"):
                log.log(2, f"[RES] {asset_type.capitalize()} file {path} not found in any package")
                return None

            pak_file_name = package_info[0]["package"]
            pak_path = f"paks/{pak_file_name}"

            with zipfile.ZipFile(pak_path, 'r') as zip_io:
                raw_data = zip_io.read(path)

            asset = bytes_loader(raw_data)
            return asset, pak_file_name

        except KeyError:
            log.log(2, f"[RES] {asset_type.capitalize()} file {path} not found in package")
        except pygame.error as e:
            log.log(2, f"[RES] Failed to load {asset_type} after unpack {path}: {e}")
        except Exception as e:
            log.log(2, f"[RES] Unexpected error loading {asset_type} {path}: {e}")
        return None

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
        norm_path = self._normalize_asset_path(path)
        _, resource_path = self._get_asset_base_paths()
        src_path = os.path.join(resource_path, norm_path)

        if os.path.exists(src_path):
            try:
                with open(src_path, 'rb') as f:
                    return f.read()
            except Exception as e:
                log.log(2, f"[RES] read source file {src_path}: {e}")
                return None

        if self.pak_finder is None:
            log.log(2, f"[RES] pak finder not ready, cannot load {norm_path}")
            return None
        try:
            package_info = self.pak_finder.find_file_by_relative_path(norm_path)
            if not package_info:
                return None
            pak_name = package_info[0]["package"]
            pak_path = os.path.join("paks", pak_name)
            with zipfile.ZipFile(pak_path, "r") as zf:
                return zf.read(norm_path)
        except Exception as e:
            log.log(2, f"[RES] load buffer {norm_path}: {e}")
            return None

    def find_file_by_relative_path(self, path: str):
        """
        根据相对路径查找文件
        Returns: (真实路径/None, 来源标签: Source / Package / None)
        """
        norm_path = self._normalize_asset_path(path)
        _, resource_path = self._get_asset_base_paths()
        src_path = os.path.join(resource_path, norm_path)
        if os.path.exists(src_path):
            return src_path, "Source"
        if self.pak_finder is None:
            return None, None
        try:
            package_info = self.pak_finder.find_file_by_relative_path(norm_path)
            if package_info and package_info[0].get("package"):
                return package_info[0]["package"], "Package"
        except Exception as e:
            log.log(2, f"[RES] Failed to find file {norm_path}: {e}")
        return None, None

    # ====================== 新增接口 ======================
    def load_text_file(self, path: str, encoding="utf-8"):
        """
        加载文本文件，带缓存
        :param path: 资源相对路径
        :param encoding: 文件编码
        :return: 文本字符串 / None
        """
        norm_path = self._normalize_asset_path(path)
        if norm_path in self._text_cache:
            self.cache_stats["hits"] += 1
            log.log(3, f"[RES] text cache hit: {norm_path}")
            return self._text_cache[norm_path]
        self.cache_stats["misses"] += 1

        raw_data = self.load_file_buffer(norm_path)
        if raw_data is None:
            log.log(2, f"[RES] Text file {norm_path} load failed")
            return None
        try:
            text = raw_data.decode(encoding)
            self._text_cache[norm_path] = text
            return text
        except Exception as e:
            log.log(2, f"[RES] decode text {norm_path}: {e}")
            return None

    def load_json_file(self, path: str, encoding="utf-8"):
        """
        加载json文件，自动解析dict/list，带缓存
        :param path: 资源相对路径
        :param encoding: 文件编码
        :return: 解析后的json对象 / None
        """
        norm_path = self._normalize_asset_path(path)
        if norm_path in self._json_cache:
            self.cache_stats["hits"] += 1
            log.log(3, f"[RES] json cache hit: {norm_path}")
            return self._json_cache[norm_path]
        self.cache_stats["misses"] += 1

        text = self.load_text_file(norm_path, encoding)
        if text is None:
            return None
        try:
            data = json.loads(text)
            self._json_cache[norm_path] = data
            return data
        except Exception as e:
            log.log(2, f"[RES] parse json {norm_path}: {e}")
            return None

    def _normalize_asset_path(self, path: str) -> str:
        """
        路径标准化：
        1. 统一转为正斜杠
        2. 循环剥离全部开头 res/ 前缀（兼容上层错误传参）
        返回：不带res前缀的内部相对路径
        """
        p = path.replace("\\", "/").strip()
        prefix = "res/"
        while p.startswith(prefix):
            p = p[len(prefix):]
        return p