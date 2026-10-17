import pygame

# 纹理图集切分
def split_image(image,raw,rate,height,width,tile_num):
    tiles = []
    for i in range(raw):
        for j in range(rate):
            if i*tile_num+j >= tile_num*tile_num:
                break
            tiles.append(image.subsurface((j*width,height*i,width,height)))
    return tiles

