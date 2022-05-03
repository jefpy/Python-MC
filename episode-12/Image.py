from ctypes import byref
import math
from re import S
import pyglet
from pyglet import gl

class Image:
    def __init__(self, texture_path, x, y, scale):
        self.image = pyglet.image.load(texture_path)
        self.texture = self.image.get_texture()
        self.scale = math.floor(float(scale))
        self.x = math.floor(float(x))
        self.y = math.floor(float(y))
        self.read_fbo_id = gl.GLuint(0)
        gl.glGenFramebuffers(1, byref(self.read_fbo_id))
        gl.glBindFramebuffer(gl.GL_READ_FRAMEBUFFER, self.read_fbo_id)
        gl.glFramebufferTexture2D(gl.GL_READ_FRAMEBUFFER, gl.GL_COLOR_ATTACHMENT0, gl.GL_TEXTURE_2D, self.texture.id, 0)
        gl.glBindFramebuffer(gl.GL_READ_FRAMEBUFFER, 0)
    
    def update(self, x):
        self.x = x

    def draw(self):
        gl.glBindFramebuffer(gl.GL_READ_FRAMEBUFFER, self.read_fbo_id)
        gl.glBlitFramebuffer(0, 0, self.texture.width, self.texture.height, self.x, self.y * self.scale,
                             self.x + (self.texture.width * self.scale), self.y + (self.texture.height * self.scale), gl.GL_COLOR_BUFFER_BIT,
                             gl.GL_NEAREST)
        gl.glBindFramebuffer(gl.GL_READ_FRAMEBUFFER, 0)