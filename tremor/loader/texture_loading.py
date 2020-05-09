from typing import Dict

import PIL, os
import numpy as np
from PIL import Image

from tremor.graphics.element_renderer import Texture

TEXTURES:Dict[str, Texture] = {}
# https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html
acceptable_file_types = ['bmp', 'png', 'jpg', 'jpeg', 'ppm']


def get_image_data(filepath):
    try:
        img = Image.open(filepath)
    except PIL.UnidentifiedImageError as e:
        print(e)
        return
    return np.array(img, dtype='uint8')

def add_texture (name:str, config:dict={}):
    load_texture('../../data/textures/defaults/default.jpg', name, config)

def load_texture(filepath, name:str=None, config:dict={}):
    if name is None: name = filepath
    data = get_image_data(filepath)
    width = len(data[0])
    height = len(data)
    TEXTURES[name] = Texture(data.flatten(), name, width, height, **config)


def load_all_textures(path='./data/textures', config:dict={}):
    files = os.listdir(path)
    for f in files:
        try:
            end = f[f.index('.')+1:]
        except ValueError:
            continue
        if not end in acceptable_file_types:
            continue
        filename = f[:f.index('.')]
        print('loaded texture %s'%filename)
        load_texture('%s/%s'%(path, f), filename, config[filename] if filename in config else {})

def get_texture (name:str) -> Texture:
    if not name in TEXTURES.keys():
        raise Exception('%s not in TEXTURES'%name)
    return TEXTURES[name]

if __name__ == '__main__':
    load_all_textures()