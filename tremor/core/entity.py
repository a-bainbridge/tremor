from typing import List

import numpy as np

from tremor.math.geometry import AABB
from tremor.math.transform import Transform


class Entity:
    def __init__(self):
        self.transform = Transform(self)
        self.mesh = None
        self._node_idx = -1
        self.children: List[Entity] = []
        self.parent: Entity = None
        self.classname = ""
        self.velocity = np.array([0, 0, 0], dtype='float32')
        self.boundingbox: AABB = AABB.point()
        self.gravity = False

    def is_renderable(self):
        return self.mesh is not None
