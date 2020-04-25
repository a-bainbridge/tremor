import numpy as np
import vertex_math


def create_new_projection_matrix(fFrustumScale, fzNear, fzFar):
    arr = np.zeros(16, dtype='float32')
    arr[0] = fFrustumScale
    arr[5] = fFrustumScale
    arr[10] = (fzFar + fzNear) / (fzNear - fzFar)
    arr[14] = (2 * fzFar * fzNear) / (fzNear - fzFar)
    arr[11] = -1.0
    return arr

def create_projection_matrix(fov, aspect_ratio, near_clip, far_clip):
    tan_half_fov = np.tan(0.5 * fov * (np.pi / 180.0))
    arr = np.zeros((4, 4), dtype='float32')
    arr[0][0] = 1 / (aspect_ratio * tan_half_fov)
    arr[1][1] = 1 / tan_half_fov
    arr[2][2] = (far_clip + near_clip) / (near_clip - far_clip)
    arr[2][3] = -1
    arr[3][2] = (2 * far_clip * near_clip) / (near_clip - far_clip)
    return arr


def create_translation_matrix(translation_vec):
    arr = np.identity(4, dtype='float32')
    arr[0][3] = translation_vec[0]
    arr[1][3] = translation_vec[1]
    arr[2][3] = translation_vec[2]
    return arr


def create_rotation_matrix(x, y, z):
    return np.array([[x[0], x[1], x[2], 0],
                     [y[0], y[1], y[2], 0],
                     [z[0], z[1], z[2], 0],
                     [0, 0, 0, 1]], dtype='float32')

def create_scale_matrix (x, y=None, z=None):
    if y is None or z is None:
        y = x
        z = x
    m = np.identity(4, dtype='float32')
    m[0][0] *= x
    m[1][1] *= y
    m[2][2] *= z
    return m


def look_at(position, target, up):
    zaxis = vertex_math.norm_vec3(target - position)
    xaxis = vertex_math.norm_vec3(vertex_math.cross_array(vertex_math.norm_vec3(up), zaxis))
    yaxis = vertex_math.cross_array(zaxis, xaxis)  # quick maths
    rotation = create_rotation_matrix(xaxis, yaxis, zaxis)
    translation = create_translation_matrix(position * -1)
    #rotation[3] = [-np.dot(xaxis, position), -np.dot(zaxis, position), -np.dot(yaxis, position), 1]
    return translation * rotation

def flatten(mat4):
    arr = np.zeros(16, dtype='float32')
    for j in range(0, 3):
        for i in range(0, 3):
            k = i+4*j
            arr[k] = mat4[j][i]
    return arr








