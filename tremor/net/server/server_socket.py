import socket
from typing import Tuple

from tremor.net.channel import Channel
from tremor.net.command import generate_commands, LoginCommand, ResponseCommand


class ServerSocket:
    def __init__(self, port):
        self._sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        self._sock.bind(("", port))
        self.port = port
        self.client_table = {}

    def send_to(self, dgram, addr):
        if dgram is None:
            return
        self._sock.sendto(dgram, addr)

    def recv(self):
        b, a = self._sock.recvfrom(8192)
        return (bytearray(b), a)

    def register_connection(self, addr_id: Tuple[str, int], udp_port: int):
        chan = Channel()
        self.client_table[addr_id] = [chan, udp_port, addr_id[0]]
        return chan

    def send_to_client(self, dgram, addr_id: Tuple[str, int]):
        if addr_id in self.client_table:
            self.send_to(dgram, (addr_id[0], self.client_table[addr_id][1]))
        else:
            raise Exception("No client")

    def parse_packet(self, addr, data):
        if len(data) < 11:
            return None
        id = Channel.get_identifier(data)
        tup = (addr[0], id)
        if tup in self.client_table.keys():
            self.client_table[tup][1] = addr[1]
            return (self.client_table[tup][0].receive_packet(data), tup)
        else:
            # be careful here
            try:
                cmd_count = Channel.get_cmd_count(data)
                cmds = generate_commands(cmd_count, data[11:len(data)])
                for cmd in cmds:
                    if type(cmd) == LoginCommand:
                        self.register_connection(tup, addr[1]).queue_command(
                            ResponseCommand(ResponseCommand.CONNECTION_ESTABLISHED))
                        return ([cmd], tup)
            except:
                return None
        return None

    def send_outgoing_commands(self):
        remove = []
        for k, cl in self.client_table.items():
            try:
                if cl[0].should_disconnect():
                    dgram = cl[0].generate_disconnect()
                    remove.append(k)
                else:
                    dgram = cl[0].generate_outbound_packet()
                self.send_to(dgram, (cl[2], cl[1]))
            except Exception as e:
                remove.append(k)
                print(e)
        for c in remove:
            self.client_table.pop(c)
