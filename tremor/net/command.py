import struct


class LoginCommand:
    PROTOCOL_VERSION_1 = 0xBEEF

    def __init__(self, protocol: int, name: bytes):
        self.protocol = protocol
        self.name = name

    @staticmethod
    def get_packet_length():
        return 20

    @staticmethod
    def deserialize(buf):
        return LoginCommand(*struct.unpack(">I16s", buf[0:20]))

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
        return 4

    @staticmethod
    def deserialize(buf):
        return ResponseCommand(struct.unpack(">I", buf[0:4])[0])

    def serialize(self):
        return struct.pack(">BI", 0x01, self.response_code)


class MessageCommand:
    def __init__(self, text: str):
        self.text = text

    def __str__(self):
        return self.text

    @staticmethod
    def get_packet_length():
        return 32

    @staticmethod
    def deserialize(buf):
        return MessageCommand(str(struct.unpack(">32s", buf[0:32])[0], 'utf-8').strip("\0"))

    def serialize(self):
        return struct.pack(">B32s", 0x00, bytes(self.text, 'utf-8'))


COMMAND_TABLE = {
    0x00: MessageCommand,
    0x01: ResponseCommand,
    0x02: LoginCommand
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
