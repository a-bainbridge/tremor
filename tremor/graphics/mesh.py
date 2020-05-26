from typing import Dict, List

import OpenGL.GL as GL
import pygltflib

from tremor.graphics import shaders
from tremor.graphics.shaders import MeshProgram
from tremor.graphics.surfaces import Material
import numpy as np

from tremor.loader.texture_loading import TEXTURE_TABLE
from tremor.math.transform import Transform


class Mesh:
    def __init__(self):
        self.vaoID = GL.glGenVertexArrays(1)
        self.program:MeshProgram = shaders.get_default_program()
        self.gl_program = self.program.program
        self.is_scene_mesh = False
        self.scene_model = None
        self.material:Material = self.program.create_material()
        self.tri_count = 0
        # elemented
        self.element = False # is elemented
        self.elementBufID = 0
        self.elementInfo = None

    def bind_vao(self):
        if self.vaoID is None:
            self.vaoID = GL.glGenVertexArrays(1)
        GL.glBindVertexArray(self.vaoID)

    def unbind_vao(self):
        GL.glBindVertexArray(0)

    def set_shader (self, shader:MeshProgram):
        self.program = shader
        self.gl_program = self.program.program

    def find_shader (self, name:str):
        self.program = shaders.query_branched_program(name, self.material)
        self.gl_program = self.program.program

    def render(self, transform: Transform):
        self.bind_vao()
        GL.glUseProgram(self.gl_program)
        self.program.update_uniform('modelViewMatrix',
                                    [1, GL.GL_FALSE, transform.to_model_view_matrix_global().transpose()])
        self.program.use_material(self.material)
        if self.element:
            GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER, self.elementBufID)
            # mode,count,type,indices
            GL.glDrawElements(GL.GL_TRIANGLES,
                              self.elementInfo.count,
                              GL.GL_UNSIGNED_SHORT,
                              None
                              )
        else:
            GL.glDrawArrays(GL.GL_TRIANGLES,
                            0,
                            self.tri_count)

    def render_scene_mesh(self, scene, transform: Transform):
        GL.glUseProgram(self.gl_program)
        self.program.update_uniform('modelViewMatrix',
                                    [1, GL.GL_FALSE, transform.to_model_view_matrix_global().transpose()])
        #self.program.use_material(self.material)
        for i in range(self.scene_model.face_start, self.scene_model.face_start + self.scene_model.face_count):
            face = scene.faces[i]
            TEXTURE_TABLE[face.textureidx].bind()
            GL.glDrawElements(GL.GL_TRIANGLES,
                              face.meshvertcount,
                              GL.GL_UNSIGNED_INT,
                              GL.ctypes.c_void_p(face.meshvertstart * 4))