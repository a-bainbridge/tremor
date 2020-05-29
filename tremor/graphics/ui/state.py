from enum import Enum


class UIState(Enum):
    MENU = 0,
    IN_GAME_HUD = 1,
    IN_GAME_MENU = 2,

    MAIN_MENU = 3,
    PAUSE_MENU = 4