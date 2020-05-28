import time

import numpy as np

from tremor.core import console
from tremor.core.entity import Entity
from tremor.graphics.graphics_subsystem import GraphicsSubsystem
from tremor.input.input_subsystem import InputSubsystem
from tremor.loader.scene import binloader
from tremor.net.client.c_net import ClientNetworkSubsystem


def main():
    graphics_subsystem = GraphicsSubsystem()
    graphics_subsystem.init()
    input_subsystem = InputSubsystem()
    input_subsystem.init(graphics_subsystem)
    console.load_startup("startup.rc")
    net = ClientNetworkSubsystem()
    net.initialize()
    net.connect(("localhost", 27070))
    scene = binloader.load_scene_file("data/scenes/out.tmb")
    scene.active_camera = Entity()
    scene.active_camera.transform.set_translation(np.array([32, 32, 32]))
    scene.active_camera.gravity = True
    scene.entities.append(scene.active_camera)
    dt = 1 / 60.0
    while not graphics_subsystem.window_close_requested():
        start_time = time.time()
        input_subsystem.poll_events()
        net.handle_events()
        # todo console buffer here
        scene.tick(dt)
        net.write_outbound()
        graphics_subsystem.draw_scene(scene)
        graphics_subsystem.draw_console()
        graphics_subsystem.end_frame()
        end_time = time.time()
        dt = end_time - start_time
    net.shutdown()
    input_subsystem.shutdown()
    graphics_subsystem.shutdown()


if __name__ == "__main__":
    print("Do not run this package directly!")
