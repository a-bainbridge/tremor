import configparser
from typing import List

from OpenGL.GL.shaders import ShaderCompilationError
from tremor.graphics.uniforms import *

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
    for vertex_shader in unique_vertex_shaders:
        txt = open(f'{vertex_location}/{vertex_shader}.glsl', 'r').read()
        compiled_vertex_shaders[vertex_shader] = create_shader(GL_VERTEX_SHADER, txt)

    for fragment_shader in unique_fragment_shaders:
        txt = open(f'{fragment_location}/{fragment_shader}.glsl', 'r').read()
        compiled_fragment_shaders[fragment_shader] = create_shader(GL_FRAGMENT_SHADER, txt)

    # then go back through programs and query the compiled shaders
    # then create the program
    for prog_name, prog in out.items():
        create_program(prog_name, compiled_vertex_shaders[prog['vertex']], compiled_fragment_shaders[prog['fragment']])

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


def create_program(name: str, compiled_vertex, compiled_fragment):
    PROGRAMS[name] = MeshShader(name, compiled_vertex, compiled_fragment)


class MeshShader:
    def __init__(self, name: str, compiled_vertex, compiled_fragment):
        self.name = name
        self.program = glCreateProgram()
        self.uniforms:Dict[str, Uniform] = {}

        glAttachShader(self.program, compiled_vertex)
        glAttachShader(self.program, compiled_fragment)
        glLinkProgram(self.program)
        status = glGetProgramiv(self.program, GL_LINK_STATUS)
        if status == GL_FALSE:
            print("Linker failure: " + str(glGetProgramInfoLog(self.program)))

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
            print('%s is not a uniform!' % name)
            return False
        return True

    def set_uniform_values(self, name: str, values: list):
        self.check_is_uniform(name)
        self.uniforms[name].values = values