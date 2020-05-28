from typing import List

import numpy as np

from tremor.core.scene_geometry import Brush
from tremor.math.geometry import Plane, AABB
from tremor.math.vertex_math import norm_vec3, magnitude_vec3

world: List[Brush] = []


class TraceResult:
    def __init__(self, collided: bool, end_point: np.ndarray, path_frac: float, plane_hit: Plane, brush_hit: Brush,
                 surface_normal: np.ndarray):
        self.collided = collided
        self.end_point = end_point
        self.path_frac = path_frac
        self.plane_hit = plane_hit
        self.brush_hit = brush_hit
        self.surface_normal = surface_normal

    def __str__(self):
        return "TraceResult: {collided:" + str(self.collided) + ", end:" + str(self.end_point) + ", frac:" + str(
            self.path_frac) + "}"


# todo don't let large traces pass through objects
def trace(start_point: np.ndarray, end_point: np.ndarray, aabb: AABB):
    og_aabb = aabb
    aabb = aabb.translate_new_aabb(start_point - aabb.center)
    diff = end_point - start_point
    direction = norm_vec3(diff)
    end_aabb = aabb.translate_new_aabb(diff)
    intersected_brushes = []
    for brush in world:
        if brush.point_in_brush(end_aabb.min_extent):
            intersected_brushes.append(brush)
            continue
        if brush.point_in_brush(end_aabb.max_extent):
            intersected_brushes.append(brush)
            continue
        for point in end_aabb.other_verts:
            if brush.point_in_brush(point):
                if brush not in intersected_brushes:
                    intersected_brushes.append(brush)
    new_aabbs = []
    for brush in intersected_brushes:
        for plane in brush.planes:
            t = end_aabb.sit_against_plane(plane)
            if t is not None:
                new_aabbs.append((t, plane, brush))
    min_move = 1E9
    min_aabb = None
    min_plane = None
    min_brush = None
    for bb, plane, brush in new_aabbs:
        center_move = bb.aabb_center_distance(aabb)
        if min_move > center_move:
            min_move = center_move
            min_aabb = bb
            min_plane = plane
            min_brush = brush
    if min_aabb is None:
        return TraceResult(False, end_aabb.center, 1.0, None, None, None)
    else:
        r_e = magnitude_vec3(min_aabb.center - start_point)
        w_e = magnitude_vec3(end_point - start_point)
        if r_e / w_e > 1:
            print("WTF! %f %f %f" % (r_e / w_e, r_e, w_e))
            print(start_point)
            print(end_point)
            print(start_point + (r_e / w_e) * (end_point - start_point))
        return TraceResult(True, min_aabb.center, (r_e / w_e), min_plane, min_brush, min_plane.normal)


def clamp_velocity(velocity: np.ndarray, trace_res: TraceResult):
    velocity = np.array(velocity, dtype='float64')
    new = velocity - (velocity.dot(trace_res.surface_normal) * trace_res.surface_normal)
    for i in range(0, 3):
        if np.abs(new[i]) < 1E-5:
            new[i] = 0
    new_mag = magnitude_vec3(new)
    old_mag = magnitude_vec3(velocity)
    if new_mag > old_mag > 0 and new_mag > 0:
        new = new / new_mag * old_mag
    return new
