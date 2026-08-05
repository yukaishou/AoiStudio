import os

from PIL import Image

def to_ico(img_path,output_path):
    if os.path.exists(output_path):
        os.remove(output_path)
    img = Image.open(img_path)
    img.save(output_path, format='ICO', sizes=[(256, 256), (48, 48), (32, 32), (16, 16)])