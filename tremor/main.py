import OpenGL

from tremor.core.scene import Scene
from tremor.core.entity import Entity

OpenGL.USE_ACCELERATE = False

import glfw

from tremor.loader import gltf_loader, texture_loading, scene_loader
from tremor.util import glutil, configuration
from tremor.core import game_clock

from tremor.graphics.shaders import *
from tremor.graphics.uniforms import *
import sys
import glm
from tremor.graphics import screen_utils, scene_renderer
from tremor.math import matrix

vbo, nvbo, cvbo = None, None, None
window = None

framecount = 0
MAX_FPS: int = None
fps_clock = game_clock.FPSController()

inputs = {'mouse': [0, 0]}  # this is probably bad

current_scene: Scene = None


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
    add_uniform_to_all('isTextured', 'bool')


def render():
    #current_scene.active_camera.transform.translate_local([0, 0.01, 0])
    scene_renderer.render(current_scene)
    glFlush()
    fps_clock.capFPS(screen_utils.MAX_FPS)


def reshape(w, h):
    glViewport(0, 0, w, h)
    screen_utils.WIDTH = w
    screen_utils.HEIGHT = h

wireframe = False

def keyboard_callback(window, key, scancode, action, mods):
    global wireframe
    if key == glfw.KEY_ESCAPE:
        glfw.set_window_should_close(window, glfw.TRUE)
        return
    if action == glfw.RELEASE:
        return
    if key == glfw.KEY_F:
        if action == glfw.REPEAT:
            return
        glPolygonMode(GL_FRONT_AND_BACK, GL_FILL if wireframe else GL_LINE)
        wireframe = not wireframe
    magnitude = 0.1
    if mods == 1:
        tform = current_scene.active_camera.transform
    else:
        tform = current_scene.active_camera.transform
    if key == glfw.KEY_UP:
        tform.translate_local([magnitude, 0, 0])
    if key == glfw.KEY_DOWN:
        tform.translate_local([-magnitude, 0, 0])
    if key == glfw.KEY_LEFT:
        tform.translate_local([0, 0, -magnitude])
    if key == glfw.KEY_RIGHT:
        tform.translate_local([0, 0, magnitude])
    if key == glfw.KEY_SPACE:
        tform.translate_local([0, magnitude, 0])
    if key == glfw.KEY_LEFT_CONTROL or key == glfw.KEY_RIGHT_CONTROL:
        tform.translate_local([0, -magnitude, 0])
    if key == glfw.KEY_Q:
        tform.rotate_local(matrix.quaternion_from_angles(np.array([magnitude, 0, 0])))
    if key == glfw.KEY_E:
        tform.rotate_local(matrix.quaternion_from_angles(np.array([-magnitude, 0, 0])))
    if key == glfw.KEY_A:
        tform.rotate_local(matrix.quaternion_from_angles(np.array([0, magnitude, 0])))
    if key == glfw.KEY_D:
        tform.rotate_local(matrix.quaternion_from_angles(np.array([0, -magnitude, 0])))
    if key == glfw.KEY_W:
        tform.rotate_local(matrix.quaternion_from_angles(np.array([0, 0, -magnitude])))
    if key == glfw.KEY_S:
        tform.rotate_local(matrix.quaternion_from_angles(np.array([0, 0, magnitude])))
    if key == glfw.KEY_R:
        tform.set_translation([0, 0, 0])
        tform.set_rotation([0, 0, 0, 1])


    inputs['key'] = key


def mouse_callback(window, x, y):
    inputs['mouse'] = [x, y]
    current_scene.active_camera.transform.set_rotation(matrix.quaternion_from_angles([0, np.pi * np.mod(x/20.0 + 90, 360)/180, 0]))


def mouseclick_callback(window, button, action, modifiers):
    print(fps_clock.average_fps)


def error_callback(error, description):
    print(str(error) + " : " + description.decode(), file=sys.stderr)


def main():
    global window, vbo, nvbo, cvbo
    global current_scene

    glfw.set_error_callback(error_callback)

    if not glfw.init():
        print("GLFW Initialization fail!")
        return

    graphics_settings = configuration.get_graphics_settings()

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
        glfw.OPENGL_PROFILE: glfw.OPENGL_CORE_PROFILE
    }

    window = create_window(size=(screen_utils.WIDTH, screen_utils.HEIGHT), pos="centered", title="Quake-like",
                           monitor=screen, hints=hints,
                           screen_size=glfw.get_monitor_physical_size(glfw.get_primary_monitor()))
    glfw.set_input_mode(window, glfw.CURSOR, glfw.CURSOR_DISABLED)
    glutil.log_capabilities()
    glEnable(GL_CULL_FACE)
    glCullFace(GL_BACK)
    glEnable(GL_DEPTH_TEST)
    glDepthMask(GL_TRUE)
    glDepthFunc(GL_LEQUAL)
    glDepthRange(0.0, 1.0)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    create_all_programs()

    # create the uniforms
    create_uniforms()
    # initialize all the uniforms for all the prpograms
    init_all_uniforms()

    texture_loading.load_all_textures('data/textures', {
        # https://open.gl/textures
        'noise_512': {
            'clamp_mode': GL_REPEAT
        }
    })
    scene_file = open("data/scenes/debug.tsf", "r", encoding="utf-8")
    current_scene = scene_loader.load_scene(scene_file)
    cam = Entity("camera")
    cam.transform.set_translation([3, 3, 3])
    cam.transform.set_rotation(matrix.quaternion_from_angles([0, np.pi/2, 0]))
    current_scene.active_camera = cam

    fps_clock.start()

    glfw.set_mouse_button_callback(window, mouseclick_callback)
    glfw.set_cursor_pos_callback(window, mouse_callback)
    glfw.set_key_callback(window, keyboard_callback)

    while not glfw.window_should_close(window):
        # todo call an update method as well
        render()
        glfw.swap_buffers(window)
        glfw.poll_events()

    glfw.terminate()


if __name__ == "__main__":
    print("Do not run this package directly!")
