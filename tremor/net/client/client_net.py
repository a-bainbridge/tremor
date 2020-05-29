import queue
import time
from queue import Queue
from threading import Thread

from tremor.net.client.client_socket import ClientSocket
from tremor.net.command import LoginCommand, MessageCommand, ResponseCommand


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


def connect(address):
    _socket.dest_addr = address
    set_connection_state(1)
    _socket.chan.queue_command(LoginCommand(0xBEEF, b"Testing"))


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


def handle_response(rcmd: ResponseCommand):
    if rcmd.response_code == ResponseCommand.CONNECTION_ESTABLISHED:
        set_connection_state(2)
    elif rcmd.response_code == ResponseCommand.CONNECTION_TERMINATED or \
            rcmd.response_code == ResponseCommand.CONNECTION_REJECTED:
        set_connection_state(0)


def handle_events():
    cmds = poll_commands()
    for cmd in cmds:
        print(cmd)
        if type(cmd) == ResponseCommand:
            handle_response(cmd)


def write_outbound():
    if _socket.dest_addr is not None:
        _socket.send_datagram(_socket.chan.generate_outbound_packet())


def send_message(message: str):
    if len(message) > 64:
        print("Message truncated!")
    _socket.chan.queue_command(MessageCommand(message), True)
