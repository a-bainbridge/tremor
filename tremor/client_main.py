import time

import numpy as np

from tremor.core import console
from tremor.core.entity import Entity
from tremor.graphics import graphics_subsystem
from tremor.graphics.ui.state import UIState
from tremor.input import input_subsystem
from tremor.loader.scene import binloader
from tremor.net.client import client_net


def main():
    graphics_subsystem.init()
    graphics_subsystem.ui_state = UIState.MAIN_MENU
    input_subsystem.init()
    console.load_startup("startup.rc")
    client_net.init()
    #net.connect(("localhost", 27070))
    # scene = binloader.load_scene_file("data/scenes/out.tmb")
    # scene.active_camera = Entity()
    # scene.active_camera.transform.set_translation(np.array([32, 32, 32]))
    # scene.active_camera.gravity = True
    # scene.entities.append(scene.active_camera)
    dt = 1 / 60.0
    while not graphics_subsystem.window_close_requested():
        start_time = time.time()
        input_subsystem.poll_events()
        client_net.handle_events()
        # todo console buffer here
        #scene.tick(dt)
        client_net.write_outbound()
        graphics_subsystem.draw_scene(None)
        graphics_subsystem.draw_ui()
        graphics_subsystem.end_frame()
        end_time = time.time()
        dt = end_time - start_time
    client_net.shutdown()
    input_subsystem.shutdown()
    graphics_subsystem.shutdown()


if __name__ == "__main__":
    print("Do not run this package directly!")
