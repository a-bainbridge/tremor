import struct

import numpy as np


class EntityCreateCommand:
    def __init__(self, entity_id: int, pos: np.ndarray, scale: np.ndarray, rotation: np.ndarray, velocity: np.ndarray,
                 mins: np.ndarray, maxs: np.ndarray, classname: str, flags: int):
        self.entity_id = entity_id
        self.pos = pos
        self.scale = scale
        self.rotation = rotation
        self.velocity = velocity
        self.mins = mins
        self.maxs = maxs
        self.classname = classname.strip("\0")
        self.flags = flags
        pass

    @staticmethod
    def get_packet_length():
        return struct.calcsize(">Hfffffffffffffffffff32sB")

    @staticmethod
    def deserialize(buf):
        stuf = struct.unpack(">Hfffffffffffffffffff32sB", buf)
        return EntityCreateCommand(stuf[0],
                                   np.array(*stuf[1:4], dtype='float32'),
                                   np.array(*stuf[4:7], dtype='float32'),
                                   np.array(*stuf[7:11], dtype='float32'),
                                   np.array(*stuf[11:14], dtype='float32'),
                                   np.array(*stuf[14:17], dtype='float32'),
                                   np.array(*stuf[17:20], dtype='float32'),
                                   stuf[20],
                                   stuf[21])

    def serialize(self):
        return struct.pack(">BHfffffffffffffffffff32sB",
                           0x06,
                           *self.pos,
                           *self.scale,
                           *self.rotation,
                           *self.mins,
                           *self.maxs,
                           self.classname,
                           self.flags)


class EntityUpdateCommand:
    def __init__(self, entity_id: int, pos: np.ndarray, scale: np.ndarray, rotation: np.ndarray, velocity: np.ndarray):
        self.entity_id = entity_id
        self.pos = pos
        self.scale = scale
        self.rotation = rotation
        self.velocity = velocity

    @staticmethod
    def get_packet_length():
        return struct.calcsize(">Hfffffffffffff")

    @staticmethod
    def deserialize(buf):
        stuf = struct.unpack(">Hfffffffffffff", buf)
        return EntityUpdateCommand(stuf[0], np.array(*stuf[1:4], dtype='float32'),
                                   np.array(*stuf[4:7], dtype='float32'),
                                   np.array(*stuf[7:11], dtype='float32'),
                                   np.array(*stuf[11:14], dtype='float32'))

    def serialize(self):
        return struct.pack(">BHfffffffffffff", 0x05, self.entity_id, *self.pos, *self.scale, *self.rotation,
                           *self.velocity)


class PlayerUpdateCommand:
    def __init__(self, last_frame_time: float, actions: int, look_angles: np.ndarray,
                 forward_move: int, side_move: int, up_move: int):
        self.forward_move = forward_move
        self.side_move = side_move
        self.up_move = up_move
        self._clamp_values()
        self.last_frame_time = last_frame_time
        self.actions = actions
        self.look_angles = look_angles

    def _clamp_values(self):
        if self.forward_move > 127:
            self.forward_move = 127
        if self.forward_move < -127:
            self.forward_move = -127  # this is correct, don't change to -128!
        if self.side_move > 127:
            self.side_move = 127
        if self.side_move < -127:
            self.side_move = -127
        if self.up_move > 127:
            self.up_move = 127
        if self.up_move < -127:
            self.up_move = -127

    @staticmethod
    def get_packet_length():
        return struct.calcsize(">fIffbbb")

    @staticmethod
    def deserialize(buf):
        stuf = struct.unpack(">fIffbbb", buf)
        return PlayerUpdateCommand(stuf[0], stuf[1], np.array(stuf[2:4], dtype='float32'), stuf[4], stuf[5], stuf[6])

    def serialize(self):
        return struct.pack(">BfIffbbb", 0x04, self.last_frame_time, self.actions, *self.look_angles, self.forward_move,
                           self.side_move, self.up_move)


class ChangeMapCommand:
    def __init__(self, map: str):
        self.map = map

    def __str__(self):
        return self.map

    @staticmethod
    def get_packet_length():
        return struct.calcsize(">16s")

    @staticmethod
    def deserialize(buf):
        return ChangeMapCommand(str(struct.unpack(">16s", buf[0:32])[0], 'utf-8').strip("\0"))

    def serialize(self):
        return struct.pack(">B16s", 0x03, bytes(self.map, 'utf-8'))


class LoginCommand:
    PROTOCOL_VERSION_1 = 0xBEEF

    def __init__(self, protocol: int, name: bytes):
        self.protocol = protocol
        self.name = name

    @staticmethod
    def get_packet_length():
        return struct.calcsize(">I16s")

    @staticmethod
    def deserialize(buf):
        return LoginCommand(*struct.unpack(">I16s", buf))

    def serialize(self):
        return struct.pack(">BI16s", 0x02, self.protocol, self.name)


class ResponseCommand:
    CONNECTION_ESTABLISHED = 1
    CONNECTION_REJECTED = 2
    CONNECTION_TERMINATED = 3
    WTF = 4

    def __init__(self, response_code: int):
        self.response_code = response_code

    @staticmethod
    def get_packet_length():
        return struct.calcsize(">I")

    @staticmethod
    def deserialize(buf):
        return ResponseCommand(struct.unpack(">I", buf[0:4])[0])

    def serialize(self):
        return struct.pack(">BI", 0x01, self.response_code)


class MessageCommand:
    def __init__(self, sender_name: str, text: str):
        self.sender_name = sender_name
        self.text = text

    def __str__(self):
        return self.text

    @staticmethod
    def get_packet_length():
        return struct.calcsize(">16s64s")

    @staticmethod
    def deserialize(buf):
        stuf = struct.unpack(">16s64s", buf)
        return MessageCommand(str(stuf[0], 'utf-8').strip("\0"),
                              str(stuf[1], 'utf-8').strip("\0"))

    def serialize(self):
        return struct.pack(">B16s64s", 0x00, bytes(self.sender_name, 'utf-8'), bytes(self.text, 'utf-8'))


COMMAND_TABLE = {
    0x00: MessageCommand,  # C <-> S
    0x01: ResponseCommand,  # C <-> S
    0x02: LoginCommand,  # C -> S
    0x03: ChangeMapCommand,  # C <- S
    0x04: PlayerUpdateCommand,  # C -> S
    0x05: EntityUpdateCommand,  # C <- S
    0x06: EntityCreateCommand,  # C <- S
    # 0x07: EntityDeleteCommand,  # C <- S
    # 0x08: PlayerEntityAssignCommand  # C <- S
}


def generate_commands(c, buf):
    commands = []
    try:
        idx = 0
        for i in range(0, c):
            cmd_type = COMMAND_TABLE[struct.unpack(">B", buf[idx:idx + 1])[0]]
            idx += 1
            commands.append(cmd_type.deserialize(buf[idx:idx + cmd_type.get_packet_length()]))
            idx += cmd_type.get_packet_length()
    except Exception:
        print("bruhhh")
    return commands
