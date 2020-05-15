import ctypes
from typing import Dict, List, Callable

from OpenGL import GL
from OpenGL.arrays import ArrayDatatype
from PIL import Image as PIL_Image
from io import BytesIO

import pygltflib

from tremor.core.entity import Entity
from tremor.graphics import shaders
from tremor.graphics.mesh import Mesh
from tremor.graphics.surfaces import MaterialTexture, TextureUnit, Material
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
    def __init__(self, buffer_settings: BufferSettings, buffer_view: bytearray, count: int = 0):
        self.settings: BufferSettings = buffer_settings
        self.buffer: bytearray = buffer_view
        self.count = count


class UnboundBuffer:
    """
    I guess here's the ones we care about:
    * GL_ARRAY_BUFFER: the most common one. For anything that uses glVertexAttribPointer
    GL_TEXTURE_BUFFER: for textures?
    GL_ELEMENT_ARRAY_BUFFER: For anything that uses glDrawElements, etc.
    GL_UNIFORM_BUFFER: probably for complicated uniforms or something

    they are all explained https://www.khronos.org/opengl/wiki/GLAPI/glBindBuffer
    """
    BIND_WITH_TARGET=True # bind immediately if there is a target

    def __init__(self, buffer_view: pygltflib.BufferView, buffer_data, index:int):
        self.buffer_view = buffer_view
        self.buffer_view_index = index
        self.data = buffer_data
        self._target = self.buffer_view.target
        self._buffer_id = None
        self.bound = False
        if UnboundBuffer.BIND_WITH_TARGET and self.has_target():
            self.bind()

    def get_buffer_id(self):
        if self._buffer_id is None:
            raise Exception('Buffer ID is null. You need to bind the buffer first.')
        return self._buffer_id

    buffer_id = property(get_buffer_id)

    def get_target(self):
        if self._target is None:
            raise Exception("Target points nowhere.")
        return self._target

    def set_target(self, new_target):
        self._target = new_target

    target = property(get_target, set_target)

    def has_target(self):
        return self._target is not None

    def bind(self, target=None, force_rebind=False) -> None:
        if self.bound and not force_rebind:
            print('buffer is already bound.')
            return
        if target is not None and not self.has_target():
            self.set_target(target)
        if not self.has_target():
            raise Exception("Cannot bind buffer without target.")
        self._buffer_id = GL.glGenBuffers(1)
        GL.glBindBuffer(self.buffer_view.target, self._buffer_id)
        GL.glBufferData(target=self.buffer_view.target,
                        size=self.buffer_view.byteLength,
                        data=self.data,
                        usage=GL.GL_STATIC_DRAW
                        )
        GL.glBindBuffer(self.buffer_view.target, 0)
        self.bound = True

    # helpers
    def optional_binder (self) -> Callable:
        if not self.bound:
            return self.bind
        else:
            return lambda a:a # empty do-nothing function
    def bind_as_array_buffer(self):
        self.bind(GL.GL_ARRAY_BUFFER)

    def bind_as_element_buffer(self):
        self.bind(GL.GL_ELEMENT_ARRAY_BUFFER)

    def bind_as_texture_buffer(self):
        self.bind(GL.GL_TEXTURE_BUFFER)

    def bind_as_uniform_buffer(self):
        self.bind(GL.GL_UNIFORM_BUFFER)

class UnboundBufferCollection:
    def __init__(self):
        self._buffers:List[UnboundBuffer] = []

    def add_buffer (self, buffer:UnboundBuffer):
        self._buffers.append(buffer)

    def add_buffers (self, buffer_list:List[UnboundBuffer]):
        self._buffers += buffer_list

    def get_buffer (self, buffer_view_index:int) -> UnboundBuffer:
        self._sort()
        for b in self._buffers:
            if buffer_view_index == b.buffer_view_index:
                return b
        raise Exception("could not find buffer with index %d"%buffer_view_index)

    def __add__ (self, other):
        if type(other) == list:
            self.add_buffers(other)
        else:
            self.add_buffer(other)

    def __getitem__ (self, buffer_view_index:int):
        return self.get_buffer(buffer_view_index)

    def _sort (self):
        self._buffers.sort(key=lambda buff:buff.buffer_view_index)

def load_gltf(filepath) -> Mesh:
    obj = glb_object(filepath)
    # if not len(obj.meshes) == 1:
    #     raise Exception("only 1 mesh")
    # if not len(obj.meshes[0].primitives) == 1:
    #     raise Exception("only 1 primitive")
    mesh = Mesh() # todo: multiple meshes w/ primitives
    mesh.bind_vao()
    blob = np.frombuffer(obj.binary_blob(), dtype='uint8')
    obj.destroy_binary_blob()
    buffers = UnboundBufferCollection()
    for i in range(len(obj.bufferViews)):
        buffer_view = obj.bufferViews[i]
        data_slice = blob[buffer_view.byteOffset:buffer_view.byteOffset + buffer_view.byteLength]
        buffers.add_buffer(UnboundBuffer(buffer_view, data_slice, index=i))

    # for each primitive in each mesh . . .
    primitive = obj.meshes[0].primitives[0]
    index_acc = obj.accessors[primitive.indices] if primitive.indices is not None else None
    if index_acc is not None:
        mesh.element = True
        mesh.elementInfo = index_acc
        mesh.elementBufID = buffers[index_acc.bufferView].buffer_id
    attrs = 'COLOR_0,JOINTS_0,NORMAL,POSITION,TANGENT,TEXCOORD_0,TEXCOORD_1,WEIGHTS_0'.split(',')
    for att in attrs:
        val = getattr(primitive.attributes, att)
        if val is None: continue
        name = att.lower()
        acc = obj.accessors[val]
        location = GL.glGetAttribLocation(mesh.gl_program, name)
        buff = buffers[acc.bufferView]
        buff.optional_binder()(GL.GL_ARRAY_BUFFER) # if not bound already, bind with that target (that target is correct for all these attributes)
        GL.glEnableVertexAttribArray(location)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, buff.buffer_id)
        GL.glVertexAttribPointer(location,
                                 type_to_dim[acc.type],
                                 acc.componentType,
                                 acc.normalized,
                                 obj.bufferViews[acc.bufferView].byteStride,
                                 ctypes.c_void_p(acc.byteOffset),
                                 )
        if name == 'position': # this is ok because gltf specifies position, see attrs
            mesh.tri_count = acc.count // 3
    GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)

    # do materials # todo: create materials, then apply to meshes
    materialIdx = obj.meshes[0].primitives[0].material
    if materialIdx is not None:
        mat = obj.materials[materialIdx]
        mesh.material = Material.from_gltf_material(mat)
        if not mat.alphaMode == 'OPAQUE':
            raise Exception("Special case! Discard model, and find the nearest exit.")
        # thus, we can safely ignore alpha information
        # lots of annoying cases can be specified, if a model looks weird, it's because those are being discarded
        # todo add support for normal map, occlusion map, and emissive map?
        def get_texture (index, sampler) -> TextureUnit:
            tex = obj.textures[index]
            img = obj.images[tex.source]
            data = buffers[img.bufferView].data
            return load_gltf_image(img, data, sampler)
        # todo: these use more properties like 'scale' and 'texCoord' but we ignore those, so far
        color = mat.pbrMetallicRoughness.baseColorTexture
        normal = mat.normalTexture
        metallic = mat.pbrMetallicRoughness.metallicRoughnessTexture
        if color is not None:
            mesh.material.set_texture(get_texture(color.index, get_default_sampler()), MaterialTexture.COLOR)
        if normal is not None:
            mesh.material.set_texture(get_texture(normal.index, get_default_sampler()), MaterialTexture.NORMAL)
        if metallic is not None:
            mesh.material.set_texture(get_texture(metallic.index, get_default_sampler()), MaterialTexture.METALLIC)


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
