# client socket sends to a dest, receives from that dest
import socket

from tremor.net.channel import Channel


class ClientSocket:
    def __init__(self, dest_addr=None):
        self.dest_addr = dest_addr
        self.connection_state = 0
        self._socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        self.chan = Channel()
        self._incoming = False

    def send_datagram(self, dgram):
        if dgram is not None:
            self._incoming = True
            self._socket.sendto(dgram, self.dest_addr)

    def read(self):
        if self._incoming and self.dest_addr is not None:
            b, a = self._socket.recvfrom(8192)
            return (bytearray(b), a)
        else:
            return None, None

    def destroy(self):
        self._socket.close()
        self.chan = None
        pass

    def reset(self):
        self.connection_state = 0
        self.dest_addr = None
        self.chan.reset()

    def parse_packet(self, addr, data):
        if len(data) < 11:
            return None
        try:
            return self.chan.receive_packet(data)
        except:
            return None
