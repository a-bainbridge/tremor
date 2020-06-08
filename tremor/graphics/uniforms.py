from typing import Dict, Callable, List

from OpenGL.GL import *

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
    'mat3': glUniformMatrix3fv,  # values as single parameter
    'mat4': glUniformMatrix4fv  # values as single parameter
}
u_type_default_value_args: Dict[str, list] = {
    # outer list matches parameter mapping for gl uniform functions. see u_types
    'float': [0.0],
    'vec2': [0., 0.],
    'vec3': [0., 0., 0.],
    'vec4': [0., 0., 0., 0.],
    'int': [0],
    'bool': [False],
    'ivec2': [0, 0],
    'ivec3': [0, 0, 0],
    'mat3': [[[0, 0, 0], [0, 0, 0], [0, 0, 0]]],
    'mat4': [[[0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0]]]
}
u_type_default_args: Dict[str, list] = {  # anything not present in this list can be assumed []
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
def add_uniform_to_all(name: str, u_type: str):
    for prog in shaders.get_programs():
        prog.add_primitive_uniform(name, u_type)


def update_all_uniform(name: str, values: list):
    for prog in shaders.get_programs():
        prog.update_uniform(name, values)


def init_all_uniforms():
    for prog in shaders.get_programs():
        prog.init_uniforms()


class Uniform:
    def __init__(self, name: str, loc, values: list, u_type: 'ShaderStructDef'):
        self.name = name # this is the instance name if this is the root (surface) object
        self._loc = loc
        self.values: list = values
        self.u_type: 'ShaderStructDef' = u_type
        self.struct:'ShaderStruct' = None
        if not self.u_type.primitive:
            self.struct = u_type.generate_struct(name)

    def _get_uniform_func(self) -> Callable:
        return u_types[self.u_type.primitive_type]

    def _get_args(self) -> list:
        return [self._loc, ] + self.values

    def set_location (self, program):
        if self.u_type.primitive:
            self._loc = glGetUniformLocation(program, self.name)
        else:
            for u in self.struct.uniforms:
                u.set_location(program)

    def call_uniform_func(self, values:list=None):
        if self.u_type.primitive:
            if values is not None:
                self.values = values
            if self.values is None or len(self.values) == 0:
                print('no value set for uniform %s' % self.name)
                return
            self._get_uniform_func()(*self._get_args())
        else:
            for u in self.struct.uniforms:
                u.call_uniform_func()

class ShaderStructDef:
    @staticmethod
    def from_uniforms(name:str, uniforms: List[Uniform]) -> "ShaderStructDef":
        factory = ShaderStructDef(name=name, primitive=False)
        for u in uniforms:
            factory.set_field(u.name, u.u_type)
        return factory

    @staticmethod
    def as_primitive (name:str, u_type:str) -> 'ShaderStructDef':
        return ShaderStructDef(name=name, primitive=True, u_type=u_type)

    def __init__(self, name:str, primitive:bool, u_type:str=None, **kwargs):
        self.name = name
        self.primitive = primitive
        self.primitive_type:str = u_type
        self._fields:Dict[str, 'ShaderStructDef'] = {} # fields is uniform_name: uniform_type
        for k,v in kwargs.items():
            self.set_field(k, v)

    def set_field (self, field_name, field_type: 'ShaderStructDef'):
        self._fields[field_name] = field_type

    def _get_uniforms (self) -> List[Uniform]: # this is STRICTLY 1D (although Uniforms can contain other uniforms)
        l = []
        for f, value in self._fields.items():
            if value.primitive:
                l.append(Uniform(
                    '.%s'%value.name,
                    loc=None,
                    values=[],
                    u_type=value
                ))
            else:
                l += value._get_uniforms()
        return l
    def generate_struct (self, name:str) -> 'ShaderStruct':
        if self.primitive:
            raise Exception("Can't generate a struct for a primitive field!")
        return ShaderStruct(name, self._get_uniforms())


class ShaderStruct:
    def __init__ (self, instance_name:str, uniforms:List[Uniform]):
        self.instance_name = instance_name
        self.uniforms = uniforms
        for u in self.uniforms:
            u.name = self.instance_name + u.name

# class StructUniform(Uniform):
#     def __init__(self, name: str, struct_factory:ShaderStructFactory):
#         super().__init__(name)
#         self.name = name
#         self.struct_def:ShaderStruct = struct_factory.generate_struct()
#
#     def call_uniform_func(self):