from io import BytesIO
from typing import Dict, List

import OpenGL.GL as gl
from PIL import Image as PIL_Image
import pygltflib
import numpy as np

class TextureType:
    def __init__ (self, target:gl.GLenum):
        self.target = target

    def size(self) -> int:
        pass
    def dimensions (self) -> tuple:
        pass

class Texture2D(TextureType):
    def __init__(self, width:int, height:int, img_format:gl.GLenum, sampler: pygltflib.Sampler, dtype):
        TextureType.__init__(self, gl.GL_TEXTURE_2D)
        self.width = width
        self.height = height
        self.img_format = img_format
        self.sampler = sampler
        self.dtype = dtype

    def size (self):
        return self.width * self.height * 4 # todo: rgba or not???

    def dimensions(self) -> tuple:
        return self.width, self.height

class TextureUnit:
    # setup:
    #  - create the texture
    #  - activate slot 0
    #  - bind texture to slot, depending on type
    # render:
    #  - assign the texture an arbitrary texture slot, but remember it
    #  - activate the texture slot
    #  - bind the texture type you want to it
    #  - assign the uniform location to be the bound texture in that slot

    # preferred 'constructor' method

    @staticmethod
    def generate_texture() -> 'TextureUnit':
        return TextureUnit(gl.glGenTextures(1))

    def __init__(self, handle):
        self.handle = handle
        self.active_location = 0
        self.texture_data:Dict[gl.GLenum, TextureType] = {}

    def active (self):
        gl.glActiveTexture(gl.GL_TEXTURE0 + self.active_location)

    def bind (self, target:gl.GLenum):
        gl.glBindTexture(target, self.handle)

    def setup_texture2D(self, data, width, height, img_format, sampler: pygltflib.Sampler, type=gl.GL_UNSIGNED_BYTE):
        self.active()
        self.bind(gl.GL_TEXTURE_2D)

        self.texture_data[gl.GL_TEXTURE_2D] = Texture2D(width, height, img_format, sampler, type)

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

    def get_data (self, target):
        if target == gl.GL_TEXTURE_2D:
            self.active()
            self.bind(target)
            metadata = self.texture_data[target]
            output = gl.glGetTexImage(target=target, level=0, format=gl.GL_RGBA, type=gl.GL_UNSIGNED_BYTE) # outputType set to bytes default
            #https://pillow.readthedocs.io/en/stable/handbook/concepts.html?highlight=modes#modes
            img:PIL_Image.Image = PIL_Image.frombytes('RGBA', metadata.dimensions(), output)
            # img.show()
            data = np.array(img)
            return data
        else:
            raise Exception(f"Don't know what to do with target '{target}' in TextureUnit.get_data")


class Material:
    """
    MAGIC: see _do_texture_flags
    """

    @staticmethod
    def from_gltf_material(gltf_mat: pygltflib.Material, color_texture: TextureUnit = None,
                           metallic_texture: TextureUnit = None, normal_texture: TextureUnit = None) -> 'Material':
        mat = Material(gltf_mat.name)
        if color_texture is not None:
            mat.set_texture(color_texture, MaterialTexture.COLOR, gl.GL_TEXTURE_2D)
        if metallic_texture is not None:
            mat.set_texture(metallic_texture, MaterialTexture.METALLIC, gl.GL_TEXTURE_2D)
        if normal_texture is not None:
            mat.set_texture(normal_texture, MaterialTexture.NORMAL, gl.GL_TEXTURE_2D)

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
            MaterialTexture.COLOR: MaterialTexture(MaterialTexture.COLOR, gl.GL_TEXTURE_2D),
            MaterialTexture.METALLIC: MaterialTexture(MaterialTexture.METALLIC, gl.GL_TEXTURE_2D),
            MaterialTexture.NORMAL: MaterialTexture(MaterialTexture.NORMAL, gl.GL_TEXTURE_2D)
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
    def set_texture(self, texture: TextureUnit, tex_type: str, target:gl.GLenum) -> None:
        self.set_mat_texture(MaterialTexture(tex_type, texture, target))
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
        textures = self.get_all_mat_textures()
        # if len(textures) + offset >= gl.glGetInteger(gl.GL_MAX_COMBINED_TEXTURE_IMAGE_UNITS):
        #     raise Exception('Number of textures exceeded maximum allowed by OpenGL')
        index = offset
        for t in textures:
            t.texture.active_location = index
            t.texture.active()
            t.texture.bind(t.target)
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

    def __init__(self, tex_type: str, target:gl.GLenum, texture: TextureUnit = None):
        self.exists: bool = texture is not None
        self.tex_type: str = tex_type
        self.target = target
        self._texture = texture

    def get_texture(self) -> TextureUnit:
        if not self.exists:
            raise Exception(f'No texture set for {self.tex_type}!')
        return self._texture

    def set_texture(self, tex: TextureUnit = None):
        self._texture = tex
        self.exists = not tex is None

    texture = property(get_texture, set_texture)
