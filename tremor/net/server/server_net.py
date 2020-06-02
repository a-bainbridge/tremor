import queue
import threading

from tremor import server_main
from tremor.net.command import EntityDeleteCommand, MessageCommand
from tremor.net.server.server_socket import ServerSocket

inbound_server_queue = queue.Queue(128)

server_sock = ServerSocket(27070)

event_queue = queue.Queue(128)


def server_net_loop(sock):
    def loop():
        while True:
            try:
                b, a = sock.recv()
                inbound_server_queue.put((a, b), True, 0.25)
            except Exception:
                pass

    return loop


server_thread = threading.Thread(name="snet", target=server_net_loop(server_sock))


def init():
    server_thread.start()


def poll_commands():
    commands = []
    while True:
        try:
            task = inbound_server_queue.get_nowait()
            cmds = server_sock.parse_packet(*task)
            if cmds is not None:
                for cmd in cmds[1]:
                    server_main.handle(cmd, cmds[0])
        except queue.Empty:
            break
        except Exception as e:
            raise e
        inbound_server_queue.task_done()
    return commands


def handle_errors():
    for k in server_sock.remove_list:
        if k in server_sock.client_table:
            connection = server_sock.client_table[k]
            server_main.broadcast_packet(MessageCommand("SERVER", "%s has disconnected." % connection.name))
            print("%s has disconnected." % connection.name)
            server_main.broadcast_packet(EntityDeleteCommand(connection.entity_id))
            server_main.current_scene.entities[connection.entity_id] = None
            server_sock.pending_remove.append(k)
    server_sock.remove_list.clear()


def check_connections():
    for k, cl in server_sock.client_table.items():
        if cl.channel.should_disconnect():
            cl.channel.generate_disconnect()
            server_sock.remove_list.append(k)


def process_outgoing():
    server_sock.send_outgoing_commands()
