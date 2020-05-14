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
    'mat3': glUniformMatrix3fv, # values as single parameter
    'mat4': glUniformMatrix4fv # values as single parameter
}
u_type_default_value_args:Dict[str, list] = { # outer list matches parameter mapping for gl uniform functions. see u_types
    'float': [0.0],
    'vec2': [0., 0.],
    'vec3': [0., 0., 0.],
    'vec4': [0., 0., 0., 0.],
    'int': [0],
    'bool': [False],
    'ivec2': [0, 0],
    'ivec3': [0, 0, 0],
    'mat3': [[[0,0,0],[0,0,0],[0,0,0]]],
    'mat4': [[[0,0,0],[0,0,0],[0,0,0],[0,0,0]]]
}
u_type_default_args:Dict[str, list] = { # anything not present in this list can be assumed []
    'mat3': [1, GL_FALSE],
    'mat4': [1, GL_FALSE]
}
# u_type_convert_func:Dict[str, Callable] = { # given a string, with values separated by commas, serialize that string value using this dict
#     'float': float,
#     'vec2': float,
#     'vec3': float,
#     'vec4': float,
#     'int': int,
#     'bool': bool,
#     'ivec2': int,
#     'ivec3': int,
#     'mat3': float,
#     'mat4': float
# }

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