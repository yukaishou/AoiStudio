import os
import py_compile


def compile_dir(path,target_dir):
    for root, dirs, files in os.walk(f"{path}"):
        for ttf in files:
            if ttf.endswith(".py"):
                print(f"Compiling {os.path.join(root,ttf)}...")
                rel_path = os.path.relpath(root, path)
                py_compile.compile(os.path.join(root,ttf),cfile=os.path.join(target_dir,rel_path,ttf) + "c")