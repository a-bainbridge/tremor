import re as ree
from typing import Dict, Callable, List, Any, Tuple
import numpy as np

import glm
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
u_type_default_value_args: Dict[str, tuple] = {
    # outer list matches parameter mapping for gl uniform functions. see u_types
    'float': (0.0,),
    'vec2': (0., 0.),
    'vec3': (0., 0., 0.),
    'vec4': (0., 0., 0., 0.),
    'int': (0,),
    'bool': (False,),
    'ivec2': (0, 0),
    'ivec3': (0, 0, 0),
    'mat3': (((0, 0, 0), (0, 0, 0), (0, 0, 0)),),
    'mat4': (((0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0)),)
}
u_type_default_args: Dict[str, list] = {  # anything not present in this list can be assumed []
    'mat3': [1, GL_FALSE],
    'mat4': [1, GL_FALSE]
}
u_type_get_default_args = lambda typ: [] if typ not in u_type_default_args.keys() else u_type_default_args[typ]
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
GLOBAL_UNIFORMS: Dict[str, 'ExpandedUniform'] = {}  # simplified, without tree structure of uniforms
GLOBAL_UBO: Dict[str, 'UBO'] = {}
GLOBAL_UNIFORM_UPDATE_QUEUE: List[str] = []  # queue for uniforms having been updated


def add_global_ubo(ubo: 'UBO'):
    GLOBAL_UBO[ubo.shadername] = ubo
    _add_ubo_to_all_programs(ubo)


def get_global_ubo(shadername: str) -> 'UBO':
    return GLOBAL_UBO[shadername]


def _add_ubo_to_all_programs(ubo: 'UBO'):
    for prog in shaders.get_programs():
        prog.apply_ubo(ubo)


def add_primitive_global_uniform(name: str, u_type: str):
    unif = Uniform.as_primitive(name, u_type, is_global=True)
    add_global_uniform(unif)


def add_global_uniform(unif: 'Uniform'):
    GLOBAL_UNIFORMS[unif.name] = ExpandedUniform(unif)
    add_uniform_to_all_programs(unif)


def add_uniform_to_all_programs(unif: 'Uniform'):
    # NOTE: if you're adding a global, use add_global_uniform instead.
    #       Only use this method if you want to add a uniform controlled
    #       per-entity or something for programs (like the model view matrix)
    for prog in shaders.get_programs():
        prog.add_uniform(unif.copy())


def get_global_uniform_leaf(leaf_name: str) -> 'Uniform':
    expr = ree.compile('(\w+)(.+)?')
    match = expr.match(leaf_name).groups()
    root_name = match[0]
    if match[1] is not None:
        return GLOBAL_UNIFORMS[root_name].expanded(leaf_name)
    else:
        return GLOBAL_UNIFORMS[root_name].uniform


def update_global_uniform(name: str, value):
    get_global_uniform_leaf(name).smart_set_value(value)


def update_global_uniform_struct(name: str, **values):
    # convenience function, set struct args based on kwargs
    for k, v in values.items():
        update_global_uniform(f'{name}.{k}', v)


def in_queue(global_uniform_name: str):
    return global_uniform_name in GLOBAL_UNIFORM_UPDATE_QUEUE


def flush_queue():
    global GLOBAL_UNIFORM_UPDATE_QUEUE
    GLOBAL_UNIFORM_UPDATE_QUEUE = []


def get_queue():
    return GLOBAL_UNIFORM_UPDATE_QUEUE


def BAD_update_all_uniform(name: str, values: list):
    for prog in shaders.get_programs():
        prog.update_uniform(name, values)


def BAD_set_all_uniform_by_property_chain(name: str, property_chain: str, values: list):
    props: List[Any] = property_chain.split('.')
    p_i = -1
    for p in props:
        p_i += 1
        try:
            i = int(p)
            props[p_i] = i
        except:
            continue
    for prog in shaders.get_programs():
        u = prog.get_uniform(name)
        index = 0
        while index < len(props):
            u = u[props[index]]
            index += 1
        u.set_raw_values(values)
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
    def as_primitive(name: str, u_type: str, is_global=False) -> 'Uniform':
        return Uniform(name, None, [], ShaderStructDef.as_primitive(name, u_type, is_global=is_global), local_name=name)

    @staticmethod
    def as_struct(name: str, u_type: 'ShaderStructDef') -> 'Uniform':
        return Uniform(name, None, [], u_type)

    def __init__(self, name: str, loc, values: list, u_type: 'ShaderStructDef', local_name='', is_global=False):

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
        self.expanded: 'ExpandedUniform' = None
        if not self.u_type.is_simple_primitive():
            self.fields = u_type.get_struct(self.name)
            self.expanded = ExpandedUniform(self)

    def is_global(self):
        return self.u_type.is_global

    def copy(self) -> 'Uniform':
        return Uniform(name=self.name, loc=None, values=[], u_type=self.u_type, local_name=self.local_name)

    def no_values(self) -> bool:
        return self.values is None or len(self.values) == 0

    def values_from_other(self, other: 'Uniform'):
        if self.u_type.is_simple_primitive() and other.u_type.is_simple_primitive():
            self.set_raw_values([v for v in other.values])
        else:
            for u in self.expanded.all_leaves:
                u.set_raw_values([v for v in other.expanded.expanded(u.name).values])

    def set_raw_values(self, values: list):
        self.values = values
        if not self.u_type.is_simple_primitive():
            print('WARNING: set values to "%s" that is not a primitive' % self.name)

    def smart_set_value(self, value):
        if not self.u_type.is_simple_primitive():
            print(
                'WARNING: setting values to %s that is not a primitive (type %s)' % (self.name, self.u_type.type_name))
        if type(value) != list:
            value = [value]
        self.set_raw_values(u_type_get_default_args(self.u_type.primitive_type) + value)

    def __getitem__(self, prop):
        """
        :param prop: either a string or int representing the child of a struct or list
        :return: Uniform or struct, depending on what you get. You can only usefully access leaf nodes.
        """
        return self.fields[prop]

    def get_fields(self) -> 'ShaderStruct':
        return self.fields

    def _get_uniform_func(self) -> Callable:
        return u_types[self.u_type.primitive_type]

    def _get_args(self) -> list:
        return [self._loc, ] + self.values

    def set_location(self, program: GLuint):
        if self.u_type.is_simple_primitive():
            self._loc = glGetUniformLocation(program, self.name)
            if self._loc == -1:
                print(f"WARNING: missing location for '{self.name}'")
        else:
            self.fields.recursive_uniform_function_call(Uniform.set_location, (program,))

    def call_uniform_func(self, values: list = None):
        if self.u_type.is_simple_primitive():
            if values is not None:
                self.values = values
            if self.no_values():
                print('no value set for uniform %s' % self.name)
                return
            self._get_uniform_func()(*self._get_args())
        else:
            self.fields.recursive_uniform_function_call(Uniform.call_uniform_func, ())

    def recursive_uniform_call(self, uniform_function: Callable, args: tuple):
        self.fields.recursive_uniform_function_call(uniform_function, args)

    def _u_int(self, ul):
        if self.u_type.is_simple_primitive():
            ul.append(self)

    def get_all_leaves(self) -> List['Uniform']:  # return a 1d list of uniforms, including all children
        if self.u_type.is_simple_primitive():
            return [self]
        us: List['Uniform'] = []
        self.fields.recursive_uniform_function_call(Uniform._u_int, (us,))
        return us


class ExpandedUniform:
    def __init__(self, uniform: Uniform):
        self.uniform = uniform
        self.all_leaves: List[Uniform] = uniform.get_all_leaves()
        self._keyed: Dict[str, Uniform] = {}
        for u in self.all_leaves:
            self._keyed[u.name] = u

    def expanded(self, uniform_name_str: str) -> Uniform:
        return self._keyed[uniform_name_str]

    def __getitem__(self, item: str) -> Uniform:
        return self.uniform[item]


class ShaderStructDef:

    @staticmethod
    def as_primitive(name: str, u_type: str, is_global=False) -> 'ShaderStructDef':
        return ShaderStructDef(type_name=name, primitive=True, primitive_type=u_type, is_list=False,
                               is_global=is_global)

    @staticmethod
    def as_primitive_list(name: str, u_type: str, length: int) -> 'ShaderStructDef':
        return ShaderStructDef(type_name=name, primitive=True, is_list=True, list_length=length, primitive_type=u_type)

    def __init__(self, type_name: str, primitive: bool, is_list: bool, list_length: int = None,
                 primitive_type: str = None, is_global: bool = False,
                 **kwargs):
        # NOTE: just because self.primitive = True doesn't mean it's not a LIST
        self.type_name = type_name
        self.primitive = primitive
        self.primitive_type: str = primitive_type
        self.is_list = is_list  # if it is a list, then it is a list containing THIS type
        self.list_length = list_length
        self.is_global = is_global
        self._fields: Dict[str, 'ShaderStructDef'] = {}  # fields is uniform_name: uniform_type
        self.set_fields_from_dict(kwargs)

    def set_fields_from_dict(self, dictionary: dict):
        for k, v in dictionary.items():
            if type(v) == str:
                self.set_field(k, ShaderStructDef.as_primitive(k, v))
            else:
                self.set_field(k, v)

    def set_field(self, field_name, field_type: 'ShaderStructDef'):
        field_type.is_global = self.is_global  # inherit
        self._fields[field_name] = field_type

    def set_primitive_field(self, name: str, u_type: str):
        self.set_field(name, ShaderStructDef.as_primitive(name, u_type))

    def _get_list_child_instance(self) -> 'ShaderStructDef':  # NOTE: lists cannot be contained in list
        s = ShaderStructDef(self.type_name, primitive=self.primitive, is_list=False, primitive_type=self.primitive_type,
                            is_global=self.is_global)
        s.set_fields_from_dict(self._fields)
        return s

    def _get_struct(self, name: str) -> 'ShaderStruct':
        uniforms: List[Uniform] = []
        children: List['ShaderStruct'] = []
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


class UBOElement:  # dataclass
    PRIMITIVE_BASE_ALIGNMENT = {
        # primitive type: number of bytes
        'bool': 4,
        'int': 4,
        'float': 4,
        'vec2': 8,
        'vec3': 16,
        'vec4': 16,
        'mat3': 64,
        'mat4': 64
    }

    def __init__(self, name, base_alignment, number, data):
        self.name = name
        self.base_alignment = base_alignment
        self.number = number
        self.data = data
        # mutable
        self.offset = -1

    def size(self) -> int:
        return self.base_alignment * self.number

    def nearest_offset(self, offset: int) -> int:
        return offset + self.base_alignment - (offset - 1) % self.base_alignment - 1  # don't ask

    def next_offset(self, next: 'UBOElement') -> int:  # return next offset, used for the next element
        return next.nearest_offset(self.offset + self.size())


class UBO:
    """
    Assuming std140 layout for convenience
    """
    _incremental_bind_point = 1  # these are arbitrary, so I'll leave it for now

    @staticmethod
    def from_struct_def(struct_def: ShaderStructDef) -> 'UBO':
        elem = []
        for field_name, field_type in struct_def._fields.items():
            if not field_type.is_simple_primitive():
                raise Exception('UBOs with complex types not supported yet!')
            elem.append(UBOElement(field_name, UBOElement.PRIMITIVE_BASE_ALIGNMENT[field_type.primitive_type], 1, 0))
        return UBO(struct_def.type_name, elem)
        # since you don't declare instances for ubos, the type IS the name of the instance

    def __init__(self, shadername, elements: List[UBOElement]):
        self.shadername = shadername
        self.ubo = glGenBuffers(1)
        self.byte_size = -1
        self.elements = elements  # order matters!
        self.bind_point = UBO._incremental_bind_point
        UBO._incremental_bind_point += 1
        self._keyed_elements: Dict[str, int] = {}
        self._key()
        self._update_elements()
        self.attach_to_ubo_base(self.bind_point)

    def _update_elements(self):
        # each element's <offset> must be a multiple of its <base_alignment>
        if len(self.elements) < 1:
            return
        self.elements[0].offset = 0  # always
        for i in range(1, len(self.elements)):
            self.elements[i].offset = self.elements[i - 1].next_offset(self.elements[i])
        dummy = UBOElement('dummy', 16, 1, 0)
        self.byte_size = self.elements[-1].next_offset(dummy)
        self.bind()
        glBufferData(GL_UNIFORM_BUFFER, self.byte_size, np.zeros(self.byte_size, dtype='float32'), GL_DYNAMIC_DRAW)
        self.unbind()

    def _key(self):
        # perform every time the order or size of the elements changes
        self._keyed_elements = {}
        for i in range(0, len(self.elements)):
            e = self.elements[i]
            self._keyed_elements[e.name] = i

    def _get_keyed(self, name):
        return self.elements[self._keyed_elements[name]]

    def add_element(self, elem: UBOElement):
        self.elements.append(elem)
        self._key()
        self._update_elements()

    def edit_element(self, name, raw_data):
        e = self._get_keyed(name)
        self.bind()
        glBufferSubData(GL_UNIFORM_BUFFER, e.offset, e.size(), raw_data)
        self.unbind()

    def bind(self):
        glBindBuffer(GL_UNIFORM_BUFFER, self.ubo)

    def unbind(self):
        glBindBuffer(GL_UNIFORM_BUFFER, 0)

    def attach_to_ubo_base(self, index: int):
        self.bind()
        glBindBufferBase(GL_UNIFORM_BUFFER, index, self.ubo)
        self.unbind()
