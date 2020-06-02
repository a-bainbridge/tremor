import numpy


# some of these are meant for obj format (elemented arrays), and stl formats (verticies per triangle)

def get_normals(vertex_data, right_hand=True):  # binary vertex data, 3 groups of 3 float 32s represent a triangle
    """
    a______b
     \    /
      \  /
       \/
       c

    assume triangle abc has a normal facing OUT of the screen
    that is, the vertices are in the order (c, b, a), (b, a, c), or (a, c, b)
    using RHR, (b - c) x (a - c) gives us the normal direction
    """
    normals = numpy.array([], dtype='float32')
    for ind in range(0, len(vertex_data), 9):
        v = vertex_data[ind:ind + 9]
        a, b, c = v[0], v[1], v[2]  # A
        i, j, k = v[3], v[4], v[5]  # B
        x, y, z = v[6], v[7], v[8]  # C
        bc = (i - x, j - y, k - z)
        ac = (a - x, b - y, c - z)
        norm = norm_vec3(cross_array(bc, ac) if right_hand else cross_array(ac, bc))
        normals = numpy.append(normals, norm)
        normals = numpy.append(normals, norm)
        normals = numpy.append(normals, norm)
    return normals


def get_normals_from_faces(normals_per_face, faces):
    # assume faces is a 2d array, not collapsed. dimensions of X by 3
    # assuming normals are in the order of the faces,
    # apply the normal to each vertex corresponding to the face
    normals_per_vertex = []  # 2d list
    f_index = -1
    for norm in normals_per_face:
        f_index += 1
        f = faces[f_index]
        for fv in f:
            while len(normals_per_vertex) <= fv:
                normals_per_vertex.append([0, 0, 0])
            normals_per_vertex[fv] = norm
    return numpy.asarray(normals_per_vertex, dtype='float32').flatten()


def find_faces_for_vertex(vertex_index: int, faces: list):
    # faces is 1d list
    found_faces = []
    for f in faces:
        for fv in f:
            if fv == vertex_index:
                found_faces.append(f)
                break
    return found_faces


def find_vertices_for_face(face, vertices):
    # assume face is array
    # assume vertices is 2d array
    verts = []
    for v in face:
        verts.append(vertices[v])
    return verts


def get_normal_for_face(face, vertices):
    # assume face is array
    # assume vertices is 2d array
    verts = find_vertices_for_face(face, vertices)
    a, b, c = verts[0][0], verts[0][1], verts[0][2]  # A
    i, j, k = verts[1][0], verts[1][1], verts[1][2]  # B
    x, y, z = verts[2][0], verts[2][1], verts[2][2]  # C
    CA = [x - a, y - b, z - c]
    CB = [x - i, y - j, z - k]
    norm = cross(CB[0], CB[1], CB[2], CA[0], CA[1], CA[2])
    return numpy.array(norm_vec3(norm), dtype='float32')


def get_normals_from_obj(vertex_pos, faces):
    # assume vertex_pos is 2d array
    # assume faces is 2d array
    # returns a 2d array of normals

    # need a normal per vertex
    # a vertex's normal is determined by the normals of the faces it's connected to
    # thus, for each vertex index:
    #   we must look it up in the faces,
    #   find the other vertices,
    #   determine the normal of each triangle it's connected to,
    #   and average all of the collected normals, and store it at that index
    normals = []
    vi = -1
    for v in vertex_pos:
        vi += 1
        v_faces = find_faces_for_vertex(vi, faces)
        norm = numpy.array([0, 0, 0], dtype='float32')
        for f in v_faces:
            n = get_normal_for_face(f, vertex_pos)
            norm += n
        norm /= len(v_faces)  # average all the normals
        norm = norm_vec3(norm)  # normalize it
        normals.append(norm)
    return normals


def cross(a, b, c, x, y, z):
    """
    | i j k |
    | a b c | = <a, b, c> x <x, y, z>
    | x y z |
    """
    return numpy.array([b * z - y * c, c * x - z * a, a * y - x * b], dtype='float32')


def dot(a, b, c, x, y, z):
    return a * x + b * y + c * z


def cross_array(v1, v2):
    return cross(v1[0], v1[1], v1[2], v2[0], v2[1], v2[2])


def dot_array(a, b):
    return dot(a[0], a[1], a[2], b[0], b[1], b[2])


def magnitude_vec3(vec):
    return numpy.sqrt(vec[0] * vec[0] + vec[1] * vec[1] + vec[2] * vec[2])


def magnitude_horizontal(vec):
    return numpy.sqrt(vec[0] * vec[0] + vec[2] * vec[2])

def norm_vec3(vec):
    mag = max(numpy.sqrt(vec[0] * vec[0] + vec[1] * vec[1] + vec[2] * vec[2]), 0.0001)
    return numpy.array([vec[0] / mag, vec[1] / mag, vec[2] / mag], dtype='float32')


def norm_vec(vec):
    mag = max(numpy.sqrt(sum([n * n for n in vec])), 0.00001)
    return numpy.asarray([n / mag for n in vec], dtype='float32')


def clamp_horizontal(vec, maximum_velocity):
    horiz_mag = magnitude_horizontal(vec)
    if horiz_mag > maximum_velocity:
        scale_factor = maximum_velocity / horiz_mag
        vec[0] = vec[0] * scale_factor
        vec[2] = vec[2] * scale_factor


def quaternion_multiply(quaternion1, quaternion0):
    w0, x0, y0, z0 = quaternion0
    w1, x1, y1, z1 = quaternion1
    return numpy.array([-x1 * x0 - y1 * y0 - z1 * z0 + w1 * w0,
                        x1 * w0 + y1 * z0 - z1 * y0 + w1 * x0,
                        -x1 * z0 + y1 * w0 + z1 * x0 + w1 * y0,
                        x1 * y0 - y1 * x0 + z1 * w0 + w1 * z0], dtype=numpy.float32)


# vec2 rotate2D (vec2 p, float angle){
#     return vec2(p.x*cos(angle)-p.y*sin(angle), p.y*cos(angle)+p.x*sin(angle));
# }
# a + bi + cj + dk
# ij = k
# i^2 = j^2 = k^2 = -1
# ki = j
def rotate2D(v, angle):
    return numpy.array([
        v[0] * numpy.cos(angle) - v[1] * numpy.sin(angle),
        v[1] * numpy.cos(angle) + v[0] * numpy.sin(angle)
    ], dtype='float32')


def euler(anglex, angley, anglez, v):
    # y then x then z
    # yxz
    yr = rotate2D([v[0], v[2]], angley)
    v[0] = yr[0]
    v[2] = yr[1]
    xr = rotate2D([v[1], v[2]], anglex)
    v[1] = xr[0]
    v[2] = xr[1]
    zr = rotate2D([v[0], v[1]], anglez)
    v[0] = zr[0]
    v[1] = zr[1]
    return v


def concat(*args):
    arr = numpy.array([], dtype='float32')
    for a in args:
        arr = numpy.append(arr, a)
    return arr


class ModelOp:
    @staticmethod
    def scale(model, scale_v: numpy.ndarray):
        nm = numpy.array(model, dtype='float32')
        nm[::3] = model[::3] * scale_v[0]  # x
        nm[1::3] = model[1::3] * scale_v[1]  # y
        nm[2::3] = model[2::3] * scale_v[2]  # z
        return nm

    @staticmethod
    def translate(model: numpy.ndarray, trans_v: numpy.ndarray):
        nm = numpy.array([], dtype='float32')
        nm[::3] = model[::3] + trans_v[0]
        nm[1::3] = model[1::3] + trans_v[1]
        nm[2::3] = model[2::3] + trans_v[2]
        return nm
