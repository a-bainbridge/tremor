import argparse
import io
import sys
import time

from tremor.core.scene_geometry import Brush, Plane
from tremor.loader.scene.scene_types import *


def parse_side(string):
    temp = string.split(" ")
    point = []
    points = []
    plane_points = []

    for token in temp:
        if len(points) == 3:
            break
        if token == "(":
            continue
        if token == ")":
            points.append(point)
            point = []
            continue
        point.append(float(token))
    for point in points:
        plane_points.append(np.array([point[1], point[2], point[0]], dtype='float32'))
    plane = Plane.plane_from_points_quake_style(plane_points)
    plane.texture_name = temp[15]
    # 0 0 0 0.1 0.1
    plane.texture_attributes = (float(temp[19]), float(temp[20]), float(temp[16]), float(temp[17]), float(temp[18]))
    plane.content = int(temp[21])
    plane.surface = int(temp[22])
    # todo load scale and offset and rotation, lol
    # todo and flags!
    return plane


def parse_keyvalue(string):
    pair = string.split("\" \"", 1)
    pair[0] = pair[0].replace("\"", "", 1)
    pair[1] = "".join(pair[1].rsplit("\"", 1))
    return pair


def parse_map_file(filename):
    file = open(filename, 'rt', encoding="utf-8")
    in_ent = False
    in_brush = False
    entities = []
    brush_temp = []
    current_ent = {}
    for line in file:
        line = line.strip()
        if line.startswith("//"):
            continue
        if line == "{":
            if not in_ent:
                in_ent = True
            elif in_ent and not in_brush:
                in_brush = True
            elif in_ent and in_brush:
                raise Exception("bad")
            continue
        if line == "}":
            if in_brush:
                in_brush = False
                if "brushes" not in current_ent:
                    current_ent["brushes"] = []
                current_ent["brushes"].append(Brush(brush_temp))
                brush_temp = []
            elif in_ent:
                in_ent = False
                entities.append(current_ent)
                current_ent = {}
            elif not in_ent and not in_brush:
                raise Exception("bad")
            continue
        if in_ent and not in_brush:
            line = parse_keyvalue(line)
            current_ent[line[0]] = line[1]
            continue
        if in_ent and in_brush:
            brush_temp.append(parse_side(line))
    return entities


def format_ents(ents: List[dict]) -> str:
    buf = io.StringIO()
    for ent in ents:
        buf.write("{\n")
        for k, v in ent.items():
            buf.write("\"" + str(k) + "\"" + " " + "\"" + str(v) + "\"\n")
        buf.write("}\n")
    return buf.getvalue()


def load_texture_cache(datadir):
    if str.endswith(datadir, "/") or str.endswith(datadir, "\\"):
        cacheloc = datadir + "textures/texturecache.txt"
    else:
        cacheloc = datadir + "/textures/texturecache.txt"
    cache_file = open(cacheloc, "rt", encoding='utf-8')
    text_cache = {}
    for line in cache_file:
        line = line.strip()
        if line == "":
            continue
        line = line.split(" ")
        text_cache[line[0]] = (int(line[1]), int(line[2]))
    return text_cache


# xq yq zq -> yt zt xt
# vec3_t	baseaxis[18] =
# {
# {0,0,1}, {1,0,0}, {0,-1,0},			// floor
# {0,0,-1}, {1,0,0}, {0,-1,0},		// ceiling
# {1,0,0}, {0,1,0}, {0,0,-1},			// west wall
# {-1,0,0}, {0,1,0}, {0,0,-1},		// east wall
# {0,1,0}, {1,0,0}, {0,0,-1},			// south wall
# {0,-1,0}, {1,0,0}, {0,0,-1}			// north wall
# };
uv_proj_planes = np.array([
    [0, 1, 0],  # floor
    [0, -1, 0],  # ceiling
    [0, 0, 1],  # west wall
    [0, 0, -1],  # east wall
    [1, 0, 0],  # south wall
    [-1, 0, 0],  # north wall
    [0, 0, 1],  # floor_u
    [-1, 0, 0],  # floor_v
    [0, 0, 1],  # ceiling_u
    [-1, 0, 0],  # ceiling_v
    [1, 0, 0],  # west_u
    [0, -1, 0],  # west_v
    [1, 0, 0],  # east_u
    [0, -1, 0],  # east_v
    [0, 0, 1],  # south_u
    [0, -1, 0],  # south_v
    [0, 0, 1],  # north_u
    [0, -1, 0],  # north_v
], dtype='float32')
warned_angle = False


# texture_attributes = (scale_x, scale_y, offset_x, offset_y, angle)
def calculate_uv(texture_size, normal, point, texture_attributes):
    global warned_angle
    if (texture_attributes[4] != 0.0) and not warned_angle:
        print("Warning: texture angles are currently unstable and may not produce good results!")
        warned_angle = True
    best_dot = 0
    best = 0
    for i in range(0, 6):
        dot = uv_proj_planes[i].dot(normal)
        if dot > best_dot:
            best_dot = dot
            best = i
    u_axis = uv_proj_planes[6 + 2 * best]
    v_axis = uv_proj_planes[7 + 2 * best]
    angle = np.pi * texture_attributes[4] / 180.0
    sin = np.sin(angle)
    cos = np.cos(angle)
    if not u_axis[0] == 0:
        sv = 0
    elif not u_axis[1] == 0:
        sv = 1
    else:
        sv = 2
    if not v_axis[0] == 0:
        tv = 0
    elif not v_axis[1] == 0:
        tv = 1
    else:
        tv = 2
    a = cos * u_axis[sv] - sin * u_axis[tv]
    b = sin * u_axis[sv] + cos * u_axis[tv]
    u_axis[sv] = a
    u_axis[tv] = b
    a = cos * v_axis[sv] - sin * v_axis[tv]
    b = sin * v_axis[sv] + cos * v_axis[tv]
    v_axis[sv] = a
    v_axis[tv] = b
    u_axis = u_axis * (1 / texture_attributes[0])
    v_axis = v_axis * (1 / texture_attributes[1])
    u = texture_attributes[2] + u_axis.dot(point)
    v = texture_attributes[3] + v_axis.dot(point)
    u /= texture_size[0]
    v /= texture_size[1]
    return u, v


def main(args):
    print("loading texture cache")
    text_cache = load_texture_cache(args.datadir)
    if args.verbose:
        print(text_cache)
    print("compiling map " + args.map)
    output_file = open(args.output, "w+b")
    output_file.write(HEADER)
    parse_time = time.time()
    ents = parse_map_file(args.map)
    parse_time = time.time() - parse_time
    raw_verts = []
    raw_faces = []
    raw_mesh_verts = []
    raw_models = []
    raw_textures = []
    raw_planes = []
    raw_brushes = []
    raw_brush_sides = []
    generate_time = time.time()
    int_time = 0
    for ent in ents:
        if "brushes" in ent:
            face_start = len(raw_faces)
            face_count = 0
            for brush in ent["brushes"]:
                plane_start = len(raw_planes)
                plane_count = 0
                brush_side_start = len(raw_brush_sides)
                brush_side_count = len(brush.planes)
                content_flag = 0
                for plane in brush.planes:
                    raw_planes.append(RawPlane(plane.point, plane.normal))
                    content_flag |= plane.content
                    raw_brush_sides.append(RawBrushSide(plane_start + plane_count, plane.surface))
                    plane_count += 1
                raw_brushes.append(RawBrush(content_flag, brush_side_start, brush_side_count))
                temp = time.time()
                vertices = brush.get_vertices()
                int_time += time.time() - temp
                for j in range(len(vertices)):
                    if brush.planes[j].texture_name == "__TB_empty":
                        continue
                    face = vertices[j]
                    raw_vert_start = len(raw_verts)
                    raw_mesh_start = len(raw_mesh_verts)
                    raw_mesh_count = 0
                    for i in range(0, len(face)):
                        u, v = calculate_uv(text_cache[brush.planes[j].texture_name], brush.planes[j].normal, face[i],
                                            brush.planes[j].texture_attributes)
                        raw_verts.append(
                            RawVertex(face[i], brush.planes[j].normal, np.array([u, v], dtype='float32')))
                    for i in range(2, len(face)):
                        raw_mesh_verts.append(RawModelVertex(raw_vert_start))
                        raw_mesh_verts.append(RawModelVertex(raw_vert_start + i - 1))
                        raw_mesh_verts.append(RawModelVertex(raw_vert_start + i))
                        raw_mesh_count += 3
                    tex_idx = -1
                    for p in range(0, len(raw_textures)):
                        if str(raw_textures[p].name, 'utf-8') == brush.planes[j].texture_name:
                            tex_idx = p
                            break
                    if tex_idx == -1:
                        tex_idx = len(raw_textures)
                        raw_textures.append(RawTexture(bytes(brush.planes[j].texture_name, 'utf-8')))
                    raw_faces.append(
                        RawFace(tex_idx, raw_vert_start, len(face), raw_mesh_start, raw_mesh_count,
                                brush.planes[j].normal))
                    face_count += 1
            ent.pop("brushes")
            ent["model"] = "*" + str(len(raw_models))
            raw_models.append(RawModel(face_start, face_count))
    generate_time = time.time() - generate_time
    write_time = time.time()
    file_loc = HEADER_SIZE + RawChunkDirectoryEntry.size() * NUMBER_OF_CHUNKS + 1
    chunks = [
        (VertexChunk(raw_verts), VERTEX_CHUNK_TYPE),
        (ModelVertexChunk(raw_mesh_verts), MESH_VERTEX_CHUNK_TYPE),
        (FaceChunk(raw_faces), FACE_CHUNK_TYPE),
        (ModelChunk(raw_models), MODEL_CHUNK_TYPE),
        (EntityChunk(bytes(format_ents(ents), 'utf-8')), ENTITY_CHUNK_TYPE),
        (TextureChunk(raw_textures), TEXTURE_CHUNK_TYPE),
        (PlaneChunk(raw_planes), PLANE_CHUNK_TYPE),
        (BrushSideChunk(raw_brush_sides), BRUSH_SIDE_CHUNK_TYPE),
        (BrushChunk(raw_brushes), BRUSH_CHUNK_TYPE)
    ]
    idx = 0
    for c, t in chunks:
        entry = RawChunkDirectoryEntry(int.from_bytes(t, byteorder='little'),
                                       0,
                                       0,
                                       file_loc,
                                       c.length_bytes())
        output_file.seek(HEADER_SIZE + RawChunkDirectoryEntry.size() * idx)
        output_file.write(entry.serialize())
        output_file.seek(entry.start)
        bla = c.serialize()
        output_file.write(bla)
        file_loc = output_file.seek(0, io.SEEK_CUR) + 1  # 1 pad byte just because ;)
        idx += 1
    write_time = time.time() - write_time
    stats = [
        "Vertices: %d" % (len(raw_verts)),
        "ModelVertices: %d" % (len(raw_mesh_verts)),
        "Faces: %d" % (len(raw_faces)),
        "Models: %d" % (len(raw_models)),
        "Textures: %d" % (len(raw_textures)),
        "Planes: %d" % (len(raw_planes)),
        "BrushSides: %d" % (len(raw_brush_sides)),
        "Brushes: %d" % (len(raw_brushes)),
        "Map parse time: %f s" % (parse_time),
        "Map generate time: %f s" % (generate_time),
        "Gen: Find intersections: %f s" % (int_time),
        "Serialize+write time: %f s" % (write_time)

    ]
    print("==== STATS ====")
    for stat in stats:
        print(stat)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Tremor map compiler')
    parser.add_argument('--data-dir', dest='datadir', type=str, required=True)
    parser.add_argument('--map', dest='map', type=str, required=True)
    parser.add_argument('--output', dest='output', type=str, required=True)
    parser.add_argument('-v', dest='verbose', type=bool, default=False)
    args = parser.parse_args(sys.argv[1:])
    now = time.time()
    main(args)
    print("Compilation took %f s" % (time.time() - now))
