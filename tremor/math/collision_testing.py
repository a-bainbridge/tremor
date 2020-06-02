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

# todo fix: you can walk through slim brushes, minkowski the shit out of this?
def trace(start_point: np.ndarray, end_point: np.ndarray, aabb: AABB):
    aabb = aabb.translate_new_aabb(start_point - aabb.center)
    diff = end_point - start_point
    direction = norm_vec3(diff)
    dist = magnitude_vec3(diff)
    points = [aabb.min_extent, aabb.max_extent, *aabb.other_verts]
    intersected_points = []
    for brush in world:
        for point in points:
            intersection, span, plane = brush.get_ray_intersection(point, direction, dist)
            if intersection is None:
                continue
            intersected_points.append([intersection, span, brush, plane])
    best_intersection_span = 9E99
    best_intersection_brush = None
    plane = None
    for intersected in intersected_points:
        if intersected[1] < best_intersection_span:
            best_intersection_span = intersected[1]
            best_intersection_brush = intersected[2]
            plane = intersected[3]
    if best_intersection_span > 1:
        best_intersection_span = 1
    return TraceResult(plane is not None,
                       best_intersection_span * diff + start_point,
                       best_intersection_span,
                       plane,
                       best_intersection_brush,
                       None if plane is None else plane.normal)

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
