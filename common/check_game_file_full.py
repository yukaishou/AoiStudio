import os
NOT_MISS = -1
MISSING_DIALOG_INDEX = 0
def check_game_file_full(path):
    if os.path.exists(path+"/config/dialog_index.json"):
        return MISSING_DIALOG_INDEX
    return NOT_MISS