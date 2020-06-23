import numpy as np

from tremor.math.geometry import Plane
from tremor.math.vertex_math import norm_vec3, magnitude_vec3


def center_of_mass(points: np.array) -> np.array:
    if len(points) == 0:
        raise Exception('wtf')
    x_accum = 0
    y_accum = 0
    z_accum = 0
    for point in points:
        x_accum += point[0]
        y_accum += point[1]
        z_accum += point[2]
    n = len(points)
    return np.array([x_accum, y_accum, z_accum]) / n


def check_ccw(v0, v1, v2, p):
    if Plane.plane_from_points(v0, v1, v2).normal.dot(p.normal) < 0:
        # bad normal!
        print("bad normal detected!")


class Side:
    pass


class Brush:

    def __init__(self, planes):
        self.contents = 0
        self.planes = planes
        self.windings = None

    def point_in_brush(self, point, epsilon=0.0001):
        for p in self.planes:
            if p.point_dist(point) > epsilon:
                return False
        return True

    def get_ray_intersection(self, ray_origin, ray_vector, distance, epsilon=0):
        plausible_intersection_points = []
        for plane in self.planes:
            point = plane.ray_intersect(ray_origin, ray_vector, epsilon)
            if point is not None:
                plausible_intersection_points.append([point, plane])
        candidate_points = []
        outside_points = []
        for plausible_point in plausible_intersection_points:
            if magnitude_vec3(ray_origin - plausible_point[0]) > distance:
                continue
            if not self.point_in_brush(plausible_point[0], 0.0001 + epsilon):
                outside_points.append(plausible_point)
                continue
            candidate_points.append(plausible_point)
        if len(candidate_points) == 1:
            return candidate_points[0][0], \
                   magnitude_vec3(ray_origin - candidate_points[0][0]) / distance, \
                   candidate_points[0][1]
        if len(candidate_points) == 0:
            return None, None, None
        closest_candidate = None
        closest_dist = 9E99
        plane = None
        for p in candidate_points:
            dist = magnitude_vec3(ray_origin - p[0])
            if dist < closest_dist:
                closest_dist = dist
                closest_candidate = p[0]
                plane = p[1]
        return closest_candidate, closest_dist / distance, plane

    def gen_vertices(self):
        all_points = []
        i = 0
        for p1 in self.planes:
            i += 1
            p1_points = []
            j = 0
            for p2 in self.planes:
                j += 1
                k = 0
                for p3 in self.planes:
                    k += 1
                    if j > k:
                        continue
                    point = p1.intersect_point(p2, p3)
                    if point is not None and self.point_in_brush(point):
                        p1_points.append(point)
            if len(p1_points) < 3:
                all_points.append([])
                continue
            all_points.append(p1_points)
        self.windings = all_points
        self.wind()

    def get_vertices(self):
        return self.windings

    def wind(self, ccw=True):
        j = 0
        all_points = []
        for face in self.windings:
            if len(face) == 0:
                all_points.append([])
                j += 1
                continue
            com = center_of_mass(face)
            vals = []
            tangent_vec = norm_vec3(face[0] - com)
            quad_1 = []
            quad_2 = []
            quad_3 = []
            quad_4 = []
            for i in range(0, len(face)):
                point = norm_vec3(face[i] - com)
                values = (self.planes[j].point_dist(np.cross(tangent_vec, point) + com), tangent_vec.dot(point))
                if values[0] >= 0:
                    if values[1] >= 0:
                        quad_1.append(i)
                    else:
                        quad_2.append(i)
                else:
                    if values[1] < 0:
                        quad_3.append(i)
                    else:
                        quad_4.append(i)
                vals.append(values)
            quad_1.sort(key=lambda x: (-1 if vals[x][0] < 0 else 1) * vals[x][1], reverse=True)
            quad_2.sort(key=lambda x: (-1 if vals[x][0] < 0 else 1) * vals[x][1], reverse=True)
            quad_3.sort(key=lambda x: (-1 if vals[x][0] < 0 else 1) * vals[x][1], reverse=True)
            quad_4.sort(key=lambda x: (-1 if vals[x][0] < 0 else 1) * vals[x][1], reverse=True)
            all_points.append([self.windings[j][p] for p in quad_1 + quad_2 + quad_3 + quad_4])
            j += 1
        self.windings = all_points

    def make_faces(self):
        if self.windings is None:
            self.gen_vertices()
        verts_tmp = self.get_vertices()
        self.sides = []
        i = 0
        for plane in self.planes:
            side = Side()
            self.contents |= plane.content
            side.surface = plane.surface
            side.texture_name = plane.texture_name
            side.texture_attributes = plane.texture_attributes
            side.vertices = verts_tmp[i]
            side.plane = plane
            self.sides.append(side)
            i += 1
