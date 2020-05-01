from typing import List

from tremor.core.entity import Entity


class Scene:
    def __init__(self, name: str):
        self.name = name
        self.elements: List[Entity] = []
        self.active_camera: Entity = None

    def tick(self):
        pass
