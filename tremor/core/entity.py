from typing import List

import numpy as np

from tremor.math.geometry import AABB
from tremor.math.transform import Transform


class Entity:
    FLAG_WORLD = 1
    FLAG_GRAVITY = 2
    FLAG_PLAYER = 4
    FLAG_FAKE = 8
    FLAG_NO_COLLIDE = 16
    FLAG_SPECIAL = 32
    FLAG_BOUNCY = 64
    FLAG_INVINCIBLE = 128
    FLAG_NO_TRANSMIT = 256
    def __init__(self):
        self.transform = Transform(self)
        self.mesh = None
        self._node_idx = -1
        self.children: List[Entity] = []
        self.parent: Entity = None
        self.classname = ""
        self.velocity = np.array([0, 0, 0], dtype='float32')
        self.boundingbox: AABB = AABB.cube(1)
        self.flags = 0
        self.needs_update = False

    def is_renderable(self):
        return self.mesh is not None
