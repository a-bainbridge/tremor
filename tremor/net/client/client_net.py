import queue
import time
from queue import Queue
from threading import Thread

from tremor import client_main
from tremor.net.client.client_socket import ClientSocket
from tremor.net.command import *
from tremor.net.common import ConnectionState


def _listener():
    while True:
        if _shutdown:
            return
        try:
            b, a = _socket.read()
            if a is None and b is None:
                time.sleep(0.1)
                continue
            _inbound_queue.put((a, b), True, 0.25)
        except Exception as e:
            print(e)


_thread = Thread(name="cnet", target=_listener)
_inbound_queue = Queue(64)
_socket = ClientSocket()
_shutdown = False


def init():
    _thread.start()


def shutdown():
    global _shutdown
    _socket.destroy()
    _shutdown = True


def connect_to_server(address, username):
    _socket.dest_addr = address
    set_connection_state(ConnectionState.CONNECTING)
    _socket.chan.queue_command(LoginCommand(0xBEEF, bytes(username, 'utf-8')))
    _socket._connect_time = time.time()


def set_connection_state(state):
    _socket.connection_state = state


def poll_commands():
    commands = []
    while True:
        try:
            task = _inbound_queue.get_nowait()
            cmds = _socket.parse_packet(*task)
            if cmds is not None:
                commands.append(cmds)
        except queue.Empty:
            break
        except Exception as e:
            raise e
        _inbound_queue.task_done()
    return commands


def handle_events():
    cmds = poll_commands()
    for cmd_group in cmds:
        for cmd in cmd_group:
            client_main.handle(cmd)


def write_outbound():
    if _socket.dest_addr is not None:
        _socket.send_datagram(_socket.chan.generate_outbound_packet())


def send_message(message: str):
    if len(message) > 64:
        print("Message truncated!")
    _socket.chan.queue_command(MessageCommand("", message), False)


def queue_update_cmd(viewangles):
    _socket.chan.queue_command(PlayerUpdateCommand(0, 0, viewangles, 0, 0, 0))