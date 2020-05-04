from enum import Enum, unique
from io import TextIOBase
from typing import Dict, Callable
import struct
from tremor.core.scene import Scene
from tremor.loader.scene import version0

version_map: Dict[int, Callable[[str, TextIOBase], Scene]] = {
    0: version0.load_scene0
}


def load_scene(file) -> Scene:
    if str.endswith(file, ".tsb"):
        # do something with binary files
        pass
    else:
        data_stream = open("data/scenes/source/"+file, "r", encoding="utf-8")
    hdr = data_stream.read(6)
    try:
        loader = version_map[format_version]
    except:
        raise Exception("Unknown format version " + str(format_version))
    name = str.rstrip(data_stream.readline())
    print("Loading scene: " + name)
    return loader(name, data_stream)
