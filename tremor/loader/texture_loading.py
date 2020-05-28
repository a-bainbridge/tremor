import os
from typing import Dict

import PIL
import numpy as np
from OpenGL import GL
from PIL import Image

from tremor.graphics.uniforms import gl_compressed_format


class Texture:
    index = 0

    def __init__(self, data: np.ndarray, name: str, width: int = 1, height: int = 1, min_filter=GL.GL_LINEAR,
                 mag_filter=GL.GL_LINEAR,
                 clamp_mode=GL.GL_REPEAT, img_format=GL.GL_RGBA):
        self.data = data
        self.width = width if width > 0 else len(self.data[0])
        self.height = height if height > 0 else len(self.data)
        self.name = name
        self.index = Texture.index
        self.min_filter = min_filter
        self.mag_filter = mag_filter
        self.clamp_mode = clamp_mode
        self.format = img_format
        self.texture = None
        self.init()
        Texture.index += 1  # increment for other textures

    def set_texture(self):
        # https://www.khronos.org/registry/OpenGL-Refpages/gl4/html/glTexImage2D.xhtml
        GL.glTexImage2D(
            GL.GL_TEXTURE_2D,  # target
            0,  # level
            gl_compressed_format[self.format],  # internalformat
            self.width,  # width
            self.height,  # height
            0,  # border
            self.format,  # format
            GL.GL_UNSIGNED_BYTE,  # type
            self.data,  # pixels
        )

        GL.glGenerateMipmap(GL.GL_TEXTURE_2D)

        GL.glTexParameterf(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, self.mag_filter)
        GL.glTexParameterf(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, self.min_filter)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_S, self.clamp_mode)  # u
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_T, self.clamp_mode)  # v

    def bind(self):
        GL.glActiveTexture(GL.GL_TEXTURE0)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.texture)

    def init(self):
        self.texture = GL.glGenTextures(1)
        self.bind()
        # GL.glPixelStorei( GL.GL_UNPACK_ALIGNMENT, 1)
        self.set_texture()


TEXTURES: Dict[str, Texture] = {}
TEXTURE_TABLE: Dict[int, Texture] = {}
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


def load_texture(filepath, name: str = None, config: dict = {}, idx=-1):
    if name is None: name = filepath
    data = get_image_data(filepath)
    width = len(data[0])
    height = len(data)
    if idx != -1:
        TEXTURE_TABLE[idx] = Texture(data.flatten(), name, width, height, **config)
    else:
        TEXTURES[name] = Texture(data.flatten(), name, width, height, **config)


def load_all_textures(path='./data/textures', config: dict = {}):
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


def get_texture(name: str) -> Texture:
    if not name in TEXTURES.keys():
        raise Exception('%s not in TEXTURES' % name)
    return TEXTURES[name]
