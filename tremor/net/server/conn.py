from tremor.net.common import ConnectionState


class Connection:
    def __init__(self, ip, port, id, channel, name):
        self.ip = ip
        self.port = port
        self.id = id
        self.state = ConnectionState.DISCONNECTED
        self.channel = channel
        self.entity = None
        self.entity_id = None
        self.connection_time = 0
        self.name = name