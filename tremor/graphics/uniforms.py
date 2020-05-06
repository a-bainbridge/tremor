from typing import Dict, Callable

from OpenGL.GL import *
import numpy as np

# https://www.khronos.org/registry/OpenGL-Refpages/gl4/html/glUniform.xhtml
from tremor.graphics import shaders

u_types: Dict[str, Callable] = {
    'float': glUniform1f,
    'vec2': glUniform2f,
    'vec3': glUniform3f,
    'vec4': glUniform4f,
    'int': glUniform1i,
    'bool': glUniform1i,
    'ivec2': glUniform2i,
    'ivec3': glUniform3i,
    'mat3': glUniformMatrix3fv,
    'mat4': glUniformMatrix4fv
}

gl_compressed_format: Dict[int, int] = {  # todo: reconsider
    GL_R: GL_COMPRESSED_RED,
    GL_RG: GL_COMPRESSED_RG,
    GL_RGB: GL_COMPRESSED_RGB,
    GL_RGBA: GL_COMPRESSED_RGBA,
    GL_SRGB: GL_COMPRESSED_SRGB,
    GL_SRGB_ALPHA: GL_COMPRESSED_SRGB_ALPHA
    # exotic formats omitted
}

def add_uniform_to_all (name: str, u_type: str):
    for prog in shaders.get_programs():
        prog.add_uniform(name, u_type)

def update_all_uniform (name: str, values: list):
    for prog in shaders.get_programs():
        prog.update_uniform(name, values)

def init_all_uniforms ():
    for prog in shaders.get_programs():
        prog.init_uniforms()

class Uniform:
    def __init__(self, name: str, loc=None, values: list = None, u_type: str = ''):
        self.name = name
        self.loc = loc
        self.values: list = values
        self.u_type: str = u_type

    def get_uniform_func(self) -> Callable:
        return u_types[self.u_type]

    def get_args(self) -> list:
        return [self.loc, ] + self.values

    def call_uniform_func(self, values: list = None) -> None:
        if not values is None:
            self.values = values
        if self.values is None or len(self.values) == 0:
            print('no value set for uniform %s' % self.name)
            return
        self.get_uniform_func()(*self.get_args())

# a texture is technically a uniform, of type "sampler2D"
# https://stackoverflow.com/questions/8866904/differences-and-relationship-between-glactivetexture-and-glbindtexture
class Texture:
    index = 0

    def __init__(self, data: np.ndarray, name: str, width: int = 1, height: int = 1, min_filter=GL_LINEAR, mag_filter=GL_LINEAR,
                 clamp_mode=GL_CLAMP_TO_EDGE, img_format=GL_RGB):
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
        glTexImage2D(
            GL_TEXTURE_2D,  # target
            0,  # level
            gl_compressed_format[self.format],  # internalformat
            self.width,  # width
            self.height,  # height
            0,  # border
            self.format,  # format
            GL_UNSIGNED_BYTE,  # type
            self.data,  # pixels
        )
        
        glGenerateMipmap(GL_TEXTURE_2D)

        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, self.mag_filter)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, self.min_filter)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, self.clamp_mode)  # u
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, self.clamp_mode)  # v

    def bind(self):
        glActiveTexture(GL_TEXTURE0 + self.index)
        glBindTexture(GL_TEXTURE_2D, self.texture)

    def init(self):
        self.texture = glGenTextures(1)
        self.bind()
        # glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
        self.set_texture()
