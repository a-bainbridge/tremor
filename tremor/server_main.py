import time

from tremor.loader.scene import binloader
from tremor.net.command import PlayerUpdateCommand, MessageCommand
from tremor.net.server import server_net

should_exit = False
current_scene = None

def handle(cmd, cl):
    cmd_type = type(cmd)
    if cmd_type is MessageCommand:
        cmd.sender_name = cl.name
        broadcast_fwded_packet(cmd)
    if cmd_type is PlayerUpdateCommand:
        pass

def broadcast_fwded_packet(cmd):
    for cl in server_net.server_sock.client_table.values():
        cl.channel.queue_command(cmd)

def main():
    global current_scene
    print("Server starting...")
    server_net.init()
    current_scene = binloader.load_scene_file("out", "data/scenes/out.tmb", False)
    dt = 1/20
    while not should_exit:
        start_time = time.time()
        server_net.poll_commands()
        server_net.process_outgoing()
        end_time = time.time() - start_time
        if end_time > 1/20:
            dt = end_time
        else:
            time.sleep((1/20)-end_time)
            dt = time.time() - start_time