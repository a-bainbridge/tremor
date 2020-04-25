from typing import Dict, List

from OpenGL import GL
from PIL import Image as PIL_Image
from io import BytesIO

import pygltflib

from tremor.graphics import shaders
from tremor.loader import obj_loader
from tremor.core.game_object import RenderableObject, Material
import numpy as np

from tremor.graphics.uniforms import Texture

GLTF = pygltflib.GLTF2()


def glb_object(filepath) -> pygltflib.GLTF2:
    f = None
    try:
        f = open(filepath)
    except FileNotFoundError:
        raise Exception('The specified file ' + filepath + ' could not be found')
    return GLTF.load_binary(filepath)


def load_scene(filepath, program: shaders.MeshShader=None) -> List[RenderableObject]:
    if program is None:
        program = shaders.get_default_program()
    obj = glb_object(filepath)
    buffer = bytearray(obj._glb_data)
    buffer_views = []
    accessors = []
    textures:List[Texture] = []
    materials:List[Material] = []
    for bv in obj.bufferViews:
        start = bv.byteOffset
        end = start + bv.byteLength
        buffer_views.append(buffer[start:end])

    ai = -1
    for acc in obj.accessors:
        ai += 1
        vec = accessor_type_dim(acc.type)
        count = acc.count
        buffer_type = accessor_dtype(acc.componentType)
        buff = buffer_views[acc.bufferView][acc.byteOffset:]
        buffer_view = obj.bufferViews[acc.bufferView]
        byte_size = vec * np.array([1], dtype=buffer_type).itemsize
        if buffer_view.byteStride is None:
            stride = byte_size
        else:
            stride = buffer_view.byteStride

        better_buff = bytearray([])
        for i in range(count):
            offset = i * stride
            next_value = buff[offset:offset+byte_size]
            better_buff += next_value

        npbuff = np.frombuffer(better_buff, dtype=buffer_type)
        accessors.append(
            npbuff.reshape((count, vec)) # make it the right dimensions
        )

    for t in obj.textures:
        if t.sampler is None:
            sampler = get_default_sampler()
        else:
            sampler = obj.samplers[t.sampler]
        image = obj.images[t.source]
        data = buffer_views[image.bufferView]
        textures.append(
            load_gltf_image(image, data, sampler)
        )

    for m in obj.materials:
        try:
            color = textures[m.pbrMetallicRoughness.baseColorTexture.index]
        except: color=None
        try:
           metallic = textures[m.pbrMetallicRoughness.metallicRoughnessTexture.index]
        except: metallic=None
        try:
            normal = textures[m.normalTexture.index]
        except: normal=None
        materials.append(Material.from_gltf_material(m,
                                                     color_texture=color,
                                                     metallic_texture=metallic,
                                                     normal_texture=normal))


    renderables: List[RenderableObject] = []
    meshes = obj.meshes
    node_idx = 0
    node_stubs = {}
    for n in obj.nodes:
        if n.mesh is None:
            node_idx += 1
            continue
        m = meshes[n.mesh]
        # https://github.com/KhronosGroup/glTF/tree/master/specification/2.0#reference-indices
        # goto Meshes
        for prim in m.primitives:
            if prim.mode != 4: # 4 is for triangles
                node_idx += 1
                continue
            attr = prim.attributes
            positions = accessors[attr.POSITION]
            normals = accessors[attr.NORMAL]  # normals are per-vertex
            ro = RenderableObject(program)
            face_index = prim.indices
            if face_index is not None:
                l = len(accessors[face_index])
                raw_faces = accessors[face_index].reshape((int(l / 3), 3))
                positions = np.asarray(obj_loader.get_vertices_from_faces(positions, raw_faces), dtype='float32')
                normals = np.asarray(obj_loader.get_vertices_from_faces(normals, raw_faces), dtype='float32')

                colors = attr.COLOR_0
                if colors is not None:
                    ro.bind_float_attribute_vbo(
                        obj_loader.get_vertices_from_faces(accessors[colors], raw_faces).flatten(), 'color', True)
                texcoord = attr.TEXCOORD_0
                if texcoord is not None:
                    uvs = accessors[texcoord]
                    flat_uvs = obj_loader.get_vertices_from_faces(uvs, raw_faces).flatten()
                    ro.has_uvs = True
                    ro.bind_float_attribute_vbo(flat_uvs, 'texcoord', True, size=2)

                    if prim.material is not None:
                        ro.set_material(materials[prim.material])

            ro.bind_float_attribute_vbo(positions.flatten(), 'position', True)
            ro.bind_float_attribute_vbo(normals.flatten(), 'normal', True)

            ro.initial_translation = n.translation
            ro.scale = np.array([1, 1, 1], dtype='float32') * n.scale

            ro.using_quaternions = True
            ro.initial_quaternion = n.rotation

            ro.node_idx = node_idx
            # todo completely broken until RO is generalized
            if n.children is not None:
                for child_idx in n.children:
                    if node_idx == child_idx:
                        raise Exception("Node is its own child???")
                    if node_idx > child_idx:
                        for r in renderables:
                            if r.node_idx == child_idx:
                                ro.children.append(r)
                                break
                    else:
                        if child_idx in node_stubs.keys():
                            raise Exception("Node is a child of multiple nodes???")
                        node_stubs[child_idx] = node_idx  # make a note to fill in the child ref when we get there
            if node_idx in node_stubs.keys():  # resolve stub
                for r in renderables:
                    if r.node_idx == node_stubs[node_idx]:
                        r.children.append(ro)
                        break
                node_stubs.pop(node_idx)
            renderables.append(ro)
            node_idx += 1

    return renderables

def get_default_sampler () -> pygltflib.Sampler:
    # print('created default sampler')
    sampler = pygltflib.Sampler()
    sampler.wrapS = pygltflib.CLAMP_TO_EDGE  # U # REPEAT
    sampler.wrapT = pygltflib.CLAMP_TO_EDGE  # V
    sampler.minFilter = pygltflib.NEAREST # pygltflib.LINEAR
    sampler.magFilter = pygltflib.NEAREST
    return sampler

def load_gltf_image (gltf_image:pygltflib.Image, data, sampler:pygltflib.Sampler) -> Texture:
    img = PIL_Image.open(BytesIO(data))
    img = img.convert('RGBA')
    mode = accessor_color_type(img.mode)

    data = np.array(img.getdata(), dtype=np.uint8).flatten()
    min_filter = accessor_sampler_type(sampler.minFilter)
    mag_filter = accessor_sampler_type(sampler.magFilter)
    clamp_mode = accessor_sampler_type(sampler.wrapS)
    tex = Texture(data, gltf_image.name, width=img.width, height=img.height, img_format=mode, min_filter=min_filter, mag_filter=mag_filter, clamp_mode=clamp_mode)
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

def accessor_color_type (typ:str):
    try:
        return pil2gl_bands[typ.lower()]
    except:
        raise Exception('HEY what is color type %s'%typ)

def accessor_sampler_type (typ: int):
    try:
        return gltf_samp_types[typ]
    except:
        raise Exception('HEY what is sampler type %d'%typ)