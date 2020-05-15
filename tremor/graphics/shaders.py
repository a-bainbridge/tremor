import configparser
from typing import List

from OpenGL.GL.shaders import ShaderCompilationError

from tremor.graphics.surfaces import Material
from tremor.graphics.uniforms import *
import re as regex

PROGRAMS: Dict[str, 'MeshShader'] = {}

# object programs
def get_program(name: str) -> 'MeshShader':
    try:
        return PROGRAMS[name]
    except ValueError:
        raise Exception(f'{name} is not a valid program name.')

def get_default_program() -> 'MeshShader':
    return get_program('default')

def get_programs() -> List['MeshShader']:
    return list(PROGRAMS.values())

def create_all_programs(filepath='data/shaders/programs.ini',
                        vertex_location: str = 'data/shaders/vertex',
                        fragment_location: str = 'data/shaders/fragment') -> None:
    # read the config file
    config_parser = configparser.ConfigParser()
    config_parser.read(filepath, encoding="UTF-8")
    out = {}
    for program in config_parser.sections():
        program_name = str(program)
        out[program_name] = {}
        for key in config_parser[program_name]:
            value = config_parser[program_name][key]
            out[program_name][key] = str(value)

    # read files, load programs
    unique_vertex_shaders = []
    unique_fragment_shaders = []
    for prog in out.values():
        if prog['vertex'] not in unique_vertex_shaders:
            unique_vertex_shaders.append(prog['vertex'])
        if prog['fragment'] not in unique_fragment_shaders:
            unique_fragment_shaders.append(prog['fragment'])

    # compile the shaders uniquely, so that we don't compile one more than once
    compiled_vertex_shaders = {}
    compiled_fragment_shaders = {}
    fragment_shader_inputs = {}
    for vertex_shader in unique_vertex_shaders:
        txt = open(f'{vertex_location}/{vertex_shader}.glsl', 'r').read()
        compiled_vertex_shaders[vertex_shader] = create_shader(GL_VERTEX_SHADER, txt)

    for fragment_shader in unique_fragment_shaders:
        txt = open(f'{fragment_location}/{fragment_shader}.glsl', 'r').read()
        fragment_shader_inputs[fragment_shader] = ShaderInput.from_shader_source(txt)
        compiled_fragment_shaders[fragment_shader] = create_shader(GL_FRAGMENT_SHADER, txt)

    # then go back through programs and query the compiled shaders
    # also query for shader inputs
    # then create the program
    for prog_name, prog in out.items():
        create_program(prog_name, compiled_vertex_shaders[prog['vertex']], compiled_fragment_shaders[prog['fragment']], fragment_shader_inputs[prog['fragment']])

    # delete the shaders
    for shad in list(compiled_vertex_shaders.values()) + list(compiled_fragment_shaders.values()):
        glDeleteShader(shad)


def create_shader(type, source) -> object:
    shader = glCreateShader(type)
    glShaderSource(shader, source)
    glCompileShader(shader)
    status = glGetShaderiv(shader, GL_COMPILE_STATUS)
    if status == GL_FALSE:
        raise ShaderCompilationError(
            "Compilation failure for %s\n%s" % (str(type), glGetShaderInfoLog(shader).decode()))
    return shader


def create_program(name: str, compiled_vertex, compiled_fragment, inputs):
    PROGRAMS[name] = MeshShader(name, compiled_vertex, compiled_fragment, inputs)

class ShaderInput:
    @staticmethod
    def from_shader_source (shader_source:str) -> List['ShaderInput']:
        """
        METHODOLOGY of SHADER INPUTS
        Scraping Inputs from the Shaders Themselves

        what:
        given a shader source (a string, the literal program), scan through each line and find lines
        starting with 'uniform' (which is the only type of shader input),
        and ending with a comment starting with '//mat:'
        For example:
        uniform blah blah blah blah;//mat:default_value

        how:
        this built-in comment syntax easily identifies the location of said material input by placing it DIRECTLY beside where it is.
        this method allows for easy parsing, by simply determining material inputs, their types and default values

        why:
        pros:
         - no need to retype input name or type anywhere
         - easily expands to higher-level shader compilation
         - easy to locate

        cons:
         - somewhat ambiguous and the format is arbitrary
         - a little hacky
         - all in all seems a bit distasteful
        """
        lines = shader_source.split('\n')
        uniforms = []
        for l in lines:
            if l[:len('uniform')] == 'uniform':
                uniforms.append(l)
        inputs = []
        find_input = regex.compile(r'uniform\s(\w+)\s(\w+);//mat') # 'uniform\s(\w+)\s(\w+);//mat\:(.*)'
        for u in uniforms:
            m = find_input.match(u)
            if m is not None:
                inputs.append(m.groups())

        # convert inputs into shader inputs : [type, name]
        shader_inputs = []
        for i in inputs:
            typ = i[0]
            name = i[1]
            is_texture = False
            if typ in u_type_default_args:
                default_args = u_type_default_args[typ]
            else:
                default_args = []
            if typ in u_type_default_value_args:
                default_value = u_type_default_value_args[typ]
            else:
                default_value = [0]
                if typ=='sampler2D':
                    is_texture=True
            shader_inputs.append(ShaderInput(name, typ, default_args, default_value, is_texture))
        return shader_inputs
    def __init__ (self, name:str, u_type='float', default_args=[], value:list=[0.0], is_texture=False):
        self.name = name
        self.u_type = u_type
        self.default_args = default_args
        self._value = value
        self.is_texture = is_texture # in the case where this is true, the name is the same as the MaterialTexture type flag.
            # @see: MaterialTexture.COLOR for example. If it isn't, it will throw a KeyError in MeshShader
        self.texture_type = None
        if self.is_texture:
            self.texture_type = self.name
    def set_value (self, value):
        if len(self._value)==1:
            self._value = [value]
        else:
            self._value = value
    def get_value (self):
        if len(self._value)==1:
            return self._value[0]
        else:
            return self._value
    def get_uniform_args (self) -> list:
        return self.default_args + self._value

class MeshShader:
    def __init__(self, name: str, compiled_vertex, compiled_fragment, inputs:List[ShaderInput]=[]):
        self.name = name
        self.program = glCreateProgram()
        self.uniforms:Dict[str, Uniform] = {}
        self.inputs:List[ShaderInput] = inputs
        self.add_uniforms_from_inputs()

        glAttachShader(self.program, compiled_vertex)
        glAttachShader(self.program, compiled_fragment)
        glLinkProgram(self.program)
        status = glGetProgramiv(self.program, GL_LINK_STATUS)
        if status == GL_FALSE:
            print("Linker failure: " + str(glGetProgramInfoLog(self.program)))

    def add_uniforms_from_inputs (self):
        for i in self.inputs:
            if not self.check_is_uniform(i.name) and not i.is_texture:
                self.add_uniform(i.name, i.u_type)

    def add_uniform (self, name: str, u_type: str):
        if not u_type in u_types.keys():
            raise Exception(f'uniform type {u_type} is not a valid type')

        self.uniforms[name] = Uniform(
            name=name,
            loc=None,
            values=[],
            u_type=u_type
        )

    def update_uniform(self, name: str, values: list = None):
        glUseProgram(self.program)
        self.check_is_uniform(name)
        self.uniforms[name].call_uniform_func(values)

    def init_uniforms(self):
        glUseProgram(self.program)
        for n, u in self.uniforms.items():
            u.loc = glGetUniformLocation(self.program, u.name)

    def check_is_uniform(self, name: str) -> bool:  # not a hard stop, but warning
        if not name in self.uniforms:
            # print('%s is not a uniform!' % name)
            return False
        return True

    def set_uniform_values(self, name: str, values: list):
        self.check_is_uniform(name)
        self.uniforms[name].values = values

    # get a material with relevant properties for this shader
    def create_material (self, name=None) -> Material:
        if name is None:
            name = f'{self.name}_mat'
        mat = Material(name)
        for prop in self.inputs:
            if prop.is_texture: continue # don't set default textures, because empty textures are created in Material.__init__
            mat.set_property(prop.name, prop.get_value())
        return mat

    # set uniforms for this shader from the provided material that are relevant
    def use_material (self, mat:Material):
        for inp in self.inputs:
            if inp.is_texture:
                mat_tex = mat.get_mat_texture(inp.texture_type)
                glUniform1i(
                    glGetUniformLocation(self.program, mat_tex.tex_type),
                    mat_tex.texture.index
                )
            else:
                inp.set_value(mat.get_property(inp.name))
                self.update_uniform(inp.name, inp.get_uniform_args())