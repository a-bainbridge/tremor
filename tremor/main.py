from random import random
import time

import OpenGL

from tremor.core.scene import Scene
from tremor.loader.scene import binloader
from tremor.math.geometry import AABB
from tremor.math.vertex_math import norm_vec3
from tremor.core.entity import Entity

OpenGL.USE_ACCELERATE = False

import glfw
from tremor.util import glutil, configuration
from tremor.core import game_clock, console, key_input

from tremor.graphics.shaders import *
from tremor.graphics.uniforms import *
import sys
import glm
from tremor.graphics import screen_utils, scene_renderer
from tremor.math import matrix, collision_testing

import imgui

from imgui.integrations.glfw import GlfwRenderer

vbo, nvbo, cvbo = None, None, None
window = None

framecount = 0
MAX_FPS: int = None
fps_clock = game_clock.FPSController()

inputs = {'mouse': [0, 0]}  # this is probably bad

current_scene: Scene = None

imgui_renderer: GlfwRenderer = None


def create_window(size, pos, title, hints, screen_size, monitor=None, share=None, ):
    if pos == "centered":
        pos = (screen_size[0] / 2, screen_size[1] / 2)
    glfw.default_window_hints()
    for hint, value in hints.items():
        if hint in [glfw.COCOA_FRAME_NAME, glfw.X11_CLASS_NAME, glfw.X11_INSTANCE_NAME]:
            glfw.window_hint_string(hint, value)
        else:
            glfw.window_hint(hint, value)
    win = glfw.create_window(size[0], size[1], title, monitor, share)
    glfw.set_window_pos(win, int(pos[0]), int(pos[1]))
    glfw.set_input_mode(win, glfw.CURSOR, glfw.CURSOR_DISABLED)
    glfw.make_context_current(win)
    return win


def create_uniforms():
    # Matricies
    add_uniform_to_all('modelViewMatrix', 'mat4')
    add_uniform_to_all('projectionMatrix', 'mat4')
    add_uniform_to_all('viewMatrix', 'mat4')

    # env
    add_uniform_to_all('time', 'float')

    # other
    add_uniform_to_all('light_pos', 'vec3') # todo: baD



def render():
    scene_renderer.render(current_scene)
    fps_clock.capFPS(screen_utils.MAX_FPS)


def reshape(w, h):
    glViewport(0, 0, w, h)
    screen_utils.WIDTH = w
    screen_utils.HEIGHT = h

wireframe = False
move_keys = [0, 0]
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
                console.handle_input(con_cmd)
            elif action == glfw.RELEASE:
                console.handle_input(str.replace(con_cmd, "+", "-", 1))
        elif action == glfw.PRESS:
            console.handle_input(con_cmd)
    if key == glfw.KEY_UP:
        move_keys[0] = action == glfw.PRESS or action == glfw.REPEAT
    if action == glfw.RELEASE:
        if key == glfw.KEY_SPACE:
            move_keys[1] = 1000
        return
    if console.SHOW_CONSOLE:
        if key == glfw.KEY_ENTER:
            console.ENTER_PRESSED = True
        return
    if key == glfw.KEY_F:
        if action == glfw.REPEAT:
            return
        glPolygonMode(GL_FRONT_AND_BACK, GL_FILL if wireframe else GL_LINE)
        wireframe = not wireframe
    inputs['key'] = key



def mouse_callback(window, x, y):
    imgui_renderer.mouse_callback(window, x, y)
    inputs['mouse'] = [x, y]
    current_scene.active_camera.transform.set_rotation(matrix.quaternion_from_angles([0, np.pi * np.mod(x/10.0, 360)/180, 0]))


def mouseclick_callback(window, button, action, modifiers):
    # print(fps_clock.average_fps)
    pass


def error_callback(error, description):
    print(str(error) + " : " + description.decode(), file=sys.stderr)


def scroll_callback(window, x, y):
    imgui_renderer.scroll_callback(window, x, y)


def resize_callback(window, w, h):
    imgui_renderer.resize_callback(window, w, h)


def char_callback(window, char):
    imgui_renderer.char_callback(window, char)

def random_unit_sphere_vec () -> np.ndarray:
    return norm_vec3([random()*2-1, random()*2-1, random()*2-1])

def main():
    global window, vbo, nvbo, cvbo
    global current_scene
    global imgui_renderer

    glfw.set_error_callback(error_callback)

    imgui.create_context()
    if not glfw.init():
        print("GLFW Initialization fail!")
        return

    graphics_settings = configuration.get_graphics_settings()
    loader_settings = configuration.get_loader_settings()

    if graphics_settings is None:
        print("bla")
        return

    screen_utils.WIDTH = graphics_settings.getint("width")
    screen_utils.HEIGHT = graphics_settings.getint("height")
    screen_utils.MAX_FPS = graphics_settings.getint("max_fps")

    screen = None
    if graphics_settings.getboolean("full_screen"):
        screen = glfw.get_primary_monitor()

    hints = {
        glfw.DECORATED: glfw.TRUE,
        glfw.RESIZABLE: glfw.FALSE,
        glfw.CONTEXT_VERSION_MAJOR: 4,
        glfw.CONTEXT_VERSION_MINOR: 5,
        glfw.OPENGL_DEBUG_CONTEXT: glfw.TRUE,
        glfw.OPENGL_PROFILE: glfw.OPENGL_CORE_PROFILE,
        glfw.SAMPLES: 4,
    }

    console.load_startup("startup.rc")

    window = create_window(size=(screen_utils.WIDTH, screen_utils.HEIGHT), pos="centered", title="Quake-like",
                           monitor=screen, hints=hints,
                           screen_size=glfw.get_monitor_physical_size(glfw.get_primary_monitor()))
    # glfw.set_input_mode(window, glfw.CURSOR, glfw.CURSOR_DISABLED)
    imgui_renderer = GlfwRenderer(window, attach_callbacks=False)
    glutil.log_capabilities()
    glEnable(GL_CULL_FACE)
    glCullFace(GL_BACK)
    glEnable(GL_DEPTH_TEST)
    glDepthMask(GL_TRUE)
    glDepthFunc(GL_LEQUAL)
    glDepthRange(0.0, 1.0)
    glEnable(GL_MULTISAMPLE)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    # create_all_programs() # todo: move away from this as testing progresses
    create_branched_programs()

    # create the uniforms
    create_uniforms()
    # initialize all the uniforms for all the prpograms
    init_all_uniforms()

    # texture_loading.load_all_textures('data/textures', {
    #     # https://open.gl/textures
    #     'noise_512': {
    #         'clamp_mode': GL_REPEAT
    #     }
    # })

    current_scene = binloader.load_scene_file("data/scenes/out.tmb")
    cam = Entity()
    cam.transform.set_translation(np.array([0, 30, 0]))
    cam.boundingbox = AABB.cube(2)
    cam.gravity = True
    cam.classname = "cam"
    current_scene.active_camera = cam
    current_scene.entities.append(cam)
    fps_clock.start()

    glfw.set_mouse_button_callback(window, mouseclick_callback)
    glfw.set_cursor_pos_callback(window, mouse_callback)
    glfw.set_key_callback(window, keyboard_callback)
    glfw.set_scroll_callback(window, scroll_callback)
    glfw.set_window_size_callback(window, resize_callback)
    glfw.set_char_callback(window, char_callback)
    dt = 1/60.0
    while not glfw.window_should_close(window):
        # todo call an update method as well
        glfw.poll_events()
        imgui_renderer.process_inputs()
        accel_vec = matrix.rot_from_quat(cam.transform.get_rotation())
        accel_vec = np.array([np.sin(accel_vec[1]), 0, np.cos(accel_vec[1])])
        accel_vec = accel_vec * dt * move_keys[0]
        accel_vec[1] = move_keys[1] * dt
        move_keys[1] = 0
        cam.velocity += accel_vec
        if accel_vec[0] == 0 and accel_vec[2] == 0:
            cam.velocity[0] -= cam.velocity[0] * 0.99 * dt
            cam.velocity[2] -= cam.velocity[2] * 0.99 * dt
        current_scene.tick(dt)
        render()
        imgui.new_frame()
        if console.SHOW_CONSOLE:
            imgui.set_next_window_bg_alpha(0.35)
            imgui.set_next_window_position(0, 0)
            imgui.set_next_window_size(screen_utils.WIDTH, 110)
            imgui.begin("ConsoleWindow", False,
                        imgui.WINDOW_NO_MOVE | imgui.WINDOW_NO_RESIZE | imgui.WINDOW_NO_COLLAPSE | imgui.WINDOW_NO_TITLE_BAR | imgui.WINDOW_NO_SAVED_SETTINGS)
            imgui.begin_child("ConsoleOutput", 0, -25, False)
            for text, color in console.text_buffer:
                if color is None:
                    color = (0.25, 0.75, 1)
                imgui.text_colored(text, color[0], color[1], color[2], 0.8)
            imgui.text("")
            imgui.set_scroll_y(imgui.get_scroll_max_y())
            imgui.end_child()
            enter, text = imgui.input_text("Input", "", 256, imgui.INPUT_TEXT_ENTER_RETURNS_TRUE)
            if enter:
                if str.startswith(text, "/"):
                    text = str.replace(text, "/", "", 1)
                    console.handle_input(text)

            imgui.end()
        imgui.render()
        imgui_renderer.render(imgui.get_draw_data())
        imgui.end_frame()
        glfw.swap_buffers(window)

    glfw.terminate()


if __name__ == "__main__":
    print("Do not run this package directly!")
