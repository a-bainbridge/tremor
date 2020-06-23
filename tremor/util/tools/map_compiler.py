import argparse
import io
import math
import sys
import time

from tremor.core.scene_geometry import Brush, Plane, center_of_mass
from tremor.loader.scene.scene_types import *
from tremor.math.geometry import PlaneSide
from tremor.math.vertex_math import norm_vec3, magnitude_vec3

EPSILON = 1 / 32


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
    plane.texture_attributes = (float(temp[19]), float(temp[20]), float(temp[16]), float(temp[17]), float(temp[18]))
    plane.content = int(temp[21])
    plane.surface = int(temp[22])
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


def pre_process(ents):
    worldspawn_ent = None
    for ent in ents:
        if ent["classname"] == "info_player_start":
            sp = ent["origin"].split(" ")
            contained_point = np.array([float(sp[1]), float(sp[2]), -float(sp[0])])
            print(contained_point)
        if ent["classname"] == "worldspawn":
            worldspawn_ent = ent
    for brush in worldspawn_ent["brushes"]:
        brush.make_faces()
    return worldspawn_ent


class Face:
    def __init__(self):
        self.verts: List[List] = None
        self.checked = False
        self.plane = None

    # must be wound properly before this!
    def is_very_small(self):
        EDGE_EPSILON = 0.2
        edge_count = 0
        for i in range(0, len(self.verts)):
            delta = np.array(self.verts[(i + 1) % len(self.verts)]) - np.array(self.verts[i])
            length = magnitude_vec3(delta)
            if length > EDGE_EPSILON:
                edge_count += 1
                if edge_count == 3:
                    return False
        return True

    @staticmethod
    def from_plane(plane):
        hugeness_factor = 1E10
        face = Face()
        face.plane = plane
        verts = [None] * 4
        d = plane.normal[0] * plane.normal[0] + plane.normal[1] * plane.normal[1]
        if d == 0:
            left = np.array([1, 0, 0], dtype=np.float32)
        else:
            left = 1 / math.sqrt(d) * np.array([-plane.normal[1], plane.normal[0], 0], dtype=np.float32)
        down = np.cross(left, plane.normal)
        left *= hugeness_factor
        down *= hugeness_factor
        verts[0] = plane.point - left + down
        verts[1] = plane.point + left + down
        verts[2] = plane.point + left - down
        verts[3] = plane.point - left - down
        face.verts = verts
        face.wind()
        return face

    def wind(self, ccw=True):
        verts_copy = []
        com = center_of_mass(self.verts)
        vals = []
        tangent_vec = norm_vec3(np.array(self.verts[0]) - com)
        quad_1 = []
        quad_2 = []
        quad_3 = []
        quad_4 = []
        for i in range(0, len(self.verts)):
            point = norm_vec3(np.array(self.verts[i]) - com)
            values = (self.plane.point_dist(np.cross(tangent_vec, point) + com), tangent_vec.dot(point))
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
        verts_copy.append([self.verts[p] for p in quad_1 + quad_2 + quad_3 + quad_4])
        self.verts = verts_copy[0]

    def clip(self, plane, epsilon):
        distances = [0] * (len(self.verts) + 1)
        sides = [0] * (len(self.verts) + 1)
        counts = [0, 0, 0]
        for i in range(0, len(self.verts)):
            dist = plane.point_dist(self.verts[i])
            distances[i] = dist
            if dist > epsilon:
                sides[i] = PlaneSide.SIDE_FRONT
            elif dist < -epsilon:
                sides[i] = PlaneSide.SIDE_BACK
            else:
                sides[i] = PlaneSide.SIDE_ON
            counts[sides[i]] += 1
        sides[len(self.verts)] = sides[0]
        distances[len(self.verts)] = distances[0]
        if counts[PlaneSide.SIDE_FRONT] == 0:
            return self # is this bad?
        if counts[PlaneSide.SIDE_BACK] == 0:
            return self
        maxpoints = len(self.verts) + 4
        new_verts = []
        for i in range(0, len(self.verts)):
            p1 = self.verts[i]
            if len(new_verts) + 1 > maxpoints:
                return self
            if sides[i] == PlaneSide.SIDE_ON:
                new_verts.append(p1)
                continue
            if sides[i] == PlaneSide.SIDE_FRONT:
                new_verts.append(p1)
            if sides[i + 1] == PlaneSide.SIDE_ON or sides[i + 1] == sides[i]:
                continue
            if len(new_verts) + 1 > maxpoints:
                return self
            p2 = self.verts[(i + 1) % len(self.verts)]
            dot = distances[i] / (distances[i] - distances[i + 1])
            midpoint = [0, 0, 0]
            for j in range(0, 3):
                if plane.normal[j] == 1:
                    midpoint[j] = plane.d()
                elif plane.normal[j] == -1:
                    midpoint[j] = -plane.d()
                else:
                    midpoint[j] = p1[j] + dot * (p2[j] - p1[j])
                # todo do uv calculations before this and interpolate?
            new_verts.append(midpoint)
        self.verts = new_verts
        self.wind()
        return self

    def split(self, plane, epsilon):
        distances = [0] * (len(self.verts) + 1)
        sides = [0] * (len(self.verts) + 1)
        counts = [0, 0, 0]
        for i in range(0, len(self.verts)):
            dist = plane.point_dist(self.verts[i])
            distances[i] = dist
            if dist > epsilon:
                sides[i] = PlaneSide.SIDE_FRONT
            elif dist < -epsilon:
                sides[i] = PlaneSide.SIDE_BACK
            else:
                sides[i] = PlaneSide.SIDE_ON
            counts[sides[i]] += 1
        sides[len(self.verts)] = sides[0]
        distances[len(self.verts)] = distances[0]
        if counts[PlaneSide.SIDE_FRONT] == 0 and counts[PlaneSide.SIDE_BACK] == 0:
            # coplanar
            if plane.normal.dot(self.plane.normal) > 0:
                return self.verts, None
            else:
                return None, self.verts
        if counts[PlaneSide.SIDE_FRONT] == 0:
            return None, self.verts
        if counts[PlaneSide.SIDE_BACK] == 0:
            return self.verts, None
        front_verts = []
        back_verts = []
        for i in range(0, len(self.verts)):
            p1 = self.verts[i]
            if sides[i] == PlaneSide.SIDE_ON:
                front_verts.append(p1)
                back_verts.append(p1)
                continue
            if sides[i] == PlaneSide.SIDE_FRONT:
                front_verts.append(p1)
            if sides[i] == PlaneSide.SIDE_BACK:
                back_verts.append(p1)
            # don't generate a splitter point if we won't cross the plane
            if sides[i + 1] == PlaneSide.SIDE_ON or sides[i + 1] == sides[i]:
                continue
            p2 = self.verts[(i + 1) % len(self.verts)]

            if sides[i] == PlaneSide.SIDE_FRONT:
                dot = distances[i] / (distances[i] - distances[i + 1])
                midpoint = [0, 0, 0]
                for j in range(0, 3):
                    if plane.normal[j] == 1:
                        midpoint[j] = plane.d()
                    elif plane.normal[j] == -1:
                        midpoint[j] = -plane.d()
                    else:
                        midpoint[j] = p1[j] + dot * (p2[j] - p1[j])
                # todo do uv calculations before this and interpolate?
            else:
                dot = distances[i + 1] / (distances[i + 1] - distances[i])
                midpoint = [0, 0, 0]
                for j in range(0, 3):
                    if plane.normal[j] == 1:
                        midpoint[j] = plane.d()
                    elif plane.normal[j] == -1:
                        midpoint[j] = -plane.d()
                    else:
                        midpoint[j] = p2[j] + dot * (p1[j] - p2[j])
            front_verts.append(midpoint)
            back_verts.append(midpoint)
        return front_verts, back_verts


# https://github.com/TTimo/doom3.gpl/blob/master/neo/tools/compilers/dmap/facebsp.cpp
def make_structural_face_list(brushes):
    faces = []
    for brush in brushes:
        for side in brush.sides:
            if len(side.vertices) == 0:
                continue
            face = Face()
            face.plane = side.plane
            face.verts = side.vertices
            # face.wind() todo this one is probably unnecessary
            # face.portal = False
            faces.append(face)
    return faces


class Bounds:
    def __init__(self, mins, maxs):
        self.mins = mins
        self.maxs = maxs

    def __getitem__(self, item):
        if item == 0:
            return self.mins
        else:
            return self.maxs

    @staticmethod
    def min_bounds():
        b = Bounds(None, None)
        b.clear()
        return b

    def clear(self):
        self.mins = np.array([float("inf"), float("inf"), float("inf")])
        self.maxs = np.array([-float("inf"), -float("inf"), -float("inf")])

    def test_point_included(self, point):
        return (point[0] >= self.mins[0] and point[0] <= self.maxs[0]) and (
                    point[1] >= self.mins[1] and point[1] <= self.maxs[1]) and (
                           point[2] >= self.mins[2] and point[2] <= self.maxs[2])

    def grow_to_include(self, point):
        self.maxs[0] = max(self.maxs[0], point[0])
        self.maxs[1] = max(self.maxs[1], point[1])
        self.maxs[2] = max(self.maxs[2], point[2])
        self.mins[0] = min(self.mins[0], point[0])
        self.mins[1] = min(self.mins[1], point[1])
        self.mins[2] = min(self.mins[2], point[2])

    def include_point(self, point):
        inside = self.test_point_included(point)
        if inside:
            return
        self.grow_to_include(point)

    def copy(self):
        return Bounds(np.array([*self.mins]), np.array([*self.maxs]))


class Tree:
    def __init__(self):
        self.head = None
        self.outside_node = None
        self.bounds = Bounds.min_bounds()

    pass


class Node:
    def __init__(self, parent):
        self.children = [None, None]
        self.parent = parent
        self.opaque = False
        self.leaf = False
        self.plane = None
        self.brushes = []
        self.bounds = None
        self.portals = []
    pass


class Portal:
    def __init__(self):
        self.nodes = [None, None]
        self.winding: Face = None
        self.onnode = None

    def add_to_nodes(self, front, back):
        if self.nodes[0] is not None or self.nodes[1] is not None:
            raise Exception("Already in nodes")
        self.nodes[0] = front
        front.portals.append(self)
        self.nodes[1] = back
        back.portals.append(self)

    def remove_from_node(self, node):
        node.portals.remove(self)
        if node == self.nodes[0]:
            self.nodes[0] = None
        if node == self.nodes[1]:
            self.nodes[1] = None


BLOCK_SIZE = 1024


def select_split_plane(node, faces):
    if len(faces) == 0:
        return None
    halfSize = (node.bounds.maxs - node.bounds.mins) * 0.5
    for axis in range(0, 3):
        if halfSize[axis] > BLOCK_SIZE:
            dist = BLOCK_SIZE * (math.floor((node.bounds.mins[axis] + halfSize[axis]) / BLOCK_SIZE) + 1.0)
        else:
            dist = BLOCK_SIZE * (math.floor(node.bounds.mins[axis] / BLOCK_SIZE) + 1.0)
        if dist > node.bounds.mins[axis] + 1 and dist < node.bounds.maxs[axis] - 1.0:
            abcd = [0, 0, 0, -dist]
            abcd[axis] = 1.0
            plane = Plane.plane_from_abcd(abcd)
            return plane
    bestVal = -999999
    bestSplit = faces[0].plane
    # havePortals = False
    for face in faces:
        face.checked = False
        # if face.portal:
        #     havePortals = True
    for face_splitter in faces:
        if face_splitter.checked:
            continue
        # if havePortals != split.portal:
        #     continue
        splits = 0
        facing = 0
        front = 0
        back = 0
        face_splitter_plane = face_splitter.plane
        for check_face in faces:
            if check_face.plane == face_splitter.plane:
                facing += 1  # handles the ON case i suppose
                check_face.checked = True
                continue
            side = check_face.plane.side(face_splitter_plane)
            if side == PlaneSide.SIDE_CROSS:
                splits += 1
            elif side == PlaneSide.SIDE_FRONT:
                front += 1
            elif side == PlaneSide.SIDE_BACK:
                back += 1
        face_val = 5 * facing - 5 * splits  # heuristic!
        if face_splitter_plane.is_axial():
            face_val += 5  # weight axial planes higher!
        if face_val > bestVal:
            bestVal = face_val
            bestSplit = face_splitter
    if bestVal == -999999:
        return None
    return bestSplit.plane


leaf_counter = 0
CLIP_EPSILON = 0.1


def build_tree(node, faces, outfaces):
    global leaf_counter
    split_plane = select_split_plane(node, faces)
    if split_plane is None:
        node.leaf = True
        return
    node.plane = split_plane
    children = [[], []]
    for face in faces:
        if face.plane == node.plane:
            # face is destroyed
            continue
        side = face.plane.side(node.plane)
        if side == PlaneSide.SIDE_CROSS:
            front_winding, back_winding = face.split(node.plane, CLIP_EPSILON * 2)
            if front_winding is not None:
                newface = Face()
                newface.verts = front_winding
                newface.plane = face.plane
                newface.wind() # todo remove the need to do this
                children[0].append(newface)
                outfaces.append(newface)
            if back_winding is not None:
                newface = Face()
                newface.verts = back_winding
                newface.plane = face.plane
                newface.wind()  # todo remove the need to do this
                children[1].append(newface)
                outfaces.append(newface)
        elif side == PlaneSide.SIDE_FRONT:
            children[0].append(face)
            outfaces.append(face)
        elif side == PlaneSide.SIDE_BACK:
            children[1].append(face)
            outfaces.append(face)
    for i in range(0, 2):
        node.children[i] = Node(node)
        node.children[i].bounds = node.bounds.copy()

    for i in range(0, 3):
        if abs(split_plane.normal[i] - 1) < 0.001:
            node.children[0].bounds.mins[i] = split_plane.d()
            node.children[1].bounds.maxs[i] = split_plane.d()
            break

    for i in range(0, 2):
        build_tree(node.children[i], children[i], outfaces)


def face_bsp(faces):
    global leaf_counter
    leaf_counter = 0
    tree = Tree()
    for face in faces:
        for vert in face.verts:
            tree.bounds.include_point(vert)
    tree.head = Node(None)
    tree.head.bounds = tree.bounds
    new_face_list = []
    build_tree(tree.head, faces, new_face_list)
    return tree, new_face_list


padding = 8


def make_head_portals(tree):
    node = tree.head
    tree.outside_node = Node(None)
    tree.outside_node.opaque = False
    portals = [None] * 6
    planes = [None] * 6
    if node.leaf:
        return
    new_bounds = Bounds(np.array([-padding, -padding, -padding]) + tree.bounds.mins,
                        np.array([padding, padding, padding]) + tree.bounds.maxs)
    for i in range(0, 3):
        for j in range(0, 2):
            n = j * 3 + i
            p = Portal()
            if j == 1:
                plane = [0, 0, 0, new_bounds[j][i]]
                plane[i] = -1
            else:
                plane = [0, 0, 0, -new_bounds[j][i]]
                plane[i] = 1
            p.plane = Plane.plane_from_abcd(plane)
            planes[n] = p.plane
            p.winding = Face.from_plane(p.plane)
            portals[n] = p
            p.add_to_nodes(node, tree.outside_node)
    for portal in portals:
        if portal.winding is None:
            print("WTF!")
    for i in range(0, 6):
        for j in range(0, 6):
            if i == j:
                continue
            portals[i].winding = portals[i].winding.clip(planes[j], CLIP_EPSILON)

def calculate_node_bounds(node):
    node.bounds.clear()
    if len(node.portals) == 0:
        return
    idx = 0
    cur_portals = node.portals
    portal = node.portals
    while True:
        if idx == len(portal):
            return
        portal = portal[idx]
        for vert in portal.winding.verts:
            node.bounds.include_point(vert)
        s = portal.nodes[1] == node
        portal = portal.nodes[1].portals if s else portal.nodes[0].portals
        if portal == cur_portals:
            idx += 1
        else:
            idx = 0
            cur_portals = portal

WIND_EPSILON = 0.001
def base_winding_for_node(node):
    winding = Face.from_plane(node.plane)
    cur_node = node
    while True:
        if cur_node.parent is not None:
            cur_node = cur_node.parent
        else:
            break
        if cur_node.children[0] == node:
            winding = winding.clip(cur_node.plane, WIND_EPSILON)
        else:
            winding = winding.clip(cur_node.plane.new_reversed(), WIND_EPSILON)
        node = cur_node
    return winding

def split_node_portals(node):
    front_child = node.children[0]
    back_child = node.children[1]
    if len(node.portals) == 0:
        return
    portals = node.portals
    pidx = -1
    while True:
        pidx += 1
        if len(portals) <= pidx:
            break
        print(pidx)
        portal = portals[pidx]
        if portal.nodes[0] == node:
            side = 0
        else:
            side = 1
        next_portals = portal.nodes[side].portals
        if next_portals != portals:
            pidx = -1
            portals = next_portals
        other_node = portal.nodes[1 if side == 0 else 1]
        portal.remove_from_node(portal.nodes[0])
        portal.remove_from_node(portal.nodes[1])
        front_wind_v, back_wind_v = portal.winding.split(node.plane, WIND_EPSILON)
        if front_wind_v is not None:
            front_wind = Face()
            front_wind.verts = front_wind_v
            front_wind.plane = node.plane
            front_wind.wind() #todo no?
        else:
            front_wind = None
        if back_wind_v is not None:
            back_wind = Face()
            back_wind.verts = back_wind_v
            back_wind.plane = node.plane
            back_wind.wind() #todo no?
        else:
            back_wind = None
        if front_wind is not None and front_wind.is_very_small():
            front_wind = None
        if back_wind is not None and back_wind.is_very_small():
            back_wind = None
        if front_wind is None and back_wind is None:
            continue
        if front_wind is None:
            if side == 0:
                portal.add_to_nodes(back_child, other_node)
            else:
                portal.add_to_nodes(other_node, back_child)
            continue
        if back_wind is None:
            if side == 0:
                portal.add_to_nodes(front_child, other_node)
            else:
                portal.add_to_nodes(other_node, front_child)
            continue
        new_portal = Portal()
        new_portal.onnode = portal.onnode
        new_portal.winding = back_wind
        portal.winding = front_wind
        if side == 0:
            portal.add_to_nodes(front_child, other_node)
            new_portal.add_to_nodes(back_child, other_node)
        else:
            portal.add_to_nodes(other_node, front_child)
            new_portal.add_to_nodes(other_node, back_child)
    node.portals = []


def make_node_portal(node):
    winding = base_winding_for_node(node)
    idx = 0
    cur_portals = node.portals
    portal = node.portals
    while True:
        if idx == len(portal):
            break
        portal = portal[idx]
        plane = portal.winding.plane
        if portal.nodes[0] == node:
            side = 0
        elif portal.nodes[1] == node:
            side = 1
        else:
            print("Wrong portal?")
        winding = winding.clip(plane, CLIP_EPSILON)
        if winding is None:
            return
        portal = portal.nodes[side].portals
        if portal == cur_portals:
            idx += 1
        else:
            idx = 0
            cur_portals = portal
    if winding.is_very_small():
        return
    new_portal = Portal()
    new_portal.plane = node.plane
    new_portal.onnode = node
    new_portal.winding = winding
    new_portal.add_to_nodes(node.children[0], node.children[1])


def make_tree_portals_recursive(node):
    calculate_node_bounds(node)
    for i in range(0, 3):
        if node.bounds.mins[i] <= -1E10 or node.bounds.maxs[i] >= 1E10:
            print("bad bounds")
            break
    if node.leaf:
        return
    make_node_portal(node)
    split_node_portals(node)

    for i in range(0, 2):
        make_tree_portals_recursive(node.children[i])


def make_tree_portals(tree):
    make_head_portals(tree)
    make_tree_portals_recursive(tree.head)


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
    world_ent = pre_process(ents)
    world_structural_faces = make_structural_face_list(world_ent["brushes"])
    tree, faces = face_bsp(world_structural_faces)
    # make_tree_portals(tree)
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
    for ent in ents:
        if ent == world_ent:
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
            for face in faces:
                raw_vert_start = len(raw_verts)
                raw_mesh_start = len(raw_mesh_verts)
                raw_mesh_count = 0
                for i in range(0, len(face.verts)):
                    raw_verts.append(
                        RawVertex(face.verts[i], face.plane.normal, np.array([0, 0], dtype='float32')))
                for i in range(2, len(face.verts)):
                    raw_mesh_verts.append(RawModelVertex(raw_vert_start))
                    raw_mesh_verts.append(RawModelVertex(raw_vert_start + i - 1))
                    raw_mesh_verts.append(RawModelVertex(raw_vert_start + i))
                    raw_mesh_count += 3
                raw_faces.append(
                    RawFace(0, raw_vert_start, len(face.verts), raw_mesh_start, raw_mesh_count,
                            face.plane.normal))
                face_count += 1
            ent.pop("brushes")
            ent["model"] = "*" + str(len(raw_models))
            raw_models.append(RawModel(face_start, face_count))
            continue
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
                vertices = brush.get_vertices()
                for j in range(len(vertices)):
                    if brush.planes[j].texture_name == "__TB_empty" or brush.planes[j].surface & SURF_NODRAW:
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
