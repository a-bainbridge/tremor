from typing import Dict, List
import numpy as np

import pygltflib
import OpenGL.GL as gl


class TextureUnit:

    # setup:
    #   - bind to gl context
    #   - set active texture
    #      -> setup the texture info
    #   - set correct uniform per shader (this changes nothing internally within this object)
    # render: don't do anything

    # preferred 'constructor' method

    global_index = 1 # todo: change this
    @staticmethod
    def generate_texture(index=0) -> 'TextureUnit':
        if index == 0:
            index = TextureUnit.global_index
            TextureUnit.global_index += 1
        return TextureUnit(index, gl.glGenTextures(1))

    def __init__(self, index: int, texture_unit):
        self.index = index
        self.unit = texture_unit

    def bad_bind (self, target=gl.GL_TEXTURE_2D):
        self.active()
        gl.glBindTexture(target, self.unit)

    def active(self):
        gl.glActiveTexture(gl.GL_TEXTURE0 + self.index)

    def bind_tex2d(self, data, width, height, img_format, sampler: pygltflib.Sampler, type=gl.GL_UNSIGNED_BYTE):
        self.active()
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.unit)

        gl.glTexImage2D(
            gl.GL_TEXTURE_2D,
            0,  # level
            img_format,  # internal format
            width,
            height,
            0,  # border (must be 0)
            img_format,  # format
            type,  # type
            data
        )

        gl.glGenerateMipmap(gl.GL_TEXTURE_2D)
        gl.glTexParameterf(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, sampler.magFilter)
        gl.glTexParameterf(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, sampler.minFilter)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, sampler.wrapS)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, sampler.wrapT)


class Material:
    @staticmethod
    def from_gltf_material(gltf_mat: pygltflib.Material, color_texture: TextureUnit = None,
                           metallic_texture: TextureUnit = None, normal_texture: TextureUnit = None) -> 'Material':
        mat = Material(gltf_mat.name)
        if color_texture is not None:
            mat.set_texture(color_texture, MaterialTexture.COLOR)
        if metallic_texture is not None:
            mat.set_texture(metallic_texture, MaterialTexture.METALLIC)
        if normal_texture is not None:
            mat.set_texture(normal_texture, MaterialTexture.NORMAL)

        pbr = gltf_mat.pbrMetallicRoughness
        mat.set_property('baseColor', pbr.baseColorFactor)
        mat.set_property('metallicFactor', pbr.metallicFactor)
        mat.set_property('roughnessFactor', pbr.roughnessFactor)
        mat.set_property('emissiveFactor', gltf_mat.emissiveFactor)
        return mat

    def __init__(self, name: str = 'unnamed', **kwargs):
        self.name = name

        # the textures
        self.textures: Dict[str, MaterialTexture] = {
            MaterialTexture.COLOR: MaterialTexture(MaterialTexture.COLOR),
            MaterialTexture.METALLIC: MaterialTexture(MaterialTexture.METALLIC),
            MaterialTexture.NORMAL: MaterialTexture(MaterialTexture.NORMAL)
        }
        self._properties:Dict[str, any] = {}

        for k, v in kwargs.items():
            self.set_property(k, v)

    def set_property (self, name, value):
        self._properties[name] = value
    def get_property (self, name):
        return self._properties[name]

    def set_mat_texture(self, mat_texture: 'MaterialTexture') -> None:
        self.textures[mat_texture.tex_type] = mat_texture

    # helper for set_mat_texture. they do the same thing
    def set_texture(self, texture: TextureUnit, tex_type: str) -> None:
        self.set_mat_texture(MaterialTexture(tex_type, texture))

    def get_mat_texture(self, mat_texture_type: str = None) -> 'MaterialTexture':
        if mat_texture_type is None:
            mat_texture_type = MaterialTexture.COLOR
        mat_tex = self.textures[mat_texture_type]
        return mat_tex  # todo note to self: check if exists!!!!!!!!!!

    def get_texture(self, mat_texture_type: str = None) -> TextureUnit:
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

    def get_all_textures(self) -> List[TextureUnit]:
        return [tex.texture for tex in self.get_all_mat_textures()]


class MaterialTexture:
    # enum for uniform names
    COLOR = 'texColor'
    METALLIC = 'texMetallic'
    NORMAL = 'texNormal'
    OCCLUSION = 'texOcclusion'
    EMISSIVE = 'texEmissive'

    def __init__(self, tex_type: str, texture: TextureUnit = None):
        self.exists: bool = texture is not None
        self.tex_type: str = tex_type
        self.texture = property(self.get_texture, self.set_texture)
        self.texture = texture

    def get_texture (self) -> TextureUnit:
        if not self.exists:
            raise Exception('No texture set!')
        return self.texture

    def set_texture (self, tex:TextureUnit=None):
        self.texture = tex
        self.exists = not tex is None