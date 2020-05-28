import queue
import time
from queue import Queue
from threading import Thread

from tremor.net.client.client_socket import ClientSocket
from tremor.net.command import LoginCommand, MessageCommand, ResponseCommand


class ClientNetworkSubsystem:
    def __init__(self):
        self._thread = Thread(name="cnet", target=self._listener)
        self._inbound_queue = Queue(64)
        self._socket = ClientSocket()
        self._shutdown = False

    def initialize(self):
        self._thread.start()

    def shutdown(self):
        self._socket.destroy()
        self._shutdown = True

    def connect(self, address):
        self._socket.dest_addr = address
        self.set_connection_state(1)
        self._socket.chan.queue_command(LoginCommand(0xBEEF, b"Testing"))

    def set_connection_state(self, state):
        self._socket.connection_state = state

    def poll_commands(self):
        commands = []
        while True:
            try:
                task = self._inbound_queue.get_nowait()
                cmds = self._socket.parse_packet(*task)
                if cmds is not None:
                    commands.append(cmds)
            except queue.Empty:
                break
            except Exception as e:
                raise e
            self._inbound_queue.task_done()
        return commands

    def handle_response(self, rcmd: ResponseCommand):
        if rcmd.response_code == ResponseCommand.CONNECTION_ESTABLISHED:
            self.set_connection_state(2)
        elif rcmd.response_code == ResponseCommand.CONNECTION_TERMINATED or \
                rcmd.response_code == ResponseCommand.CONNECTION_REJECTED:
            self.set_connection_state(0)

    def handle_events(self):
        cmds = self.poll_commands()
        for cmd in cmds:
            print(cmd)
            if type(cmd) == ResponseCommand:
                self.handle_response(cmd)

    def write_outbound(self):
        if self._socket.dest_addr is not None:
            self._socket.send_datagram(self._socket.chan.generate_outbound_packet())

    def send_message(self, message: str):
        if len(message) > 64:
            print("Message truncated!")
        self._socket.chan.queue_command(MessageCommand(message), True)

    def _listener(self):
        while True:
            if self._shutdown:
                return
            try:
                b, a = self._socket.read()
                if a is None and b is None:
                    time.sleep(0.1)
                    continue
                self._inbound_queue.put((a, b), True, 0.25)
            except Exception as e:
                print(e)
