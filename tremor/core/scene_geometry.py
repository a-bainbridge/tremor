import numpy as np

from tremor.math.geometry import Plane
from tremor.math.vertex_math import norm_vec3


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

class Brush:

    def __init__(self, planes):
        self.planes = planes

    def point_in_brush(self, point):
        for p in self.planes:
            if p.point_dist(point) > 0.00001:
                return False
        return True

    def get_vertices(self):
        all_points = []
        i = 0
        for p1 in self.planes:
            i += 1
            p1_points = []
            j = 0
            for p2 in self.planes:
                j += 1
                # if i > j:
                #    continue
                k = 0
                for p3 in self.planes:
                    k += 1
                    if j > k:
                        continue
                    point = p1.intersect_point(p2, p3)
                    if point is not None and self.point_in_brush(point):
                        # print(i,j,k)
                        p1_points.append(point)
            if len(p1_points) < 3:
                continue
            com = center_of_mass(p1_points)
            vals = []
            tangent_vec = norm_vec3(p1_points[0] - com)
            quad_1 = []
            quad_2 = []
            quad_3 = []
            quad_4 = []
            for i in range(0, len(p1_points)):
                point = norm_vec3(p1_points[i] - com)
                values = (p1.point_dist(np.cross(tangent_vec, point) + com), tangent_vec.dot(point))
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
            all_points.append([p1_points[p] for p in quad_1 + quad_2 + quad_3 + quad_4])
        return all_points
