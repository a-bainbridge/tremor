import socket
import time
from typing import Tuple

from tremor.net.channel import Channel
from tremor.net.command import generate_commands, LoginCommand, ResponseCommand, ChangeMapCommand
from tremor.net.common import ConnectionState
from tremor.net.server import conn


class ServerSocket:
    def __init__(self, port):
        self._sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        self._sock.bind(("0.0.0.0", port))
        self.port = port
        self.client_table = {}

    def send_to(self, dgram, addr):
        if dgram is None:
            return
        self._sock.sendto(dgram, addr)

    def recv(self):
        b, a = self._sock.recvfrom(8192)
        return (bytearray(b), a)

    def register_connection(self, addr_id: Tuple[str, int], udp_port: int, name: str):
        chan = Channel()
        connection = conn.Connection(addr_id[0], udp_port, addr_id[1], chan, name)
        connection.connection_time = time.time()
        connection.connection_state = ConnectionState.CONNECTED
        self.client_table[addr_id] = connection
        return connection

    def send_to_client(self, dgram, addr_id: Tuple[str, int]):
        if addr_id in self.client_table:
            self.send_to(dgram, (addr_id[0], self.client_table[addr_id].port))
        else:
            raise Exception("No client")

    def parse_packet(self, addr, data):
        if len(data) < 11:
            return None
        id = Channel.get_identifier(data)
        tup = (addr[0], id)
        if tup in self.client_table.keys():
            self.client_table[tup].port = addr[1]
            return self.client_table[tup], self.client_table[tup].channel.receive_packet(data)
        else:
            # be careful here
            try:
                cmd_count = Channel.get_cmd_count(data)
                cmds = generate_commands(cmd_count, data[11:len(data)])
                for cmd in cmds:
                    if type(cmd) == LoginCommand:
                        con = self.register_connection(tup, addr[1], str(cmd.name, 'utf-8'))
                        con.channel.queue_command(ResponseCommand(ResponseCommand.CONNECTION_ESTABLISHED), True)
                        con.channel.queue_command(ChangeMapCommand("out"), True)
                        return con, self.client_table[tup].channel.receive_packet(data)
            except:
                return None
        return None

    def send_outgoing_commands(self):
        remove = []
        for k, cl in self.client_table.items():
            try:
                if cl.channel.should_disconnect():
                    print("dc'ing")
                    dgram = cl.channel.generate_disconnect()
                    remove.append(k)
                else:
                    dgram = cl.channel.generate_outbound_packet()
                self.send_to(dgram, (cl.ip, cl.port))
            except Exception as e:
                remove.append(k)
                print(e)
        for c in remove:
            self.client_table.pop(c)
