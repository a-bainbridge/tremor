import random
import struct

from tremor.net.command import generate_commands, ResponseCommand


class Channel:
    def __init__(self, maximum_cmd_buf=256):
        self._id = random.randint(0x0, 0xFFFF)
        self._sequence = 0
        self._last_received_sequence = 0
        self._reliable_buffer = []
        self._reliable_waiting = []
        self._command_buffer = []
        self.maximum_cmd_buf = maximum_cmd_buf

    def queue_command(self, cmd, reliable=False):
        if reliable:
            self._reliable_waiting.append(cmd)
        else:
            self._command_buffer.append(cmd)

    def should_disconnect(self):
        return len(self._reliable_waiting) + len(self._command_buffer) > self.maximum_cmd_buf

    @staticmethod
    def get_identifier(dgram):
        return struct.unpack(">H", dgram[8:10])[0]

    @staticmethod
    def get_cmd_count(dgram):
        return struct.unpack(">B", dgram[10:11])[0]

    def reset(self):
        self._command_buffer = []
        self._reliable_buffer = []
        self._reliable_waiting = []
        self._sequence = 0
        self._last_received_sequence = 0

    def receive_packet(self, dgram):
        seqnum, ackd, id, cmdcount = struct.unpack(">IIHB", dgram[0:11])
        self._last_received_sequence = seqnum
        if ackd & (1 << 31):
            self._reliable_buffer = []
        return generate_commands(cmdcount, dgram[11:len(dgram)])

    def _shuffle_bufs(self):
        if len(self._reliable_buffer) == 0:
            self._reliable_buffer = self._reliable_waiting
            self._reliable_waiting = []

    def _write_header(self, reliable, cnt):
        if self._sequence > 0x7FFFFFFF:
            self._sequence = 0
        out = struct.pack(">IIHB", self._sequence | (1 << 31 if reliable else 0), self._last_received_sequence,
                          self._id, cnt)
        self._sequence += 1
        return out

    def generate_outbound_packet(self):
        self._shuffle_bufs()
        if len(self._reliable_buffer) + len(self._command_buffer) == 0:
            return None
        remaining = 8192 - 11
        test_rm = remaining
        commands = 0
        for reliable in self._reliable_buffer:
            test_rm -= 1 + reliable.get_packet_length()
        if test_rm < 0:
            raise Exception("Uh oh, guess it's time to implement reliable packet fragmentation")
        buffer = bytearray(8192)
        pos = 11
        for reliable in self._reliable_buffer:
            buffer[pos:reliable.get_packet_length() + pos + 1] = reliable.serialize()
            pos += reliable.get_packet_length() + 1
            commands += 1
        written_unreliable = []
        for unreliable in self._command_buffer:
            if pos + unreliable.get_packet_length() > 8192:
                break
            written_unreliable.append(unreliable)
            buffer[pos:unreliable.get_packet_length() + pos + 1] = unreliable.serialize()
            pos += unreliable.get_packet_length() + 1
            commands += 1
        for unreliable in written_unreliable:
            self._command_buffer.remove(unreliable)
        buffer[0:11] = self._write_header(len(self._reliable_buffer) > 0, commands)
        print("sent")
        return buffer

    def generate_disconnect(self):
        self._command_buffer = []
        self._reliable_buffer = []
        self._reliable_waiting = []
        self.queue_command(ResponseCommand(ResponseCommand.CONNECTION_TERMINATED))
        return self.generate_outbound_packet()
