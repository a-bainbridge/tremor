from typing import List, Dict

import pygltflib

import numpy as np
import OpenGL.GL as GL
from PIL import Image

from tremor.graphics import shaders
from tremor.math import vertex_math, matrix
from tremor.math.transform import Transform


class BufferSettings:  # data class
    def __init__(self, size: int = 3, data_type=GL.GL_FLOAT, stride: int = 0):
        self.size = size
        self.data_type = data_type
        self.stride = stride


class Attribute:
    def __init__(self, location=0, name="none", vbo_id=0, settings: BufferSettings = BufferSettings()):
        self.name = name
        self.location = location
        self.vbo_id = vbo_id
        self.settings = settings

    def bind(self) -> None:
        GL.glEnableVertexAttribArray(self.location)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.vbo_id)
        GL.glVertexAttribPointer(self.location, self.settings.size, self.settings.data_type, GL.GL_FALSE,
                                 self.settings.stride, None)

    def unbind(self):
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)

    def get_size(self) -> int:
        return self.settings.size


class Attributes:
    def __init__(self):
        self.attributes: List[Attribute] = []

    def name_in_attributes(self, name: str) -> bool:
        for a in self.attributes:
            if a.name == name:
                return True
        return False

    def location_in_attributes(self, location) -> bool:
        for a in self.attributes:
            if a.location == location:
                return True
        return False

    def vbo_id_in_attributes(self, vbo_id: int):
        for a in self.attributes:
            if a.vbo_id == vbo_id:
                return True
        return False

    def add_attribute(self, name: str, location, vbo_id: int, settings: BufferSettings):
        if not self.name_in_attributes(name) and not self.location_in_attributes(
                location) and not self.vbo_id_in_attributes(vbo_id):
            self.attributes.append(Attribute(name=name, location=location, vbo_id=vbo_id, settings=settings))

    def bind_all(self) -> None:
        for a in self.attributes:
            a.bind()

    def unbind_all(self) -> None:
        for a in self.attributes:
            a.unbind()


class ElementRenderer:
    def __init__(self):
        self.meshes: List[Mesh] = []

    def render(self):
        for mesh in self.meshes:
            mesh.render()


class Mesh:

    def __init__(self, parent_element, program: shaders.MeshShader = None):
        self.vaoID = GL.glGenVertexArrays(1)
        self.attributes = Attributes()
        self.vertex_count = 0
        self.face_count = 0

        # display
        self.material = Material()
        self.program: shaders.MeshShader = shaders.get_default_program() if program is None else program
        self.gl_program = self.program.program

        self.has_uvs = False
        self.parent = parent_element
        self.elemented: bool = False
        self.faces: int = 0

    def set_material(self, material: 'Material') -> None:
        self.material = material

    def set_image(self, image: Image):
        data = np.asarray(image, dtype='float32').flatten()
        mode = image.mode.lower()
        form = GL.GL_RGBA if mode == 'rgba' else (
            GL.GL_RGB if mode == 'rgb' else print('unknown format %s' % mode))  # default is RGB
        tex = Texture(data, name='unnamed', width=image.width, height=image.height, img_format=form)
        self.set_texture(tex)

    def set_texture(self, tex: 'Texture'):
        self.material.set_texture(tex, MaterialTexture.COLOR)

    def bind_elements_vbo(self, data, length):
        vbo_id = GL.glGenBuffers(1)
        GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER, vbo_id)
        GL.glBufferData(GL.GL_ELEMENT_ARRAY_BUFFER, data, GL.GL_STATIC_DRAW)
        self.elemented = True
        self.faces = int(length / 3)

    def bind_float_attribute_vbo(self, data, attribute_name: str, static: bool,
                                 buffer_settings: BufferSettings = BufferSettings()):  # must be 4 byte floats
        self.bind_vao()
        if attribute_name == 'position':  # aaaaaaaaaaaaaaaaaaaaaa
            self.vertex_count = int(len(data) / 3)
        vbo_id = GL.glGenBuffers(1)
        location = GL.glGetAttribLocation(self.gl_program, attribute_name)
        # print('location is %s for %s'%(location, attribute_name))
        self.attributes.add_attribute(name=attribute_name, location=location, vbo_id=vbo_id, settings=buffer_settings)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, vbo_id)  # bind it
        GL.glBufferData(GL.GL_ARRAY_BUFFER, data,
                        GL.GL_STATIC_DRAW if static else GL.GL_DYNAMIC_DRAW)  # add the data into it
        GL.glVertexAttribPointer(location, buffer_settings.size, GL.GL_FLOAT, GL.GL_FALSE, buffer_settings.stride,
                                 None)  # tell it how to parse it
        # self.attributes.attributes[-1].bind()
        # self.attributes.attributes[-1].unbind()
        self.unbind_vao()

    def render(self):
        # https://github.com/TheThinMatrix/OpenGL-Tutorial-3/blob/master/src/renderEngine/Renderer.java #render
        GL.glUseProgram(self.gl_program)
        self.program.update_uniform('modelViewMatrix',
                                    [1, GL.GL_FALSE, self.parent.transform.to_model_view_matrix_global().transpose()])
        self.program.update_uniform('isTextured', [self.material.get_mat_texture().exists])
        self.bind_vao()
        for mat_tex in self.material.get_all_mat_textures():
            mat_tex.texture.bind()
            GL.glUniform1i(
                GL.glGetUniformLocation(self.gl_program, mat_tex.tex_type),
                self.material.get_texture(MaterialTexture.COLOR).index
            )
        self.attributes.bind_all()
        if not self.elemented:
            GL.glDrawArrays(GL.GL_TRIANGLES, 0, self.vertex_count)
        else:
            GL.glDrawElements(GL.GL_TRIANGLES, self.faces, GL.GL_UNSIGNED_BYTE, None)
        self.attributes.unbind_all()
        for a in self.attributes.attributes:
            GL.glDisableVertexAttribArray(a.location)
        self.unbind_vao()

    def bind_vao(self):
        GL.glBindVertexArray(self.vaoID)

    def unbind_vao(self):
        GL.glBindVertexArray(0)


# a texture is technically a uniform, of type "sampler2D"
# https://stackoverflow.com/questions/8866904/differences-and-relationship-between-glactivetexture-and-glbindtexture
class Texture:
    index = 0

    def __init__(self, data: np.ndarray, name: str, width: int = 1, height: int = 1, min_filter=GL.GL_LINEAR,
                 mag_filter=GL.GL_LINEAR,
                 clamp_mode=GL.GL_CLAMP_TO_EDGE, img_format=GL.GL_RGB):
        self.data = data
        self.width = width if width > 0 else len(self.data[0])
        self.height = height if height > 0 else len(self.data)
        self.name = name
        self.index = Texture.index
        self.min_filter = min_filter
        self.mag_filter = mag_filter
        self.clamp_mode = clamp_mode
        self.format = img_format
        self.texture = None
        self.init()
        Texture.index += 1  # increment for other textures

    def set_texture(self):
        # https://www.khronos.org/registry/OpenGL-Refpages/gl4/html/glTexImage2D.xhtml
        GL.glTexImage2D(
            GL.GL_TEXTURE_2D,  # target
            0,  # level
            GL.gl_compressed_format[self.format],  # internalformat
            self.width,  # width
            self.height,  # height
            0,  # border
            self.format,  # format
            GL.GL_UNSIGNED_BYTE,  # type
            self.data,  # pixels
        )

        GL.glGenerateMipmap(GL.GL_TEXTURE_2D)

        GL.glTexParameterf(GL.GL_TEXTURE_2D, GL.GL.GL_TEXTURE_MAG_FILTER, self.mag_filter)
        GL.glTexParameterf(GL.GL_TEXTURE_2D, GL.GL.GL_TEXTURE_MIN_FILTER, self.min_filter)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL.GL_TEXTURE_WRAP_S, self.clamp_mode)  # u
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL.GL_TEXTURE_WRAP_T, self.clamp_mode)  # v

    def bind(self):
        GL.glActiveTexture(GL.GL_TEXTURE0 + self.index)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.texture)

    def init(self):
        self.texture = GL.glGenTextures(1)
        self.bind()
        # GL.glPixelStorei( GL.GL_UNPACK_ALIGNMENT, 1)
        self.set_texture()


class Material:
    # LightingModels:Dict[str, Dict[str, type]] = { # currently unused, but might be helpful for shaders or something
    #     'PHONG': { # maybe do something like this with MeshPrograms instead
    #         'diffuse': float,
    #         'specular': float,
    #         'ambient': float,
    #         'shinyness': float
    #     }
    # }
    @staticmethod
    def from_gltf_material(gltf_mat: pygltflib.Material, color_texture: Texture = None,
                           metallic_texture: Texture = None, normal_texture: Texture = None) -> 'Material':
        mat = Material(gltf_mat.name)
        if color_texture is not None:
            mat.set_texture(color_texture, MaterialTexture.COLOR)
        if metallic_texture is not None:
            mat.set_texture(metallic_texture, MaterialTexture.METALLIC)
        if normal_texture is not None:
            mat.set_texture(normal_texture, MaterialTexture.NORMAL)

        pbr = gltf_mat.pbrMetallicRoughness
        mat.base_color = pbr.baseColorFactor
        mat.metallic_factor = pbr.metallicFactor
        mat.roughness_factor = pbr.roughnessFactor
        mat.emissive_factor = gltf_mat.emissiveFactor
        return mat

    def __init__(self, name: str = 'unnamed', **kwargs):
        self.name = name

        # the textures
        self.textures: Dict[str, MaterialTexture] = {
            MaterialTexture.COLOR: MaterialTexture(MaterialTexture.COLOR),
            MaterialTexture.METALLIC: MaterialTexture(MaterialTexture.METALLIC),
            MaterialTexture.NORMAL: MaterialTexture(MaterialTexture.NORMAL)
        }

        self.base_color: np.array = np.array([1, 1, 1])
        self.metallic_factor: float = 1.0  # [0, 1]
        self.roughness_factor: float = 1.0  # [0, 1]
        self.emissive_factor: np.array = np.array([0.0, 0.0, 0.0])
        for k, v in kwargs.items():
            if not hasattr(self, k):
                print('not sure what %s is, but setting it to material %s anyway' % (k, name))
            setattr(self, k, v)

    def set_mat_texture(self, mat_texture: 'MaterialTexture') -> None:
        self.textures[mat_texture.tex_type] = mat_texture

    def set_texture(self, texture: Texture,
                    tex_type: str) -> None:  # helper for set_mat_texture. they do the same thing
        self.set_mat_texture(MaterialTexture(tex_type, texture))

    def get_mat_texture(self, mat_texture_type: str = None) -> 'MaterialTexture':
        if mat_texture_type is None:
            mat_texture_type = MaterialTexture.COLOR
        mat_tex = self.textures[mat_texture_type]
        return mat_tex  # todo note to self: check if exists!!!!!!!!!!

    def get_texture(self, mat_texture_type: str = None) -> Texture:
        if mat_texture_type is None:
            mat_texture_type = MaterialTexture.COLOR
        mat_texture = self.get_mat_texture(mat_texture_type)
        if mat_texture.exists:
            return mat_texture.texture
        else:
            return None

    def has_texture(self, mat_texture_type: str) -> bool:
        return self.textures[mat_texture_type].exists

    def get_all_mat_textures(self) -> List['MaterialTexture']:
        return [tex for tex in self.textures.values() if tex.exists]

    def get_all_textures(self) -> List[Texture]:
        return [tex.texture for tex in self.get_all_mat_textures()]


class MaterialTexture:
    COLOR = 'texColor'  # these correspond to uniform names
    METALLIC = 'texMetallic'
    NORMAL = 'texNormal'

    def __init__(self, tex_type: str, texture: Texture = None):
        self.exists: bool = texture is not None
        self.tex_type: str = tex_type
        self.texture: Texture = texture
