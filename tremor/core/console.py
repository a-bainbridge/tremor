from enum import Enum
from typing import Any

# todo fixme
import glfw

from tremor.input import key_input

text_buffer = []
SHOW_CONSOLE = False
cvars = {}
cmds = {}


def get_cvar_value(cvar):
    return cvars[cvar]["value"]


def conprint(message: Any, color: (float, float, float) = None):
    text_buffer.append((str(message), color))
    print(message)


def clear():
    global text_buffer
    text_buffer = []


# noinspection PyPep8Naming
def CVar(*args, **kwargs):
    def check_cvar(f):
        cvars[args[0]] = {
            "set_func": f,
            "value": kwargs["default_value"],  # todo load from archive
            "default_value": kwargs["default_value"],
            "flags": kwargs["flags"]
        }

    return check_cvar


def CCmd(*args, **kwargs):
    def check_cmd(f):
        cmds[args[0]] = f

    return check_cmd


@CVar("test_cvar", flags=0, default_value="0")
def _con_show_cvar_set(a):
    return a


def set_cvar(cvar, value):
    if cvar not in cvars.keys():
        return
    cv = cvars[cvar]
    if cv["flags"] & CVarFlag.READONLY:
        print('readonly')
        return
    cv["value"] = cv["set_func"](value)


@CCmd("set")
def _set_cmd(*args):
    if len(args) != 2:
        conprint("Usage: /set <cvar> <value>")
        return
    set_cvar(args[0], args[1])


@CCmd("cvarlist")
def _cvarlist(*args):
    for name, cvar in cvars.items():
        conprint(name + " " + str(cvar["value"]))


@CCmd("cmdlist")
def _cmdlist(*args):
    for name in cmds.keys():
        conprint(name)


@CCmd("bind")
def _bind(*args):
    if not len(args) == 2:
        conprint("Usage: /bind <key> <command>")
        return
    key_name = str.upper(args[0])
    # todo fixme
    if hasattr(glfw, "KEY_" + key_name):
        key_input.bind_map[getattr(glfw, "KEY_" + key_name)] = args[1]
    else:
        conprint("Invalid key " + "KEY_" + key_name)


@CCmd("toggleconsole")
def _togglecon(*args):
    global SHOW_CONSOLE
    SHOW_CONSOLE = not SHOW_CONSOLE


class CVarFlag(Enum):
    READONLY = 1
    CHEAT = 2,
    ARCHIVE = 4,
    DEVELOPER = 8

    def __or__(self, other):
        return self.value | other

    def __ror__(self, other):
        return self.__or__(other)

    def __and__(self, other):
        return self.value & other

    def __rand__(self, other):
        return self.__and__(other)


def handle_input(console_input):
    split = str.split(console_input, " ")
    if split[0] not in cmds.keys():
        conprint("Unknown command")
        return
    if len(split) == 1:
        cmds[split[0]]()
    else:
        cmds[split[0]](*split[1:])


def load_startup(filename):
    with open(filename, "r", encoding="utf-8") as file:
        for i, line in enumerate(file):
            handle_input(str.strip(line))
