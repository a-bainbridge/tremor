import OpenGL.GL as GL
import numpy as np

from tremor.graphics import shaders
from tremor.graphics.shaders import MeshProgram
from tremor.graphics.surfaces import Material
from tremor.loader.texture_loading import TEXTURE_TABLE
from tremor.math.transform import Transform


class Mesh:
    def __init__(self):
        self.vaoID = GL.glGenVertexArrays(1)
        self.program: MeshProgram = shaders.get_default_program()
        self.gl_program = self.program.program
        self.is_scene_mesh = False
        self.scene_model = None
        self.material: Material = self.program.create_material()
        self.tri_count = 0
        # elemented
        self.element = False  # is elemented
        self.elementBufID = 0
        self.elementInfo = None

    def bind_vao(self):
        if self.vaoID is None:
            self.vaoID = GL.glGenVertexArrays(1)
        GL.glBindVertexArray(self.vaoID)

    def unbind_vao(self):
        GL.glBindVertexArray(0)

    def set_shader(self, shader: MeshProgram):
        self.program = shader
        self.gl_program = self.program.program

    def find_shader(self, name: str):
        self.program = shaders.query_branched_program(name, self.material)
        self.gl_program = self.program.program

    def render(self, transform: Transform):
        self.bind_vao()
        GL.glUseProgram(self.gl_program)
        self.program.update_uniform('modelViewMatrix',
                                    [1, GL.GL_FALSE, transform.to_model_view_matrix_global().transpose()])
        self.material.bind_textures(0)
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
        # self.program.use_material(self.material)
        bound_tex = -1
        # list of (texture_to_bind, start[], count[])
        drawcalls = {}
        for i in range(self.scene_model.face_start, self.scene_model.face_start + self.scene_model.face_count):
            face = scene.faces[i]
            tex = TEXTURE_TABLE[face.textureidx]
            if tex in drawcalls:
                drawcalls[tex][0].append((face.meshvertstart * 4))
                drawcalls[tex][1].append(face.meshvertcount)
                drawcalls[tex][2][0] = drawcalls[tex][2][0] + 1
            else:
                drawcalls[tex] = ([(face.meshvertstart * 4)], [face.meshvertcount], [1])
        for tex, call in drawcalls.items():
            tex.bind()
            GL.glMultiDrawElements(GL.GL_TRIANGLES,
                                   call[1],
                                   GL.GL_UNSIGNED_INT,
                                   np.array(call[0], dtype=np.intp),
                                   call[2][0])
