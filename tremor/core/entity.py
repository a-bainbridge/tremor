from typing import List

from tremor.graphics.element_renderer import ElementRenderer
from tremor.math.transform import Transform


class Entity:
    def __init__(self, name):
        self.transform = Transform(self)
        self.mesh = None
        self.name = name
        self._node_idx = -1
        self.children: List[Entity] = []
        self.parent: Entity = None

    def __str__(self):
        return self.name + " (Entity-" + str(self.__hash__()) + ")"

    def is_renderable(self):
        return self.mesh is not None
