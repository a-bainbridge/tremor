import random
import time

from tremor.core.entity import Entity
from tremor.loader.scene import binloader
from tremor.math import matrix
from tremor.math.geometry import AABB
from tremor.net.command import *
from tremor.net.common import ConnectionState
from tremor.net.server import server_net
from tremor.net.server.conn import Connection

should_exit = False
current_scene = None


def handle(cmd, cl):
    cmd_type = type(cmd)
    if cmd_type is MessageCommand:
        cmd.sender_name = cl.name
        broadcast_packet(cmd)
    if cmd_type is PlayerUpdateCommand:
        handle_player_update(cmd, cl)
    if cmd_type is LoginCommand:
        handle_login_phase_2(cmd, cl)


def handle_player_update(cmd: PlayerUpdateCommand, cl: Connection):
    if cl.entity is not None:
        cl.entity.transform.set_rotation(matrix.quat_from_viewangles(cmd.look_angles))
        cl.entity.needs_update = True


def handle_login_phase_2(cmd: LoginCommand, cl: Connection):
    idx = 0
    for ent in current_scene.entities:
        if ent is not None and not ent.flags & Entity.FLAG_WORLD:
            cl.channel.queue_command(EntityCreateCommand.from_ent(idx, ent),True)
        idx += 1
    id, player_ent = current_scene.allocate_new_ent()
    player_ent.classname = "player"
    player_ent.transform.set_translation(np.array([random.random() * 32, 128, random.random() * 32]))
    player_ent.boundingbox = AABB(np.array([-16, -20, -16]), np.array([16, 20, 16]))
    player_ent.flags = Entity.FLAG_PLAYER | Entity.FLAG_GRAVITY | Entity.FLAG_BOUNCY
    broadcast_packet(EntityCreateCommand.from_ent(id, player_ent),True)
    cl.entity = player_ent
    cl.channel.queue_command(PlayerEntityAssignCommand(id), True)
    cl.state = ConnectionState.SPAWNED


def broadcast_packet(cmd, r=False):
    for cl in server_net.server_sock.client_table.values():
        cl.channel.queue_command(cmd, r)


def main():
    global current_scene
    print("Server starting...")
    server_net.init()
    current_scene = binloader.load_scene_file("out", "data/scenes/out.tmb", False)
    dt = 1 / 20
    while not should_exit:
        start_time = time.time()
        server_net.poll_commands()
        current_scene.move_entities(dt)
        idx = 0
        for ent in current_scene.entities:
            if ent is not None and ent.needs_update:
                broadcast_packet(EntityUpdateCommand.from_ent(idx, ent))
            idx += 1
        server_net.process_outgoing()
        end_time = time.time() - start_time
        if end_time > 1 / 20:
            dt = end_time
        else:
            time.sleep((1 / 20) - end_time)
            dt = time.time() - start_time
