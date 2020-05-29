import time

from tremor.core import console
from tremor.core.entity import Entity
from tremor.graphics import graphics_subsystem
from tremor.graphics.ui.state import UIState
from tremor.input import input_subsystem
from tremor.loader.scene import binloader
from tremor.math import matrix
from tremor.net.client import client_net
from tremor.net.command import *
from tremor.net.common import ConnectionState

current_scene = None
viewangles = np.array([0, 0], dtype='float32')

def handle(cmd):
    cmd_type = type(cmd)
    print(cmd_type)
    if cmd_type is ResponseCommand:
        handle_response(cmd)
    if cmd_type is ChangeMapCommand:
        handle_map(cmd)
    if cmd_type is MessageCommand:
        console.conprint(cmd.sender_name+": "+cmd.text)


def handle_response(cmd):
    global current_scene
    if cmd.response_code == ResponseCommand.CONNECTION_ESTABLISHED:
        client_net.set_connection_state(ConnectionState.CONNECTED)
    elif cmd.response_code == ResponseCommand.CONNECTION_TERMINATED or \
            cmd.response_code == ResponseCommand.CONNECTION_REJECTED:
        client_net.set_connection_state(ConnectionState.DISCONNECTED)
        if current_scene is not None:
            unload_map()
            current_scene = None
            graphics_subsystem._ui_state = UIState.MAIN_MENU


def handle_map(cmd):
    map_name = cmd.map
    if current_scene is None:
        load_map(map_name)
        graphics_subsystem._ui_state = UIState.IN_GAME_HUD
        return
    if current_scene.name == map_name:
        return
    unload_map()
    load_map(map_name)


def unload_map():
    current_scene.destroy()


def load_map(map_name):
    global current_scene
    current_scene = binloader.load_scene_file(map_name, "data/scenes/" + map_name + ".tmb", True)


def main():
    graphics_subsystem.init()
    graphics_subsystem._ui_state = UIState.MAIN_MENU
    input_subsystem.init()
    console.load_startup("startup.rc")
    client_net.init()
    dt = 1 / 60.0
    while not graphics_subsystem.window_close_requested():
        start_time = time.time()
        input_subsystem.poll_events()
        client_net.handle_events()
        # todo console buffer here
        if current_scene is not None:
            if current_scene.current_player_ent is not None:
                current_scene.current_player_ent.transform.set_rotation(matrix.quat_from_viewangles(viewangles))
            else:
                current_scene.current_player_ent = Entity()
            current_scene.move_entities(dt)  # prediction
        if client_net._socket.connection_state == ConnectionState.CONNECTED:
            client_net.queue_update_cmd(viewangles)
        client_net.write_outbound()
        graphics_subsystem.draw_scene(current_scene)
        graphics_subsystem.draw_ui()
        graphics_subsystem.end_frame()
        end_time = time.time()
        dt = end_time - start_time
    client_net.shutdown()
    input_subsystem.shutdown()
    graphics_subsystem.shutdown()
