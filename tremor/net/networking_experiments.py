import queue
import threading
import time

# server: packets come in, queued for processing at beginning of next server tick
# send responses on separate thread?
# client: packets come in, queued for processing at beginning of next client tick
# response(s) sent at end of tick
from tremor.net.server.server_socket import ServerSocket

inbound_server_queue = queue.Queue(128)


def server_net_loop(sock):
    def loop():
        while True:
            try:
                b, a = sock.recv()
                inbound_server_queue.put((a, b), True, 0.25)
            except Exception:
                print("wtf")

    return loop


if __name__ == "__main__":
    server_sock = ServerSocket(27070)
    server_thread = threading.Thread(name="snet", target=server_net_loop(server_sock))
    server_thread.start()
    while True:
        time.sleep(1 / 20)
        commands = []
        while True:
            try:
                task = inbound_server_queue.get_nowait()
                cmds = server_sock.parse_packet(*task)
                if cmds is not None:
                    commands.append(cmds)
            except queue.Empty:
                break
            except Exception as e:
                raise e
            inbound_server_queue.task_done()
        for cmd_list, sender in commands:
            for cmd in cmd_list:
                print("Received a %s command from %s" % (str(cmd), sender))
        server_sock.send_outgoing_commands()
