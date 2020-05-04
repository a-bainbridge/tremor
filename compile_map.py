import sys, getopt, struct
import numpy as np

from tremor.core.scene_geometry import Brush, Plane


def write_map():
    struct.pack('BBBB', 0, 0xDE, 0xAD, 0xBE, 0xE5, 0x01)  # dead bees!


def parse_vec(block: str) -> np.ndarray:
    block = str.split(block, " ")
    return np.array([float(block[0]), float(block[1]), float(block[2])], dtype="float32")


def parse_plane_from_line(line: str) -> Plane:
    chunks = line.split(",")
    point = parse_vec(chunks[0])
    normal = parse_vec(chunks[1])
    surface_name = chunks[2]
    tex_off_x = float(chunks[3])
    tex_off_y = float(chunks[4])
    plane = Plane(point, normal)
    plane.surface_name = surface_name
    plane.tex_off_x = tex_off_x
    plane.tex_off_y = tex_off_y
    return plane


def main(argv):
    if len(argv) != 2:
        print("Usage: compile_map.py in_file out_file")
        return
    in_f = argv[0]
    print("Compiling " + in_f)
    file = open(in_f, "r", encoding="utf-8")
    print(str.strip(file.readline()))
    print(str.strip(file.readline()))
    ents = []
    current_ent = {}
    current_planes = []
    in_ent = False
    in_brush = False
    while True:
        line = file.readline()
        if line == "":
            break
        line = str.strip(line)
        if line == "":
            continue
        first = line[0]
        if first == "{":
            if not in_ent:
                in_ent = True
                current_ent = {"brushes": []}
                continue
            if in_ent and not in_brush:
                in_brush = True
                current_planes = []
                continue
            if in_ent and in_brush:
                raise Exception("bad block")
        if first == "}":
            if not in_ent and not in_brush:
                raise Exception("not in block")
            if in_brush:
                in_brush = False
                current_ent["brushes"].append(Brush(current_planes))
                continue
            if in_ent:
                in_ent = False
                ents.append(current_ent)
                continue
        if not in_ent:
            raise Exception("field outside block")
        if in_ent and not in_brush:
            line_split = line.split(" ")
            current_ent[line_split[0]] = line_split[1]
        if in_brush:
            current_planes.append(parse_plane_from_line(line))
    write_map()


if __name__ == "__main__":
    main(sys.argv[1:])
