import os
import json

def build_dialog_index(root_dir: str, output_index_path: str = "config/dialog_index.json"):
    """
    扫描剧本文件夹，生成 id -> 相对路径 的索引文件
    :param root_dir: 剧本根目录，例如 "./dialogs"
    :param output_index_path: 输出索引文件路径
    """
    index = dict()
    root_abs = os.path.abspath(root_dir)

    for dirpath, _, filenames in os.walk(root_abs):
        for fname in filenames:
            if not fname.lower().endswith(".json"):
                continue
            file_abs = os.path.join(dirpath, fname)
           # 把res/前的字符串删除
            rel_path = file_abs[len(root_abs) + 1:]

            try:
                with open(file_abs, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception as e:
                print(f"[跳过]读取失败 {rel_path} : {e}")
                continue

            script_id = data.get("id", "").strip()
            if not script_id:
                print(f"[跳过]id为空 {rel_path}")
                continue

            if script_id in index:
                print(f"[警告]重复id！id={script_id}，已有:{index[script_id]} 冲突:{rel_path}")
            index[script_id] = rel_path

    # 写出索引
    with open(output_index_path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=4)

    print(f"构建完成，一共 {len(index)} 条剧本索引，输出到：{output_index_path}")
    return index


if __name__ == "__main__":
    # ========== 修改这里为你的剧本目录 ==========
    DIALOG_FOLDER = "../engine_src/res"
    OUTPUT_FILE = "config/dialog_index.json"
    build_dialog_index(DIALOG_FOLDER, OUTPUT_FILE)