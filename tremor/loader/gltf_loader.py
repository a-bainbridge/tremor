import ctypes
from typing import Dict, List

from OpenGL import GL
from OpenGL.arrays import ArrayDatatype
from PIL import Image as PIL_Image
from io import BytesIO

import pygltflib

from tremor.core.entity import Entity
from tremor.graphics import shaders
from tremor.graphics.mesh import Mesh
from tremor.graphics.surfaces import MaterialTexture, TextureUnit
from tremor.loader import obj_loader
from tremor.graphics.element_renderer import ElementRenderer, BufferSettings
import numpy as np


GLTF = pygltflib.GLTF2()


def glb_object(filepath) -> pygltflib.GLTF2:
    f = None
    try:
        f = open(filepath)
    except FileNotFoundError:
        raise Exception('The specified file ' + filepath + ' could not be found')
    return GLTF.load_binary(filepath)


class DecoratedAccessor:
    def __init__(self, buffer_settings: BufferSettings, buffer_view: bytearray, count:int=0):
        self.settings:BufferSettings = buffer_settings
        self.buffer:bytearray = buffer_view
        self.count = count

def load_gltf(filepath) -> Mesh:
    obj = glb_object(filepath)
    if not len(obj.meshes) == 1:
        raise Exception("only 1 mesh")
    if not len(obj.meshes[0].primitives) == 1:
        raise Exception("only 1 primitive")
    mesh = Mesh()
    mesh.bind_vao()
    bv_tbl = {}
    blob = np.frombuffer(obj.binary_blob(), dtype='uint8')
    obj.destroy_binary_blob()
    image_buffer_data = {}
    for i in range(len(obj.bufferViews)):
        buffer_view = obj.bufferViews[i]
        # images oft have no target. we'll deal with those later
        data_slice = blob[buffer_view.byteOffset:buffer_view.byteOffset + buffer_view.byteLength]
        if buffer_view.target is not None:
            bufID = GL.glGenBuffers(1)
            bv_tbl[i] = bufID
            GL.glBindBuffer(buffer_view.target, bufID)
            GL.glBufferData(target=buffer_view.target,
                            size=buffer_view.byteLength,
                            data=data_slice,
                            usage=GL.GL_STATIC_DRAW
                            )
            GL.glBindBuffer(buffer_view.target, 0)
        else:
            image_buffer_data[i] = data_slice
    primitive = obj.meshes[0].primitives[0]
    pos_acc = obj.accessors[primitive.attributes.POSITION]
    norm_acc = obj.accessors[primitive.attributes.NORMAL]
    tex_acc = obj.accessors[primitive.attributes.TEXCOORD_0] #todo make optional
    index_acc = obj.accessors[primitive.indices] if primitive.indices is not None else None
    if index_acc is not None:
        mesh.element = True
        mesh.elementInfo = index_acc
        mesh.elementBufID = bv_tbl[index_acc.bufferView]
    # positions

    pos_loc = GL.glGetAttribLocation(mesh.gl_program, "position")
    GL.glEnableVertexAttribArray(pos_loc)
    GL.glBindBuffer(GL.GL_ARRAY_BUFFER, bv_tbl[pos_acc.bufferView])
    GL.glVertexAttribPointer(pos_loc,
                             type_to_dim[pos_acc.type],
                             pos_acc.componentType,
                             pos_acc.normalized,
                             obj.bufferViews[pos_acc.bufferView].byteStride,
                             ctypes.c_void_p(pos_acc.byteOffset),
                             )

    mesh.tri_count = pos_acc.count // 3  # assume vec3
    # normals
    GL.glBindBuffer(GL.GL_ARRAY_BUFFER, bv_tbl[norm_acc.bufferView])
    norm_loc = GL.glGetAttribLocation(mesh.gl_program, "normal")
    GL.glVertexAttribPointer(index=norm_loc,
                             size=type_to_dim[norm_acc.type],
                             normalized=norm_acc.normalized,
                             stride=obj.bufferViews[norm_acc.bufferView].byteStride,
                             pointer=ctypes.c_void_p(norm_acc.byteOffset),
                             type=norm_acc.componentType)
    GL.glEnableVertexAttribArray(norm_loc)
    # tex coords

    GL.glBindBuffer(GL.GL_ARRAY_BUFFER, bv_tbl[tex_acc.bufferView])
    tex_loc = GL.glGetAttribLocation(mesh.gl_program, "texcoord")
    GL.glEnableVertexAttribArray(tex_loc)
    GL.glVertexAttribPointer(index=tex_loc,
                             size=type_to_dim[tex_acc.type],
                             normalized=tex_acc.normalized,
                             stride=obj.bufferViews[tex_acc.bufferView].byteStride,
                             pointer=ctypes.c_void_p(tex_acc.byteOffset),
                             type=tex_acc.componentType)
    GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)

    # actually handle textures :)
    materialIdx = obj.meshes[0].primitives[0].material
    mat = obj.materials[materialIdx]
    if not mat.alphaMode == 'OPAQUE':
        raise Exception("Special case! Discard model, and find the nearest exit.")
    # thus, we can safely ignore alpha information
    # lots of annoying cases can be specified, if a model looks weird, it's because those are being discarded
    # todo add support for normal map, occlusion map, and emissive map?
    color_tex = obj.textures[mat.pbrMetallicRoughness.baseColorTexture.index]
    color_img = obj.images[color_tex.source]
    color_img_data = image_buffer_data[color_img.bufferView]

    mesh.material.set_texture(load_gltf_image(color_img, color_img_data, get_default_sampler()), MaterialTexture.COLOR)
    mesh.unbind_vao()
    return mesh


def get_default_sampler() -> pygltflib.Sampler:
    # print('created default sampler')
    sampler = pygltflib.Sampler()
    sampler.wrapS = pygltflib.CLAMP_TO_EDGE  # U # REPEAT
    sampler.wrapT = pygltflib.CLAMP_TO_EDGE  # V
    sampler.minFilter = pygltflib.NEAREST  # pygltflib.LINEAR
    sampler.magFilter = pygltflib.NEAREST
    return sampler


def load_gltf_image(gltf_image: pygltflib.Image, data, sampler: pygltflib.Sampler) -> TextureUnit:
    img = PIL_Image.open(BytesIO(data))
    img = img.convert('RGBA')
    mode = accessor_color_type(img.mode)

    data = np.array(img.getdata(), dtype=np.uint8).flatten()
    # min_filter = accessor_sampler_type(sampler.minFilter)
    # mag_filter = accessor_sampler_type(sampler.magFilter)
    # clamp_mode = accessor_sampler_type(sampler.wrapS)
    tex = TextureUnit.generate_texture()
    tex.bind_tex2d(data, width=img.width, height=img.height, img_format=mode, sampler=sampler)
    # tex = Texture(data, gltf_image.name, width=img.width, height=img.height, img_format=mode, min_filter=min_filter,
    #               mag_filter=mag_filter, clamp_mode=clamp_mode)
    return tex


pil2gl_bands = {
    'rgba': GL.GL_RGBA,
    'rgb': GL.GL_RGB,
    # 'p': GL.GL_RGB
}

# https://github.com/KhronosGroup/glTF/tree/master/specification/2.0#floating-point-data
type_to_dim: Dict[str, int] = {
    'MAT4': 16,
    'VEC4': 4,
    'VEC3': 3,
    'VEC2': 2,
    'SCALAR': 1
}
gltf_dtype: Dict[int, type] = {
    5120: np.int8,  # byte (1)
    5121: np.uint8,  # unsigned byte (1)
    5122: np.int16,  # short (2)
    5123: np.uint16,  # ushort (2)
    5125: np.uint32,  # uint (4)
    5126: np.float32,  # float (4)
}

gltf_samp_types: Dict[int, type] = {
    # mag / min filters
    9728: GL.GL_NEAREST,
    9729: GL.GL_LINEAR,

    9984: GL.GL_NEAREST_MIPMAP_NEAREST,
    9985: GL.GL_LINEAR_MIPMAP_NEAREST,
    9986: GL.GL_NEAREST_MIPMAP_LINEAR,
    9987: GL.GL_LINEAR_MIPMAP_LINEAR,
    # wrap types
    33071: GL.GL_CLAMP_TO_EDGE,
    33648: GL.GL_MIRRORED_REPEAT,
    10497: GL.GL_REPEAT
}


def accessor_type_dim(typ: str) -> int:
    try:
        return type_to_dim[typ]
    except:
        raise Exception('HEY what is %s' % typ)


def accessor_dtype(typ: int) -> type:
    try:
        return gltf_dtype[typ]
    except:
        raise Exception('HEY what is %d' % typ)


def accessor_color_type(typ: str):
    try:
        return pil2gl_bands[typ.lower()]
    except:
        raise Exception('HEY what is color type %s' % typ)


def accessor_sampler_type(typ: int):
    try:
        return gltf_samp_types[typ]
    except:
        raise Exception('HEY what is sampler type %d' % typ)
