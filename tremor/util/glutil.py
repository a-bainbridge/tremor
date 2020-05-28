from OpenGL.GL import *

from tremor.core import console


def log_capabilities():
    console.conprint(
        "OPENGL VERSION: " + str(glGetIntegerv(GL_MAJOR_VERSION)) + "." + str(glGetIntegerv(GL_MINOR_VERSION)))
    caps = {
        GL_MAX_TEXTURE_SIZE,
        GL_MAX_COMBINED_TEXTURE_IMAGE_UNITS,
        GL_MAX_CUBE_MAP_TEXTURE_SIZE,
        GL_MAX_VIEWPORT_DIMS,
        GL_MAX_PATCH_VERTICES,
        GL_MAX_UNIFORM_BLOCK_SIZE,
        GL_MAX_UNIFORM_BUFFER_BINDINGS,
        GL_MAX_UNIFORM_LOCATIONS,
        GL_MAX_CULL_DISTANCES
    }
    for cap in caps:
        console.conprint(cap.name + " = " + str(glGetIntegerv(cap)))
