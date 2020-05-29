from enum import Enum


class ConnectionState(Enum):
    DISCONNECTED = 0,
    CONNECTING = 1,
    CONNECTED = 2, # connected, but not in the world yet
    SPAWNED = 3,