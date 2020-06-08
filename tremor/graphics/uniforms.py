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
    """
    Since Uniforms have gotten increasingly sophisticated, I gave up on making an approachable constructor
    Instead, for quick construction, I recommend using the static constructor methods
    """

    @staticmethod
    def as_primitive(name: str, u_type: str) -> 'Uniform':
        return Uniform(name, None, [], ShaderStructDef.as_primitive(name, u_type))

    @staticmethod
    def as_struct(name:str, u_type: 'ShaderStructDef') -> 'Uniform':
        return Uniform(name, None, [], u_type)

    def __init__(self, name: str, loc, values: list, u_type: 'ShaderStructDef'):
        self.name = name  # this is the instance name if this is the root (surface) object
        # If it is not the root object, self.name and self.u_type.name are interchangeable
        # otherwise, they must be different (it would look something like `struct Rect { . . . } Rect;`)
        self._loc = loc
        self.values: list = values
        self.u_type: 'ShaderStructDef' = u_type
        self.fields: List[Uniform] = []
        self.is_list = False
        self.list_children: List[Uniform] = []
        if not self.u_type.primitive:
            self.fields = u_type.get_uniforms()

    def _get_uniform_func(self) -> Callable:
        return u_types[self.u_type.primitive_type]

    def _get_args(self) -> list:
        return [self._loc, ] + self.values

    def set_location(self, program):
        if self.u_type.is_simple_primitive():
            self._loc = glGetUniformLocation(program, self.name)
        else:
            for u in self.fields:
                u.set_location(program)

    def call_uniform_func(self, values: list = None):
        if self.u_type.is_simple_primitive():
            if values is not None:
                self.values = values
            if self.values is None or len(self.values) == 0:
                print('no value set for uniform %s' % self.name)
                return
            self._get_uniform_func()(*self._get_args())
        else:
            for u in self.fields:
                u.call_uniform_func()


class ShaderArrayDef:
    def __init__(self, name: str, u_type: 'ShaderStructDef', length: int):
        self.name = name
        self.u_type = u_type
        self.length = length

    def get_uniforms(self) -> List[Uniform]:
        us = []
        for i in range(self.length):
            if self.u_type.is_simple_primitive():
                us.append(Uniform(f'{self.name}[{i}]', loc=None, values=[], u_type=self.u_type))
            else:
                us += self.u_type.get_uniforms()
        return us


class ShaderStructDef:

    @staticmethod
    def as_primitive(name: str, u_type: str) -> 'ShaderStructDef':
        return ShaderStructDef(name=name, primitive=True, primitive_type=u_type, is_list=False)

    @staticmethod
    def as_primitive_list (name:str, u_type:str, length:int) -> 'ShaderStructDef':
        return ShaderStructDef(name=name, primitive=True, is_list=True, list_length=length, primitive_type=u_type)

    def __init__(self, name: str, primitive: bool, is_list: bool, list_length: int = None, primitive_type: str = None,
                 **kwargs):
        # NOTE: just because self.primitive = True doesn't mean it's not a LIST
        self.name = name
        self.primitive = primitive
        self.primitive_type: str = primitive_type
        self.is_list = is_list
        self.list_length = list_length
        self._fields: Dict[str, 'ShaderStructDef'] = {}  # fields is uniform_name: uniform_type
        self.set_fields_from_dict(kwargs)

    def set_fields_from_dict(self, dictionary: dict):
        for k, v in dictionary:
            self.set_field(k, v)

    def set_field(self, field_name, field_type: 'ShaderStructDef'):
        self._fields[field_name] = field_type

    def _get_list_child(self) -> 'ShaderStructDef':  # NOTE: lists cannot be contained in lists (thank god)
        s = ShaderStructDef(self.name, primitive=self.primitive, is_list=False, primitive_type=self.primitive_type)
        s.set_fields_from_dict(s._fields)
        return s

    def _get_uniforms(self, name: str) -> List[Uniform]:
        # NOTE: this is a STRICTLY 1D LIST
        l = []
        if self.is_list:
            for i in range(self.list_length):
                child_name = f'{name}.[{i}]'
                if self.primitive:
                    l.append(Uniform.as_primitive(child_name, self.primitive_type))
                else:
                    l += self._get_list_child()._get_uniforms(child_name)
        else:
            for f, value in self._fields.items():
                child_name = '%s.%s'%(name, value.name)
                if value.is_simple_primitive():
                    l.append(Uniform(
                        child_name,  # end of recursion
                        loc=None,
                        values=[],
                        u_type=value
                    ))
                else:
                    l += value._get_uniforms(child_name)  # recursion continues,
        return l

    def get_uniforms(self) -> List[Uniform]:
        if self.is_simple_primitive():
            raise Exception("Can't generate a struct for a primitive field!")
        return self._get_uniforms(self.name)

    def is_simple_primitive (self) -> bool:
        return self.primitive and not self.is_list


class ShaderStruct:
    def __init__(self, instance_name: str, uniforms: List[Uniform]):
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
