from typing import Dict
import numpy as np

import pygltflib
import OpenGL.GL as gl


class TextureUnit:

    # preferred 'constructor' method
    @staticmethod
    def generate_texture(index) -> 'TextureUnit':
        return TextureUnit(index, gl.glGenTextures(1))

    def __init__(self, index: int, texture_unit):
        self.index = index
        self.unit = texture_unit

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


class Material: # todo: inputs
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