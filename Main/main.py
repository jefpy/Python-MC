import math
import ctypes
import os
import random
from turtle import width
import pyglet
from Image import Image

pyglet.options["shadow_window"] = False
pyglet.options["debug_gl"] = False
pyglet.options['audio'] = ('pulse', 'openal', 'silent')

import pyglet.gl as gl

import matrix
import shader
import player

import block_type
import texture_manager

import chunk
import world

import hit

file_path = os.path.dirname(os.path.abspath(__file__))
os.chdir(file_path)

soundList = []
p = pyglet.media.Player()

with os.scandir(file_path) as listEntries:
	for entry in listEntries:
		if entry.is_dir:
			if entry.name == "sounds":
				with os.scandir(entry) as sounds:
					for sound in sounds:
						soundList.append(sound.name)

def fetchSong(num):
	snd = pyglet.media.load(f"sounds/{soundList[num]}")
	return snd

class Window(pyglet.window.Window):
	def __init__(self, **args):
		super().__init__(**args)

		self.WIDTH = self.width
		self.HEIGHT = self.height

		# create world

		self.world = world.World()
		
		# create shader

		self.shader = shader.Shader("vert.glsl", "frag.glsl")
		self.shader_sampler_location = self.shader.find_uniform(b"texture_array_sampler")
		self.shader.use()

		# pyglet stuff

		pyglet.clock.schedule_interval(self.update, 1.0 / 120)
		self.mouse_captured = False

		# player stuff

		self.player = player.Player(self.world, self.shader, self.width, self.height)
		self.sensitivity = 0.005

		# misc stuff

		self.holding = None
		self.block_scale = 2
		self.offset = 0
		self.activeSlotNum = 0

		self.slots = {"1": None, "2": None, "3": None, "4": None, "5": None, "6": None, "7": None, "8": None, "9": None}
		self.activeSlot = self.slots.get("1")
		self.selectedX = 0

		# 2d on-screen images

		self.image_list = []

		self.crosshair_image = Image(f"textures/crosshair.png", (self.WIDTH)/2, (self.HEIGHT)/2, scale=1)
		self.selected  = Image(f"textures/selection.png", self.selectedX, y=0, scale=1)

		self.image_list.append(self.crosshair_image)
		
		for slot in range(9):
			slot = Image(f"textures/slot.png", (self.selected.x) + self.offset, 0, 1)
			self.image_list.append(slot)
			self.offset += 44

		self.offset = 0
		self.image_list.append(self.selected)
		self.iteration = 0
		for x in range(9):
			num = random.randint(1, len(self.world.block_types) - 1)
			self.png = self.world.block_types[num].block_face_textures.get("all")
			self.block_image = Image(f"textures/{self.png}.png", self.image_list[self.iteration+1].x + 3, self.image_list[self.iteration+1].y + 3, self.block_scale)
			self.block_image.width = 15
			self.block_image.height = 20
			self.image_list.append(self.block_image)
			self.offset += 44
			if self.iteration == 0:
				self.holding = num
			self.slots[str(self.iteration+1)] = num
			self.iteration += 1


	def update(self, delta_time): 
		# print(f"FPS: {1.0 / delta_time}")
		if p.playing == False:
			num = random.randint(0, len(soundList)-1)
			name = soundList[num]
			snd = fetchSong(num)
			p.queue(snd)
			p.play()
			print(f"{name[:-28]}\n")

		if not self.mouse_captured:
			self.player.input = [0, 0, 0]
			
		self.WIDTH, self.HEIGHT = self.get_size()
		self.player.update(delta_time)
		self.crosshair_image.updateCross(x=int(self.WIDTH/2), y=int(self.HEIGHT/2))
		self.selected.updateSelect(int(self.image_list[self.activeSlotNum+1].x))
		self.selectedX = int(self.WIDTH / 2 - 208)
		
		offset = 0
		for x in range(1, 10, 1):
			self.image_list[x].updateSelect(self.selectedX + offset)
			offset += 44

		offset = 0
		for x in range(11, 20, 1):
			self.image_list[x].updateSelect(self.selectedX + offset + 7)
			offset += 44
	
	def on_draw(self):
		self.clear()

		self.player.update_matrices()
		
		# bind textures
		gl.glActiveTexture(gl.GL_TEXTURE0)
		gl.glBindTexture(gl.GL_TEXTURE_2D_ARRAY, self.world.texture_manager.texture_array)
		gl.glUniform1i(self.shader_sampler_location, 0)

		# draw stuff

		gl.glEnable(gl.GL_DEPTH_TEST)
		gl.glEnable(gl.GL_CULL_FACE)

		gl.glClearColor(0.0, 0.0, 0.0, 0.0)
		self.world.draw()

		for image in self.image_list:
			image.draw()

		gl.glFinish()

	# input functions

	def on_resize(self, width, height):
		# print(f"Resize {width} * {height}")
		gl.glViewport(0, 0, width, height)

		self.player.view_width = width
		self.player.view_height = height

	def on_mouse_press(self, x, y, button, modifiers):
		if not self.mouse_captured:
			self.mouse_captured = True
			self.set_exclusive_mouse(True)
			return

		# handle breaking/placing

		def hit_callback(current_block, next_block):
			if button == pyglet.window.mouse.RIGHT: 
				self.world.try_set_block(current_block, self.holding, self.player.collider)
			elif button == pyglet.window.mouse.LEFT: 
				self.world.set_block(next_block, 0)
			elif button == pyglet.window.mouse.MIDDLE:
				num = self.world.get_block_number(next_block)
				keys = list(self.slots.keys())
				self.slots[keys[self.activeSlotNum]] = num
				self.holding = num
				index = 11 + self.activeSlotNum
				self.image_list.pop(index)
				self.png = self.world.block_types[num].block_face_textures.get("all")
				self.block_image = Image(f"textures/{self.png}.png", self.selectedX + 3, self.selected.y + 4, self.block_scale)
				self.block_image.width = 20
				self.block_image.height = 20
				self.image_list.insert(index, self.block_image)

		x, y, z = self.player.position
		y += self.player.eyelevel
		hit_ray = hit.Hit_ray(self.world, self.player.rotation, (x, y, z))
		'''
		hit_ray2 = hit.Hit_ray(self.world, self.player.rotation, (x-1, y, z-1))
		hit_ray3 = hit.Hit_ray(self.world, self.player.rotation, (x-1, y, z))
		hit_ray4 = hit.Hit_ray(self.world, self.player.rotation, (x, y, z-1))
		'''
		hits = [];hits.append(hit_ray);# hits.append(hit_ray2);hits.append(hit_ray3);hits.append(hit_ray4)
		for hit_rays in hits:
			while hit_rays.distance < hit.HIT_RANGE:
				if hit_rays.step(hit_callback):
					if button == 4 or button == 2:
						break
					elif button == 1: 
						# continue will go until ray length; break will end it once it hits a block
						break
	
	def on_mouse_motion(self, x, y, delta_x, delta_y):
		if self.mouse_captured:

			self.player.rotation[0] += delta_x * self.sensitivity
			self.player.rotation[1] += delta_y * self.sensitivity

			self.player.rotation[1] = max(-math.tau / 4, min(math.tau / 4, self.player.rotation[1]))
	
	def on_mouse_drag(self, x, y, delta_x, delta_y, buttons, modifiers):
		self.on_mouse_motion(x, y, delta_x, delta_y)
	
	def on_key_press(self, key, modifiers):
		if not self.mouse_captured:
			return

		if   key == pyglet.window.key.D: self.player.input[0] += 1
		elif key == pyglet.window.key.A: self.player.input[0] -= 1
		elif key == pyglet.window.key.W: self.player.input[2] += 1
		elif key == pyglet.window.key.S: self.player.input[2] -= 1

		elif key == pyglet.window.key.SPACE : self.player.input[1] += 1
		elif key == pyglet.window.key.LSHIFT: 
			if self.player.speed == 2:
				self.player.target_speed += 1
			else:
				self.player.target_speed = player.SPRINTING_SPEED + 2; self.player.FOV += 5
		elif key == pyglet.window.key.LCTRL : 
			self.player.input[1] -= 1
			if not self.player.flying: 
				self.player.eyelevel = self.player.height - 0.3
				self.player.speed = 2

		elif key == pyglet.window.key.F:
			self.player.target_speed = 4.317
			self.player.flying = not self.player.flying

		elif key == pyglet.window.key.G:
			num = random.randint(1, len(self.world.block_types) - 1)
			keys = list(self.slots.keys())
			self.slots[keys[self.activeSlotNum]] = num
			self.holding = num
			index = 11 + self.activeSlotNum
			self.image_list.pop(index)
			self.png = self.world.block_types[num].block_face_textures.get("all")
			self.block_image = Image(f"textures/{self.png}.png", self.image_list[self.activeSlotNum+1].x + 5, self.image_list[self.activeSlotNum+1].y + 4, self.block_scale)
			self.block_image.width = 20
			self.block_image.height = 20
			self.image_list.insert(index, self.block_image)

		elif key == pyglet.window.key.O:
			print("Saved.")
			self.world.save.save()

		elif key == pyglet.window.key.R:
			x, y, z = self.player.position
			y += self.player.eyelevel
			hit_ray = hit.Hit_ray(self.world, self.player.rotation, (x, y, z))

			def hit_callback(current_block, next_block):
				current_block = hit_ray.block
				self.player.teleport(current_block)

			while hit_ray.distance < hit.HIT_RANGE:
				num = self.world.get_block_number(hit_ray.block)
				if hit_ray.step(hit_callback):
					break
			
		elif key == pyglet.window.key.ESCAPE:
			self.mouse_captured = False
			self.set_exclusive_mouse(False)
		
		elif key == 49:
			self.activeSlot = self.slots.get("1")
			self.activeSlotNum = 0
			self.holding = self.activeSlot
			self.selectedX = self.image_list[1].x
		elif key == 50:
			self.activeSlot = self.slots.get("2")
			self.activeSlotNum = 1
			self.holding = self.activeSlot
			self.selectedX = self.image_list[2].x
		elif key == 51:
			self.activeSlot = self.slots.get("3")
			self.activeSlotNum = 2
			self.holding = self.activeSlot
			self.selectedX = self.image_list[3].x
		elif key == 52:
			self.activeSlot = self.slots.get("4")
			self.activeSlotNum = 3
			self.holding = self.activeSlot
			self.selectedX = self.image_list[4].x
		elif key == 53:
			self.activeSlot = self.slots.get("5")
			self.activeSlotNum = 4
			self.holding = self.activeSlot
			self.selectedX = self.image_list[5].x
		elif key == 54:
			self.activeSlot = self.slots.get("6")
			self.activeSlotNum = 5
			self.holding = self.activeSlot
			self.selectedX = self.image_list[6].x
		elif key == 55:
			self.activeSlot = self.slots.get("7")
			self.activeSlotNum = 6
			self.holding = self.activeSlot
			self.selectedX = self.image_list[7].x
		elif key == 56:
			self.activeSlot = self.slots.get("8")
			self.activeSlotNum = 7
			self.holding = self.activeSlot
			self.selectedX = self.image_list[8].x
		elif key == 57:
			self.activeSlot = self.slots.get("9")
			self.activeSlotNum = 8
			self.holding = self.activeSlot
			self.selectedX = self.image_list[9].x
	
	def on_key_release(self, key, modifiers):
		if not self.mouse_captured:
			return

		if   key == pyglet.window.key.D: self.player.input[0] -= 1
		elif key == pyglet.window.key.A: self.player.input[0] += 1
		elif key == pyglet.window.key.W: self.player.input[2] -= 1
		elif key == pyglet.window.key.S: self.player.input[2] += 1

		elif key == pyglet.window.key.SPACE : self.player.input[1] -= 1
		elif key == pyglet.window.key.LSHIFT: self.player.target_speed = player.WALKING_SPEED; self.player.FOV = 90
		elif key == pyglet.window.key.LCTRL : 
			self.player.input[1] += 1; 
			self.player.eyelevel = self.player.height - 0.2; 
			self.player.speed = 4.317

class Game:
	def __init__(self):
		self.config = gl.Config(major_version = 3, minor_version = 3, depth_size = 16)
		self.window = Window(config = self.config, width = 1920, height = 1080, caption = "Minecraf", resizable = True, vsync = False)
		print("Playing:")
	
	def run(self):
		pyglet.app.run()

if __name__ == "__main__":
	game = Game()
	game.run()