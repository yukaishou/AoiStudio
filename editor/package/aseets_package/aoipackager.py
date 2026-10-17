import struct
import os

MAGIC_CBRESB = b"AOIP"
BUNDLE_VERSION = 1


def pack_resource_bundle(
    input_file_list: list[str],
    output_prefix: str,
    max_per_file: int
):
    """
    打包资源，支持分卷
    :param input_file_list: 要打包的文件路径列表（可以是cbresf/png/mp3/txt）
    :param output_prefix: 输出文件前缀，例如 "res_bundle" → res_bundle_0.cbresb
    :param max_per_file: 单个包最大字节上限（单位：字节）
    """
    bundle_index = 0
    current_entries = []
    current_data_buffer = b""

    def flush_current_bundle():
        nonlocal bundle_index, current_entries, current_data_buffer
        if not current_entries:
            return

        out_name = f"{output_prefix}_{bundle_index}.aoipackage"
        with open(out_name, "wb") as f:
            # 先预留头部位置，后面回来写索引数量
            f.write(MAGIC_CBRESB)
            f.write(struct.pack("<H", BUNDLE_VERSION))
            f.write(struct.pack("<I", len(current_entries)))

            # 写入索引表
            for entry in current_entries:
                name_bytes = entry["name"].encode("utf-8")
                f.write(struct.pack("<H", len(name_bytes)))
                f.write(name_bytes)
                f.write(struct.pack("<Q", entry["offset"]))
                f.write(struct.pack("<Q", entry["size"]))

            # 写入资源数据块
            f.write(current_data_buffer)
        print(f"已生成包：{out_name}，资源数量：{len(current_entries)}")
        bundle_index += 1
        current_entries.clear()
        current_data_buffer = b""

    for filepath in input_file_list:
        if not os.path.isfile(filepath):
            print(f"跳过不存在文件：{filepath}")
            continue
        filename = os.path.basename(filepath)
        with open(filepath, "rb") as f:
            data = f.read()

        # 预估加入后总大小：头部固定 +索引大小 + 当前data_buffer长度 + data长度
        # 估算单条索引占用：2(名字长度)+名字字节+8+8
        name_bytes = filename.encode("utf-8")
        entry_est_size = 2 + len(name_bytes) + 16
        estimated_total = (4 + 2 + 4) + (sum(2+len(e["name"].encode("utf-8"))+16 for e in current_entries)) + entry_est_size + len(current_data_buffer) + len(data)

        # 如果超过单包上限，先把当前包刷写到磁盘
        if estimated_total > max_per_file and len(current_entries) > 0:
            flush_current_bundle()

        # 记录该资源在当前data_buffer内的偏移
        offset_in_bundle = len(current_data_buffer)
        current_entries.append({
            "name": filename,
            "offset": offset_in_bundle,
            "size": len(data)
        })
        current_data_buffer += data

    # 把最后剩下的资源写入最后一个包
    flush_current_bundle()
    print("全部打包完成！")


def unpack_bundle(bundle_path: str, out_dir="bundle_out"):
    """
    解包单个cbresb文件，提取里面所有资源
    """
    os.makedirs(out_dir, exist_ok=True)
    with open(bundle_path, "rb") as f:
        magic = f.read(4)
        if magic != MAGIC_CBRESB:
            raise Exception("不是有效的cbresb资源包")
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
            entries.append({"name": res_name, "offset": offset, "size": size})

        # 索引读完，当前文件指针位置就是数据块起始位置
        data_start_pos = f.tell()
        for e in entries:
            f.seek(data_start_pos + e["offset"])
            res_data = f.read(e["size"])
            out_path = os.path.join(out_dir, e["name"])
            with open(out_path, "wb") as fw:
                fw.write(res_data)
            print(f"提取：{e['name']}")
    print(f"{bundle_path} 解包完成")


if __name__ == "__main__":
    # ============ 使用示例 ============
    # 打包：设置每个包最大 10MB (10*1024*1024)
    file_list = [
        "aoipackager.py"
    ]
    # 每个包最大100MB，超过自动分割
    pack_resource_bundle(
        input_file_list=file_list,
        output_prefix="package_test",
        max_per_file=100 * 1024 * 1024
    )