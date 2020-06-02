import imgui
from imgui.core import GuiStyle, Vec4

from tremor import client_main
from tremor.math.vertex_math import magnitude_vec3, magnitude_horizontal


def show_ingame_hud():
    if client_main.current_scene.current_player_ent is None:
        return
    style: GuiStyle = imgui.get_style()
    style.window_border_size = 0
    style.colors[imgui.COLOR_BUTTON] = Vec4(0.26, 0.59, 0.5, 0.4)
    style.colors[imgui.COLOR_BUTTON_ACTIVE] = Vec4(0.06, 0.53, 0.4, 1.0)
    style.colors[imgui.COLOR_BUTTON_HOVERED] = Vec4(0.26, 0.59, 0.5, 1.0)
    imgui.set_next_window_bg_alpha(0)
    imgui.set_next_window_position(0, 0)
    imgui.set_next_window_size(300, 100)
    imgui.begin("speedometer", False, imgui.WINDOW_NO_COLLAPSE | imgui.WINDOW_NO_MOVE | imgui.WINDOW_NO_RESIZE | imgui.WINDOW_NO_TITLE_BAR |
                imgui.WINDOW_ALWAYS_USE_WINDOW_PADDING)
    imgui.text("%d" % int(magnitude_horizontal(client_main.current_scene.current_player_ent.velocity)))
    imgui.text("%f" % client_main.viewangles[0])
    if client_main.current_scene.current_player_ent is not None:
        t = client_main.current_scene.current_player_ent.transform.get_translation()
        imgui.text("%.3f %.3f %.3f" % (t[0], t[1], t[2]))
    imgui.end()