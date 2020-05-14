from typing import Dict, List

import OpenGL.GL as GL
import pygltflib

from tremor.graphics import shaders
from tremor.graphics.surfaces import Material
import numpy as np

from tremor.math.transform import Transform


class Mesh:
    def __init__(self):
        self.vaoID = GL.glGenVertexArrays(1)
        self.program = shaders.get_default_program()
        self.gl_program = self.program.program
        self.material = self.program.create_material()
        self.element = False
        self.elementBufID = 0

    def bind_vao(self):
        GL.glBindVertexArray(self.vaoID)

    def unbind_vao(self):
        GL.glBindVertexArray(0)

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