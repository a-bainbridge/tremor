import numpy as np

from tremor.math.vertex_math import norm_vec3, magnitude_vec3


class Plane:
    def __init__(self, point: np.ndarray, normal: np.ndarray):
        self.point = point
        self.normal = norm_vec3(normal)

    @staticmethod
    def plane_from_points(v0: np.ndarray, v1: np.ndarray, v2: np.ndarray) -> "Plane":
        n = norm_vec3(np.cross((v1 - v0), (v2 - v0)))
        return Plane(v0, n)

    @staticmethod
    def plane_from_points_quake_style(points) -> "Plane":
        n = norm_vec3(np.cross((points[2] - points[0]), (points[1] - points[0])))
        return Plane(points[0], n)

    def point_dist(self, point: np.ndarray):
        return self.normal.dot(point - self.point)

    def ray_intersect(self, ray_origin, ray_vector, epsilon=0):
        vdn = ray_vector.dot(self.normal)
        if vdn >= 0:
            return None
        t = (-(ray_origin.dot(self.normal) - self.normal.dot(self.point))) / vdn
        if t < 0:
            return None
        t -= epsilon
        return ray_origin + t * ray_vector

    def intersect_point(self, p1: "Plane", p2: "Plane", epsilon=0.0000002):
        # n1 dot n2 cross n3 == 0, single point of intersection
        # n1 dot n2 cross n3 != 0, no points or infinite points of intersection
        a = p2.normal.dot(np.cross(self.normal, p1.normal))
        if abs(a) < epsilon:
            # print("no single point intersection")
            return None
        A = np.array([
            self.normal,
            p1.normal,
            p2.normal
        ])
        B = np.array([
            self.normal.dot(self.point),
            p1.normal.dot(p1.point),
            p2.normal.dot(p2.point)
        ])
        x = np.linalg.solve(A, B)
        return x


class AABB:
    # min_extent.x <= max_extent.x, min_extent.y <= max_extent.y, min_extent.z <= max_extent.z
    def __init__(self, min_extent: np.ndarray, max_extent: np.ndarray):
        self.min_extent = min_extent
        self.max_extent = max_extent
        self.other_verts = AABB._gen_verts(min_extent, max_extent)
        self.center = (max_extent + min_extent) / 2

    def aabb_center_distance(self, other):
        return magnitude_vec3(self.center - other.center)

    # todo this is technically incorrect for sweeps
    def sit_against_plane(self, plane: Plane):
        closest_dist = 1E9
        for i in range(0, 8):
            if i == 0:
                cur_point = self.min_extent
            elif i == 1:
                cur_point = self.max_extent
            else:
                cur_point = self.other_verts[i - 2]
            cur_dist = plane.point_dist(cur_point)
            if cur_dist < closest_dist:
                closest_dist = cur_dist
        return self.translate_new_aabb(closest_dist * -plane.normal)

    def translate_new_aabb(self, translate_vec: np.ndarray):
        return AABB(self.min_extent + translate_vec, self.max_extent + translate_vec)

    @staticmethod
    def _gen_verts(min_extent: np.ndarray, max_extent: np.ndarray):
        other = np.empty((6, 3), dtype='float32')
        # other 0,1,2 in xz of min_extent
        other[0][0] = max_extent[0]
        other[0][1] = min_extent[1]
        other[0][2] = max_extent[2]

        other[1][0] = min_extent[0]
        other[1][1] = min_extent[1]
        other[1][2] = max_extent[2]

        other[2][0] = max_extent[0]
        other[2][1] = min_extent[1]
        other[2][2] = min_extent[2]
        # other 3,4,5 in xz of max_extent
        other[3][0] = min_extent[0]
        other[3][1] = max_extent[1]
        other[3][2] = min_extent[2]

        other[4][0] = max_extent[0]
        other[4][1] = max_extent[1]
        other[4][2] = min_extent[2]

        other[5][0] = min_extent[0]
        other[5][1] = max_extent[1]
        other[5][2] = max_extent[2]
        return other

    @staticmethod
    def point():
        return AABB(np.array([0, 0, 0], dtype='float32'), np.array([0, 0, 0], dtype='float32'))

    @staticmethod
    def cube(s):
        return AABB(np.array([-s, -s, -s], dtype='float32'), np.array([s, s, s], dtype='float32'))
