import os
NOT_MISS = -1
MISSING_DIALOG_INDEX = 0
RUNTIME_MISSING_TYPE_TEXTS = [
    "缺少剧本索引文件(config/dialog_index.json)，请关闭该窗口然后在编辑器的文件菜单中点击构建剧本索引"
]
EDITOR_MISSING_TYPE_TEXTS = [
    "缺少剧本索引文件(config/dialog_index.json)，是否构建剧本索引？"
]
def check_game_file_full(path):
    print(path+"/config/dialog_index.json")
    if not os.path.exists(path+"/config/dialog_index.json"):
        return MISSING_DIALOG_INDEX
    return NOT_MISS