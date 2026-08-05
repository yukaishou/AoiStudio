import ctypes
from ctypes import wintypes
import struct
import os
import shutil
import pefile

RT_ICON = 3
RT_GROUP_ICON = 14
kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

BeginUpdateResourceW = kernel32.BeginUpdateResourceW
BeginUpdateResourceW.argtypes = [wintypes.LPCWSTR, wintypes.BOOL]
BeginUpdateResourceW.restype = wintypes.HANDLE

UpdateResourceW = kernel32.UpdateResourceW
UpdateResourceW.argtypes = [wintypes.HANDLE, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.WORD, wintypes.LPCVOID, wintypes.DWORD]
UpdateResourceW.restype = wintypes.BOOL

EndUpdateResourceW = kernel32.EndUpdateResourceW
EndUpdateResourceW.argtypes = [wintypes.HANDLE, wintypes.BOOL]
EndUpdateResourceW.restype = wintypes.BOOL


def make_int_resource(res_id):
    return ctypes.cast(ctypes.c_void_p(res_id), wintypes.LPCWSTR)


def load_icon_file(ico_path):
    with open(ico_path, 'rb') as f:
        data = f.read()
    if len(data) < 6:
        raise ValueError("无效ICO文件")
    reserved, type_, count = struct.unpack('<HHH', data[:6])
    if reserved != 0 or type_ != 1:
        raise ValueError("不是标准ICO图标")
    entries = []
    offset = 6
    for _ in range(count):
        ed = data[offset:offset + 16]
        w, h, col, r2, planes, bpp, sz, img_off = struct.unpack('<BBBBHHII', ed)
        img = data[img_off:img_off + sz]
        entries.append({
            'w': w or 256,
            'h': h or 256,
            'planes': planes,
            'bpp': bpp,
            'sz': sz,
            'data': img
        })
        offset += 16
    group_data = struct.pack('<HHH', 0, 1, count)
    for i, e in enumerate(entries):
        group_data += struct.pack('<BBBBHHII', e['w'], e['h'], 0, 0, e['planes'], e['bpp'], e['sz'], i + 1)
    return group_data, [e['data'] for e in entries]


def modify_bootloader_icon(boot_path, ico_path):
    group_data, images = load_icon_file(ico_path)
    hUpdate = BeginUpdateResourceW(boot_path, False)
    if not hUpdate:
        raise OSError(f"BeginUpdateResourceW失败，错误码={ctypes.get_last_error()}，请管理员运行")
    try:
        for i, img in enumerate(images):
            buf = ctypes.create_string_buffer(img)
            UpdateResourceW(hUpdate, make_int_resource(RT_ICON), make_int_resource(i + 1), 0, ctypes.byref(buf), len(img))
        grp_buf = ctypes.create_string_buffer(group_data)
        UpdateResourceW(hUpdate, make_int_resource(RT_GROUP_ICON), make_int_resource(1), 0, ctypes.byref(grp_buf), len(group_data))
    except Exception:
        EndUpdateResourceW(hUpdate, True)
        raise
    EndUpdateResourceW(hUpdate, False)


def calc_overlay_offset(pe: pefile.PE):
    """替代已经删除的 get_overlay_offset，计算PE实际文件大小"""
    max_raw = 0
    for sec in pe.sections:
        end = sec.PointerToRawData + sec.SizeOfRawData
        if end > max_raw:
            max_raw = end
    return max_raw


def patch_pyinstaller_icon_inplace(exe_path: str, ico_file: str):
    if not os.path.isfile(exe_path):
        raise FileNotFoundError(f"EXE不存在：{exe_path}")
    if not os.path.isfile(ico_file):
        raise FileNotFoundError(f"ICO不存在：{ico_file}")

    backup_path = os.path.splitext(exe_path)[0] + "_backup.exe"
    shutil.copy2(exe_path, backup_path)
    print(f"已备份原exe → {backup_path}")

    pe = pefile.PE(exe_path)
    overlay_offset = calc_overlay_offset(pe)
    pe.close()   # 立刻释放PE句柄！！

    with open(exe_path, 'rb') as f:
        raw = f.read()
    boot_bytes = raw[:overlay_offset]
    overlay_bytes = raw[overlay_offset:]

    temp_boot = "_temp_boot.exe"
    with open(temp_boot, 'wb') as f:
        f.write(boot_bytes)

    modify_bootloader_icon(temp_boot, ico_file)

    with open(temp_boot, 'rb') as f:
        new_boot = f.read()
    os.remove(temp_boot)

    with open(exe_path, 'wb') as f:
        f.write(new_boot)
        f.write(overlay_bytes)

    print(f"exe图标修改完成：{exe_path}")