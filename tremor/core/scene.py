from typing import List

from tremor.core.entity import Entity
from tremor.math import collision_testing
from tremor.math.vertex_math import magnitude_vec3


class Scene:
    def __init__(self, name: str):
        self.name = name
        self.active_camera: Entity = None
        self.entities: List[Entity] = None
        self.faces: List = None
        self.vao = None
        self.faceVBO = None
        self.faceIBO = None

    def setup_scene_geometry(self, vertex_data, index_data, faces):
        from tremor.graphics.vbo import VertexBufferObject
        from OpenGL.GL import glGenVertexArrays, glBindVertexArray, glBindBuffer, GL_FALSE, GL_FLOAT, glGenBuffers, \
            GL_STATIC_DRAW, \
            GL_ELEMENT_ARRAY_BUFFER, glBufferData, glVertexAttribPointer, ctypes, glEnableVertexAttribArray
        self.faces = faces
        self.vao = glGenVertexArrays(1)
        glBindVertexArray(self.vao)
        self.faceVBO = VertexBufferObject()
        self.faceVBO.update_data(vertex_data, True)  # vertex information: vec3f pos, vec3f norm, vec2f tex
        self.faceVBO.bind()
        self.faceIBO = glGenBuffers(1)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.faceIBO)
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, index_data, GL_STATIC_DRAW)
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, (3 + 3 + 2) * 4, ctypes.c_void_p(0))
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, (3 + 3 + 2) * 4, ctypes.c_void_p(3 * 4))
        glEnableVertexAttribArray(1)
        glVertexAttribPointer(3, 2, GL_FLOAT, GL_FALSE, (3 + 3 + 2) * 4, ctypes.c_void_p(6 * 4))
        glEnableVertexAttribArray(3)
        glBindVertexArray(0)

    def bind_scene_vao(self):
        from OpenGL.GL import glBindVertexArray
        glBindVertexArray(self.vao)

    def unbind_scene_vao(self):
        from OpenGL.GL import glBindVertexArray
        glBindVertexArray(0)

    def tick(self, dt):
        for ent in self.entities:
            if ent.gravity:
                ent.velocity[1] -= 30.0 * dt
            bb = ent.boundingbox
            if magnitude_vec3(ent.velocity) >= 0.000001:
                next_frame_pos = ent.transform.get_translation() + ent.velocity * dt
                trace_res = collision_testing.trace(ent.transform.get_translation(), next_frame_pos, bb)
                if trace_res.collided:
                    ent.velocity = collision_testing.clamp_velocity(ent.velocity, trace_res)
                ent.transform.set_translation(trace_res.end_point)
        pass
