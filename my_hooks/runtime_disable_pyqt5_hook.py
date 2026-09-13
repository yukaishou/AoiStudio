# runtime_disable_pyqt5_hook.py
from PyInstaller import hooks

# 移除PyQt5相关钩子注册项，阻止post‑graph加载hook‑PyQt5.py
for key in list(hooks.module_hooks.keys()):
    if "PyQt5" in key:
        del hooks.module_hooks[key]
