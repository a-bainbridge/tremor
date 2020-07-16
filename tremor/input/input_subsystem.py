import glfw

from tremor import client_main
from tremor.core import console
from tremor.graphics import graphics_subsystem
from tremor.input import key_input
import OpenGL.GL as gl

inputs = {'mouse': [0, 0]}

def init():
    clamp = lambda value, min_value, max_value: min(max(value, min_value), max_value)
    imgui_renderer = graphics_subsystem.imgui_renderer
    window = graphics_subsystem.window

    def mouseclick_callback(window, button, action, modifiers):
        print('fps: %s'%client_main.debug_fps)

        # to test gpu -> cpu texture thing
        # if len(list(graphics_subsystem.TEXTURE_TABLE.values()))>0:
        #     list(graphics_subsystem.TEXTURE_TABLE.values())[0].get_data(gl.GL_TEXTURE_2D)

    def scroll_callback(window, x, y):
        imgui_renderer.scroll_callback(window, x, y)

    def resize_callback(window, w, h):
        imgui_renderer.resize_callback(window, w, h)

    def char_callback(window, char):
        imgui_renderer.char_callback(window, char)

    def keyboard_callback(window, key, scancode, action, mods):
        global wireframe
        imgui_renderer.keyboard_callback(window, key, scancode, action, mods)
        if key == glfw.KEY_ESCAPE:
            glfw.set_window_should_close(window, glfw.TRUE)
            return
        if key in key_input.bind_map.keys():
            con_cmd = key_input.bind_map[key]
            if str.startswith(con_cmd, "+"):
                if action == glfw.PRESS:
                    # todo input queue
                    console.handle_input(con_cmd)
                elif action == glfw.RELEASE:
                    # todo input queue
                    console.handle_input(str.replace(con_cmd, "+", "-", 1))
            elif action == glfw.PRESS:
                # todo input queue
                console.handle_input(con_cmd)
            return
        if console.SHOW_CONSOLE:
            if key == glfw.KEY_ENTER:
                console.ENTER_PRESSED = True
            return
        # todo input queue
        # inputs['key'] = key

    def mouse_callback(window, x, y):
        inputs['mouse'] = [x, y]
        y = -y * 0.05
        x = -x * 0.05
        if y > 90:
            y = 90
        if y < -90:
            y = -90
        if console.SHOW_CONSOLE:
            return
        client_main.viewangles[0] = x % 360
        client_main.viewangles[1] = y
        pass

    glfw.set_mouse_button_callback(window, mouseclick_callback)
    glfw.set_cursor_pos_callback(window, mouse_callback)
    glfw.set_key_callback(window, keyboard_callback)
    glfw.set_scroll_callback(window, scroll_callback)
    glfw.set_window_size_callback(window, resize_callback)
    glfw.set_char_callback(window, char_callback)

def poll_events():
    glfw.poll_events()
    graphics_subsystem.imgui_renderer.process_inputs()

def shutdown():
    pass
