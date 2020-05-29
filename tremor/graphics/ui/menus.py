import imgui
from imgui.core import GuiStyle, Vec4

from tremor.graphics import graphics_subsystem
from tremor.net.client import client_net

text = "Player"
ip_text = "96.19.3.230"

def show_main_menu():
    global text, ip_text
    style: GuiStyle = imgui.get_style()
    style.window_border_size = 0
    style.colors[imgui.COLOR_BUTTON] = Vec4(0.26, 0.59, 0.5, 0.4)
    style.colors[imgui.COLOR_BUTTON_ACTIVE] = Vec4(0.06, 0.53, 0.4, 1.0)
    style.colors[imgui.COLOR_BUTTON_HOVERED] = Vec4(0.26, 0.59, 0.5, 1.0)
    imgui.set_next_window_bg_alpha(0)
    imgui.set_next_window_position(300, 220)
    imgui.set_next_window_size(180, 200)
    imgui.begin("tremor0", False, imgui.WINDOW_NO_COLLAPSE | imgui.WINDOW_NO_MOVE | imgui.WINDOW_NO_RESIZE | imgui.WINDOW_NO_TITLE_BAR |
                imgui.WINDOW_ALWAYS_USE_WINDOW_PADDING)
    _, username = imgui.input_text("Name", text, 16)
    _, ip = imgui.input_text("Host", ip_text, 32)
    ip_text = ip
    text = username
    imgui.end()
    imgui.set_next_window_bg_alpha(0)
    imgui.set_next_window_size(100, 100)
    imgui.set_next_window_position(200, 200)
    imgui.begin("tremor1", False, imgui.WINDOW_NO_COLLAPSE | imgui.WINDOW_NO_MOVE | imgui.WINDOW_NO_RESIZE | imgui.WINDOW_NO_TITLE_BAR |
                imgui.WINDOW_ALWAYS_USE_WINDOW_PADDING)
    imgui.text_colored("Tremor", 0.9, 0.6, 1.0)
    play_clicked = imgui.button("Play", 82, 25)
    exit_clicked = imgui.button("Exit", 82, 25)
    if exit_clicked:
        graphics_subsystem.request_close()
    if play_clicked:
        print(username)
        client_net.connect_to_server((ip, 27070), username)
    imgui.end()
