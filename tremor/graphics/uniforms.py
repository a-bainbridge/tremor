import copy
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


def add_primitive_uniform_to_all(name: str, u_type: str):
    for prog in shaders.get_programs():
        prog.add_primitive_uniform(name, u_type)

def add_uniform_to_all (unif: 'Uniform'):
    for prog in shaders.get_programs():
        prog.add_uniform(unif.copy())


def update_all_uniform(name: str, values: list):
    for prog in shaders.get_programs():
        prog.update_uniform(name, values)

def BAD_set_all_uniform_by_property_chain (name:str, property_chain:str, values:list):
    props = property_chain.split('.')
    p_i = -1
    for p in props:
        p_i += 1
        try:
            i = int(p)
            props[p_i] = i
        except: continue
    for prog in shaders.get_programs():
        u = prog.get_uniform(name)
        index = 0
        while index < len(props):
            s = u
            if type(u) == Uniform:
                s = u.get_fields()
            u = s[props[index]]
            index += 1
        u.set_values(values)
        prog.use()
        u.call_uniform_func()

def init_all_uniforms():
    for prog in shaders.get_programs():
        prog.init_uniforms()


class Uniform:
    """
    Since Uniforms have gotten increasingly sophisticated, I gave up on making an approachable constructor
    Instead, for quick construction, I recommend using the static constructor methods
    """

    @staticmethod
    def as_primitive(name: str, u_type: str, localname='') -> 'Uniform':
        return Uniform(name, None, [], ShaderStructDef.as_primitive(name, u_type), local_name=localname)

    @staticmethod
    def as_struct(name: str, u_type: 'ShaderStructDef') -> 'Uniform':
        return Uniform(name, None, [], u_type)

    def __init__(self, name: str, loc, values: list, u_type: 'ShaderStructDef', local_name=''):

        self.name = name  # this is the instance name if this is the root (surface) object
        # If it is not the root object, self.name and self.u_type.name are interchangeable
        # assume `struct Rect { vec2 corner; vec2 size; };` for example purposes
        # otherwise, they must be different (it would look something like `struct Rect { . . . } Rect;`)

        self.local_name: str = local_name  # for the root, this is "" because it's irrelevant.
        # This is only useful for accessing uniforms
        # for example, (using Rect example), given `Rect yeet = Rect(vec2(0.), vec2(1.));`,
        # self.name for the `yeet.corner` property would be "yeet.corner", while self.local_name SHOULD be "corner"
        self._loc = loc
        self.values: list = values
        self.u_type: 'ShaderStructDef' = u_type
        self.fields: 'ShaderStruct' = None
        if not self.u_type.is_simple_primitive():
            self.fields = u_type.get_struct(self.name)

    def copy (self) -> 'Uniform':
        return Uniform(name=self.name, loc=None, values=[], u_type=self.u_type, local_name=self.local_name)

    def set_values (self, values:list):
        self.values = values
        if not self.u_type.is_simple_primitive():
            print('WARNING: set values to %s that is not a primitive'%self.name)

    def set_property (self, prop:str, values:list):
        print("WARNING: this function isn't ready for use yet")

    def get_fields(self) -> 'ShaderStruct':
        return self.fields

    def _get_uniform_func(self) -> Callable:
        return u_types[self.u_type.primitive_type]

    def _get_args(self) -> list:
        return [self._loc, ] + self.values

    def set_location(self, program: GLuint):
        if self.u_type.is_simple_primitive():
            self._loc = glGetUniformLocation(program, self.name)
            # if self._loc == -1:
            #     print(f"WARNING: missing location for '{self.name}'")
        else:
            self.fields.recursive_uniform_function_call(Uniform.set_location, (program,))

    def call_uniform_func(self, values: list = None):
        if self.u_type.is_simple_primitive():
            if values is not None:
                self.values = values
            if self.values is None or len(self.values) == 0:
                print('no value set for uniform %s' % self.name)
                return
            self._get_uniform_func()(*self._get_args())
        else:
            self.fields.recursive_uniform_function_call(Uniform.call_uniform_func, ())


# class ShaderArrayDef:
#     def __init__(self, name: str, u_type: 'ShaderStructDef', length: int):
#         self.name = name
#         self.u_type = u_type
#         self.length = length
#
#     def get_struct(self) -> List[Uniform]:
#         us = []
#         for i in range(self.length):
#             if self.u_type.is_simple_primitive():
#                 us.append(Uniform(f'{self.name}[{i}]', loc=None, values=[], u_type=self.u_type))
#             else:
#                 us += self.u_type.get_struct(self.name)
#         return us


class ShaderStructDef:

    @staticmethod
    def as_primitive(name: str, u_type: str) -> 'ShaderStructDef':
        return ShaderStructDef(type_name=name, primitive=True, primitive_type=u_type, is_list=False)

    @staticmethod
    def as_primitive_list(name: str, u_type: str, length: int) -> 'ShaderStructDef':
        return ShaderStructDef(type_name=name, primitive=True, is_list=True, list_length=length, primitive_type=u_type)

    def __init__(self, type_name: str, primitive: bool, is_list: bool, list_length: int = None, primitive_type: str = None,
                 **kwargs):
        # NOTE: just because self.primitive = True doesn't mean it's not a LIST
        self.type_name = type_name
        self.primitive = primitive
        self.primitive_type: str = primitive_type
        self.is_list = is_list  # if it is a list, then it is a list containing THIS type
        self.list_length = list_length
        self._fields: Dict[str, 'ShaderStructDef'] = {}  # fields is uniform_name: uniform_type
        self.set_fields_from_dict(kwargs)

    def set_fields_from_dict(self, dictionary: dict):
        for k, v in dictionary.items():
            self.set_field(k, v)

    def set_field(self, field_name, field_type: 'ShaderStructDef'):
        self._fields[field_name] = field_type

    def set_primitive_field(self, name:str, u_type:str):
        self.set_field(name, ShaderStructDef.as_primitive(name, u_type))

    def _get_list_child_instance(self) -> 'ShaderStructDef':  # NOTE: lists cannot be contained in list
        s = ShaderStructDef(self.type_name, primitive=self.primitive, is_list=False, primitive_type=self.primitive_type)
        s.set_fields_from_dict(self._fields)
        return s

    def _get_struct(self, name: str) -> 'ShaderStruct':
        uniforms:List[Uniform] = []
        children:List['ShaderStruct'] = []
        if self.is_list:
            for i in range(self.list_length):
                child_name = f'{name}[{i}]'
                if self.primitive:
                    uniforms.append(Uniform.as_primitive(child_name,
                                                         self.primitive_type))  # does not require local name; is list item
                else:
                    children.append(self._get_list_child_instance()._get_struct(child_name))
        else:
            for f, value in self._fields.items():
                child_name = '%s.%s' % (name, f)
                if value.is_simple_primitive():
                    uniforms.append(Uniform(
                        child_name,  # end of recursion
                        loc=None,
                        values=[],
                        u_type=value,
                        local_name=value.type_name
                    ))
                else:
                    children.append(value._get_struct(f))  # recursion continues,
        return ShaderStruct(name, uniforms, children, is_list=self.is_list)

    def get_struct(self, name) -> 'ShaderStruct':
        if self.is_simple_primitive():
            raise Exception("Can't generate a struct for a primitive field!")
        return self._get_struct(name)

    def is_simple_primitive(self) -> bool:
        return self.primitive and not self.is_list


class ShaderStruct:
    def __init__(self, instance_name: str, uniforms: List[Uniform], children: List['ShaderStruct'], is_list: bool):
        # self.uniforms and self.children are both children of this instance, only types are different
        self.instance_name = instance_name
        self.children: List['ShaderStruct'] = children
        self.uniforms: List[Uniform] = uniforms
        self._uniform_dict: Dict[str, Uniform] = {}
        self._children_dict: Dict[str, 'ShaderStruct'] = {}
        self.is_list = is_list
        self.list_has_children = len(children) > 0 and is_list
        self.has_children = len(children) > 0
        if not is_list:
            # then it's unordered, and these dicts need to be filled
            for u in self.uniforms:
                if u.local_name == '':
                    raise Exception(f'{u.name} does not have a local name!')
                self._uniform_dict[u.local_name] = u
            for c in self.children:
                self._children_dict[c.instance_name] = c

    def __getitem__(self, item):
        if type(item) == int:
            return self.get_list_item(item)
        elif type(item) == str:
            return self.get_property(item)
        else:
            raise Exception(f"{self.instance_name} does not know what to do with {item}!")

    def get_list_item(self, index: int):
        if self.list_has_children:
            return self.get_list_struct(index)
        else:
            return self.get_list_uniform(index)

    def get_list_uniform(self, index: int) -> Uniform:
        return self.uniforms[index]

    def get_list_struct(self, index: int) -> 'ShaderStruct':
        return self.children[index]

    def get_uniform(self, u_name: str) -> Uniform:
        if self.is_list:
            raise Exception(f"{self.instance_name} is not a struct containing unordered uniforms.")
        if u_name in self._uniform_dict.keys():
            return self._uniform_dict[u_name]
        raise Exception(f"There is no uniform with the local name '{u_name}'")

    def get_struct(self, struct_name: str) -> 'ShaderStruct':
        if self.is_list:
            raise Exception(f"{self.instance_name} is not a struct containing unordered structs.")
        if struct_name in self._children_dict:
            return self._children_dict[struct_name]
        raise Exception(f"There is no internal struct property called '{struct_name}'")

    def get_property(self, property_name: str):
        if property_name in self._uniform_dict.keys():
            return self._uniform_dict[property_name]
        if property_name in self._children_dict.keys():
            return self._children_dict[property_name]
        raise Exception(f"There is no internal property called '{property_name}'")

    def recursive_uniform_function_call(self, func: Callable, args: tuple):
        for u in self.uniforms:
            func(u, *args)
        for c in self.children:
            c.recursive_uniform_function_call(func, args)
