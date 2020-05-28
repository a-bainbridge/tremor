import sys

import OpenGL
import glm

OpenGL.USE_ACCELERATE = False
import glfw
import imgui
from imgui.integrations.glfw import GlfwRenderer
from tremor.core import console
from tremor.util import glutil, configuration
from tremor.graphics.shaders import *
from tremor.graphics.uniforms import *
from tremor.graphics import screen_utils
from tremor.math import matrix
import numpy as np


def _create_window(size, pos, title, hints, screen_size, monitor=None, share=None, ):
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
    # glfw.set_input_mode(win, glfw.CURSOR, glfw.CURSOR_DISABLED)
    glfw.make_context_current(win)
    return win


class GraphicsSubsystem:
    def __init__(self):
        self.window = None
        self.imgui_renderer = None

    def init(self):
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
        self.window = _create_window(size=(screen_utils.WIDTH, screen_utils.HEIGHT), pos="centered", title="Tremor",
                                     monitor=screen, hints=hints,
                                     screen_size=glfw.get_monitor_physical_size(glfw.get_primary_monitor()))
        self.imgui_renderer = GlfwRenderer(self.window, attach_callbacks=False)
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
        create_branched_programs()
        # create the uniforms
        _create_uniforms()
        # initialize all the uniforms for all the prpograms
        init_all_uniforms()

    def reshape(self, w, h):
        glViewport(0, 0, w, h)
        screen_utils.WIDTH = w
        screen_utils.HEIGHT = h

    def window_close_requested(self):
        return glfw.window_should_close(self.window)

    def draw_scene(self, scene):
        framecount = 0
        if scene is None:
            return
        glClearColor(0.0, 0.0, 0.0, 0.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glUseProgram(0)
        perspective_mat = glm.perspective(glm.radians(100.0), screen_utils.aspect_ratio(), 0.1, 100000.0)
        tmat = scene.active_camera.transform._get_translation_matrix()
        rmat = scene.active_camera.transform._get_rotation_matrix()
        a = tmat.dot(rmat.dot(matrix.create_translation_matrix([1, 0, 0])))
        cam_vec = glm.vec3(scene.active_camera.transform.get_translation()[:3])
        point_at = glm.vec3(matrix.translation_from_matrix(a)[:3])
        view_mat = glm.lookAt(cam_vec, point_at, glm.vec3([0, 1, 0]))
        model_mat = np.identity(4, dtype='float32')  # by default, no transformations applied
        update_all_uniform('modelViewMatrix', [1, GL_FALSE, model_mat])
        update_all_uniform('viewMatrix', [1, GL_FALSE, np.array(view_mat)])
        update_all_uniform('projectionMatrix', [1, GL_FALSE, np.array(perspective_mat)])

        update_all_uniform('time', [framecount / screen_utils.MAX_FPS])  # seconds

        light_pos = [np.sin(framecount * 0.01) * 5, np.cos(framecount * 0.01) * 5, np.cos(framecount * 0.001)]
        update_all_uniform('light_pos', light_pos)

        scene.bind_scene_vao()
        for element in scene.entities:
            if element.is_renderable() and element.mesh.is_scene_mesh:
                element.mesh.render_scene_mesh(scene, element.transform)

        for element in scene.entities:
            if element.is_renderable():
                if not element.mesh.is_scene_mesh:
                    element.mesh.render(element.transform)
        framecount += 1

    def draw_console(self):
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
        self.imgui_renderer.render(imgui.get_draw_data())
        imgui.end_frame()

    def end_frame(self):
        glfw.swap_buffers(self.window)

    def shutdown(self):
        glfw.terminate()


def _create_uniforms():
    # Matricies
    add_uniform_to_all('modelViewMatrix', 'mat4')
    add_uniform_to_all('projectionMatrix', 'mat4')
    add_uniform_to_all('viewMatrix', 'mat4')

    # env
    add_uniform_to_all('time', 'float')

    # other
    add_uniform_to_all('light_pos', 'vec3')  # todo: ba


def error_callback(error, description):
    print(str(error) + " : " + description.decode(), file=sys.stderr)
