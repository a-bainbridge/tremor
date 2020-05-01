from collections import Callable
from enum import Enum, unique
from typing import Dict, List

from tremor.core.scene import Scene
import numpy as np

from tremor.core.entity import Entity
from tremor.loader.gltf_loader import load_gltf
from tremor.math import matrix

def load_scene0(name, data_stream) -> Scene:
    has_resources = False
    has_elements = False
    state = State.NO_BLOCK
    resource_entries = {}
    element_entries = []
    while True:
        line = data_stream.readline()
        if line == "":
            break
        line = str.rstrip(line)
        print(line)
        if line == "":
            continue  # this is a different case than the check above, trust me
        split = str.split(line, " ")
        cmd = split[0]
        if cmd == "{":  # handle block start
            if not len(split) == 2:
                raise Exception("Malformed block start")
            if not state == State.NO_BLOCK:
                raise Exception("Block open before a close")
            block_name = split[1]
            if block_name == "resources":
                state = State.RESOURCE_BLOCK
                has_resources = True
            elif block_name == "elements":
                if has_resources:
                    state = State.ELEMENT_BLOCK
                    has_elements = True
                else:
                    raise Exception("Resources must be defined before elements")
            else:
                raise Exception("Unknown block " + block_name)
        elif cmd == "}":  # handle block end
            if not len(split) == 1:
                raise Exception("Malformed block end")
            if state == State.NO_BLOCK:
                raise Exception("Block end outside of a block")
            state = State.NO_BLOCK
        elif cmd == "lr":
            if not len(split) == 4:
                raise Exception("Malformed load resource command")
            if not state == State.RESOURCE_BLOCK:
                raise Exception("Load resource command outside of resource block")
            resource_entries[split[1]] = {"format": split[2], "location": split[3]}
        elif cmd == "ce":
            if not len(split) == 12:
                raise Exception("Malformed create element command")
            if not state == State.ELEMENT_BLOCK:
                raise Exception("Create element command outside of resource block")
            element_entries.append({"name": split[1], "resource": split[2],
                                    "translation": np.array([float(split[3]), float(split[4]), float(split[5])],
                                                            dtype='float32'),
                                    "rotation_angles": np.array([float(split[6]), float(split[7]), float(split[8])],
                                                                dtype='float32'),
                                    "scale": np.array([float(split[9]), float(split[10]), float(split[11])],
                                                      dtype='float32')})
        else:
            raise Exception("Unknown command " + cmd)
    if not state == State.NO_BLOCK:
        raise Exception("Parse ended in unclean state")
    if not has_resources or not has_elements:
        raise Exception("Missing one or more required sections")
    scene = Scene(name)
    for raw_elem in element_entries:
        raw_res = resource_entries[raw_elem["resource"]]
        if raw_res["format"] == "gltf":
            loader = load_gltf
        else:
            loader = None
        # i'm not entirely happy with the loader producing SceneElements, todo come up with a different approach
        loaded_mesh = loader(raw_res["location"])
        parent_elem = Entity(raw_elem["name"])
        parent_elem.transform.set_translation(raw_elem["translation"])
        parent_elem.transform.set_rotation(matrix.quaternion_from_angles(raw_elem["rotation_angles"], degrees=True))
        parent_elem.transform.set_scale(raw_elem["scale"])
        parent_elem.mesh = loaded_mesh
        scene.elements.append(parent_elem)
    return scene

@unique
class State(Enum):
    RESOURCE_BLOCK = 0
    ELEMENT_BLOCK = 1
    NO_BLOCK = 2
