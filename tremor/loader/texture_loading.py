import os
from typing import Dict

import PIL
import numpy as np
from OpenGL import GL
from PIL import Image
import deprecated

from tremor.graphics.opengl_primitives import get_default_sampler
from tremor.graphics.surfaces import TextureUnit


TEXTURES: Dict[str, TextureUnit] = {}
TEXTURE_TABLE: Dict[int, TextureUnit] = {}
# https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html
acceptable_file_types = ['bmp', 'png', 'jpg', 'jpeg', 'ppm']


def get_image_data(filepath):
    try:
        img = Image.open(filepath)
        print(img.format, img.size, img.mode)
    except PIL.UnidentifiedImageError as e:
        print(e)
        return
    return np.asarray(img, dtype='uint8')


def load_texture_by_name(name, idx):
    files = os.listdir("./data/textures/" + name.split("/")[0])
    for f in files:
        try:
            end = f[f.index('.') + 1:]
        except ValueError:
            continue
        if not end in acceptable_file_types:
            continue
        filename = f[:f.index('.')]
        if filename == name.split("/")[1]:
            print('loaded texture %s' % filename)
            load_texture('%s/%s' % ("./data/textures/" + name.split("/")[0], f), filename, {}, idx)
            return
    load_texture("./data/textures/defaults/missing.png", name.split("/")[0], {}, idx)


def load_texture(filepath, name: str = None, config=None, idx=-1):
    if config is None:
        config = {}
    if name is None: name = filepath
    data = get_image_data(filepath)
    width = len(data[0])
    height = len(data)
    if idx != -1:
        TEXTURE_TABLE[idx] = TextureUnit.generate_texture()
        img_format = config['format'] if 'format' in config else GL.GL_RGBA # todo: uh
        samp = get_default_sampler()
        samp.wrapS = GL.GL_REPEAT
        samp.wrapT = GL.GL_REPEAT
        TEXTURE_TABLE[idx].setup_texture2D(data.flatten(), width, height, img_format, samp)
    else:
        TEXTURES[name] = TextureUnit.generate_texture()
        img_format = config['format'] if 'format' in config else GL.GL_RGBA
        samp = get_default_sampler()
        samp.wrapS = GL.GL_REPEAT
        samp.wrapT = GL.GL_REPEAT
        TEXTURE_TABLE[idx].setup_texture2D(data.flatten(), width, height, img_format, samp)


def load_all_textures(path='./data/textures', config=None):
    if config is None:
        config = {}
    files = os.listdir(path)
    for f in files:
        try:
            end = f[f.index('.') + 1:]
        except ValueError:
            continue
        if not end in acceptable_file_types:
            continue
        filename = f[:f.index('.')]
        print('loaded texture %s' % filename)
        load_texture('%s/%s' % (path, f), filename, config[filename] if filename in config else {})

def get_texture(name: str) -> TextureUnit:
    if not name in TEXTURES.keys():
        raise Exception('%s not in TEXTURES' % name)
    return TEXTURES[name]
