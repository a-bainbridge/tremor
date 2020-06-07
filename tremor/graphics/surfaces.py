from typing import Dict, List

import OpenGL.GL as gl
import pygltflib


class TextureUnit:
    # setup:
    #  - create the texture
    #  - activate slot 0
    #  - bind texture to slot, depending on type

    # preferred 'constructor' method

    @staticmethod
    def generate_texture() -> 'TextureUnit':
        return TextureUnit(gl.glGenTextures(1))

    def __init__(self, handle):
        self.handle = handle
        self.active_location = 0

    def active (self):
        gl.glActiveTexture(gl.GL_TEXTURE0 + self.active_location)

    def bind (self, target:gl.GLenum):
        gl.glBindTexture(target, self.handle)

    def setup_texture2D(self, data, width, height, img_format, sampler: pygltflib.Sampler, type=gl.GL_UNSIGNED_BYTE):
        self.active()
        self.bind(gl.GL_TEXTURE_2D)

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
    """
    MAGIC: see _do_texture_flags
    """

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

    def __init__(self, name: str = 'unnamed', flags: List[str] = (), **kwargs):
        self.name = name

        # the textures
        self.textures: Dict[str, MaterialTexture] = {
            MaterialTexture.COLOR: MaterialTexture(MaterialTexture.COLOR),
            MaterialTexture.METALLIC: MaterialTexture(MaterialTexture.METALLIC),
            MaterialTexture.NORMAL: MaterialTexture(MaterialTexture.NORMAL)
        }
        self._texture_flags = []
        self._do_texture_flags()
        self._properties: Dict[str, any] = {}
        self._flags: List[str] = list(flags)

        for k, v in kwargs.items():
            self.set_property(k, v)

    def add_flag(self, flag_name):
        if not flag_name in self._flags:
            self._flags.append(flag_name)

    def remove_flag(self, flag_name):
        if flag_name in self._flags:
            self._flags.remove(flag_name)

    def get_flags(self) -> List[str]:
        return self._flags + self._texture_flags

    def set_property(self, name, value):
        self._properties[name] = value

    def get_property(self, name):
        if not name in self._properties.keys():
            raise Exception(f"Shader requested property '{name}' but material '{self.name}' does not have it.")
        return self._properties[name]

    def set_mat_texture(self, mat_texture: 'MaterialTexture') -> None:
        self.textures[mat_texture.tex_type] = mat_texture
        self._do_texture_flags()

    # helper for set_mat_texture. they do the same thing
    def set_texture(self, texture: TextureUnit, tex_type: str) -> None:
        self.set_mat_texture(MaterialTexture(tex_type, texture))
        self._do_texture_flags()

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

    def bind_textures(self, offset:int=0) -> int: # bind textures starting at the offset, and return the index of the NEXT unused texture slot
        textures = self.get_all_textures()
        # if len(textures) + offset >= gl.glGetInteger(gl.GL_MAX_COMBINED_TEXTURE_IMAGE_UNITS):
        #     raise Exception('Number of textures exceeded maximum allowed by OpenGL')
        index = offset
        for t in textures:
            t.active_location = index
            t.active()
            t.bind(gl.GL_TEXTURE_2D)
            index += 1
        return index

    def _do_texture_flags(self):
        self._texture_flags = []
        for tex in self.get_all_mat_textures():
            if tex.exists:
                self._texture_flags.append(f't_{tex.tex_type}')  # magic


class MaterialTexture:
    """
    MAGIC: MaterialTexture static enum things
    """
    # enum for uniform names
    COLOR = 'texColor'
    METALLIC = 'texMetallic'
    NORMAL = 'texNormal'
    OCCLUSION = 'texOcclusion'
    EMISSIVE = 'texEmissive'

    def __init__(self, tex_type: str, texture: TextureUnit = None):
        self.exists: bool = texture is not None
        self.tex_type: str = tex_type
        self._texture = texture

    def get_texture(self) -> TextureUnit:
        if not self.exists:
            raise Exception(f'No texture set for {self.tex_type}!')
        return self._texture

    def set_texture(self, tex: TextureUnit = None):
        self._texture = tex
        self.exists = not tex is None

    texture = property(get_texture, set_texture)
