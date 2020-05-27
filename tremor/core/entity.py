from typing import List

from tremor.graphics.mesh import Mesh
from tremor.math.geometry import AABB
from tremor.math.transform import Transform

import numpy as np


class Entity:
    def __init__(self):
        self.transform = Transform(self)
        self.mesh: Mesh = None
        self._node_idx = -1
        self.children: List[Entity] = []
        self.parent: Entity = None
        self.classname = ""
        self.velocity = np.array([0, 0, 0], dtype='float32')
        self.boundingbox: AABB = None
        self.gravity = False

    def is_renderable(self):
        return self.mesh is not None
