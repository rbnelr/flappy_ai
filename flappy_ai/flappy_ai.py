from collections import deque
import pyglet as pg
import pyglet.gl as gl
from pyglet.window import key
import noise
import random

from mymath import *

def draw_rect(pos, size, col=(255,30,30,200)):
	pos = (pos[0] * sprite_scale, pos[1] * sprite_scale)
	size = (size[0] * sprite_scale, size[1] * sprite_scale)
	
	gl.glEnable(gl.GL_BLEND)
	gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)

	poss = []

	poss += (pos[0] + size[0],	pos[1]				)
	poss += (pos[0] + size[0],	pos[1] + size[1]	)
	poss += (pos[0],			pos[1]				)
	poss += (pos[0],			pos[1]				)
	poss += (pos[0] + size[0],	pos[1] + size[1]	)
	poss += (pos[0],			pos[1] + size[1]	)

	count = len(poss) // 2

	pg.graphics.draw(count, pg.gl.GL_TRIANGLES, ('v2f', poss), ('c4B', col * count))

def draw_circle(pos, size, col=(255,30,30,200)):
	pos = (pos[0] * sprite_scale, pos[1] * sprite_scale)
	size = (size[0] * sprite_scale, size[1] * sprite_scale)
	
	gl.glEnable(gl.GL_BLEND)
	gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)

	poss = []

	poss += (pos[0] + size[0],	pos[1]				)
	poss += (pos[0] + size[0],	pos[1] + size[1]	)
	poss += (pos[0],			pos[1]				)
	poss += (pos[0],			pos[1]				)
	poss += (pos[0] + size[0],	pos[1] + size[1]	)
	poss += (pos[0],			pos[1] + size[1]	)

	count = len(poss) // 2

	pg.graphics.draw(count, pg.gl.GL_TRIANGLES, ('v2f', poss), ('c4B', col * count))

def draw_graph(pos_screen, size, func, res=0.2): # func(x) -> x, y in [0,1], res: line segments per pixel
	
	lines_pos = []

	count = math.floor(res * size[0])
	for i in range(0, count):
		x = i / (count -1)
		y = func(x)

		lines_pos.append(x * size[0] + pos_screen[0])
		lines_pos.append(y * size[1] + pos_screen[1])
		
	lines_col = (0,0,0,255) * (len(lines_pos) // 2)

	pg.graphics.draw(len(lines_pos) // 2, pg.gl.GL_LINE_STRIP, ('v2f', lines_pos), ('c4B', lines_col))

images = {} # image caching

sprite_scale = 5

def load_sprite(name, relative_scale=1, flip_y=False):
	if name not in images:
		images[name] = pg.resource.image(name)
	
	img = images[name]

	scale = sprite_scale * relative_scale

	sprite = pg.sprite.Sprite(img)
	sprite.scale_x = scale
	sprite.scale_y = -scale if flip_y else scale

	# enable nearest filtering, ugly but works
	gl.glEnable(gl.GL_TEXTURE_2D)
	gl.glBindTexture(gl.GL_TEXTURE_2D, sprite._texture.id)
	gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_NEAREST)

	return sprite

def draw_sprite(sprite, pos_screen_px, ori=0, rotation_axis=(0,0)): # rotation_axis position inside of sprite in sprite pixels
	pos = (pos_screen_px[0] * sprite_scale, pos_screen_px[1] * sprite_scale) # place in pixel based global space
	rotation = ori # degrees

	axis_offset = rotate2(-rotation, rotation_axis)
	axis_offset = (axis_offset[0] -rotation_axis[0], axis_offset[1] -rotation_axis[0])

	pos = (pos[0] - axis_offset[0] * sprite.scale_x, pos[1] - axis_offset[1] * sprite.scale_y) # correct for rotation_axis
	
	sprite.update(pos[0], pos[1], rotation)
	sprite.draw()

flappy_body = load_sprite("flappy_body.png", 3/5)
flappy_wings = load_sprite("flappy_wings.png", 3/5)

flappy_rotation_axis = (13,8) # px in sprite

background = load_sprite("background.png")
ground = load_sprite("ground.png")
pipe_top = load_sprite("pipe.png")
pipe_bottom = load_sprite("pipe.png", flip_y=True)

test = load_sprite("test.png", 2)

ldist = pg.text.Label(y = background.height -24, font_name="Consolas", font_size=18, color=(0,0,0,255))

wnd = pg.window.Window(width=background.width, height=background.height, caption="Flappy AI")

###########

class Game:
	def __init__(self):
		self.reset()

	def reset(self):
		self.flappy_y = 100.0
		self.flappy_vel_y = 0

		self.flappy_jump_vel_y = 120

		self.flappy_t_since_jump = 0

		self.grav_accel = -400

		self.dist = 0
		self.speed = 70
		
		self.noise_seed = random.uniform(0,1000)
		self.pipe_noise_x = 0

		self.screen_width = ground.width / sprite_scale;
		self.pipes_seperation = self.screen_width * 0.7
		self.pipe_gap = 40

		self.pipes = deque()

		self._dbg_t = 0
		
	def need_to_gen_pipe_x(self):
		
		if len(self.pipes) == 0:
			gen_pipe = True
			next_pipe_x = 150
		else:
			last_pipe_x = self.pipes[-1][0]
			next_pipe_x = last_pipe_x + self.pipes_seperation
		
			# generate next pipe when it enters to the right of the screen
			pipe_left = next_pipe_x

			gen_pipe = self.dist + self.screen_width >= pipe_left

		return gen_pipe, next_pipe_x
	def pipe_left_screen(self, pipe):
		pipe_right = pipe[0] + (pipe_top.width /sprite_scale)
		return self.dist > pipe_right

	# generate height of tube based on perlin/simplex noise to keep tubes from looking too random
	#  noise_x should be continous, increate by 1 per tube or by 1.5, 2, etc. to increase the frequency of the variation to vary difficulty after a time
	def random_pipe_height(self, noise_x): # 
		
		#rand = abs(noise_x % 2 -1) * 2 -1 # [-1,1]
		rand = noise.snoise2(noise_x, self.noise_seed)

		lowest = ground.height/sprite_scale + self.pipe_gap/2 + 10
		highest = 192 - self.pipe_gap/2 - 10

		return map(rand, -1,1, lowest,highest)
	
	def update_pipes(self):
		while len(self.pipes) > 0 and self.pipe_left_screen(self.pipes[0]):
			self.pipes.popleft()

		while True:
			gen_pipe, next_pipe_x = self.need_to_gen_pipe_x()

			if not gen_pipe:
				break
			
			y = self.random_pipe_height(self.pipe_noise_x)
			self.pipes.append((next_pipe_x, y))

			self.pipe_noise_x += self.pipes_seperation / self.screen_width

	def update(self, dt):

		self.dist += self.speed * dt

		self.update_pipes()

		if self.flappy_y < 80 and self.flappy_vel_y < 0:
			self.jump()

		self.flappy_vel_y += self.grav_accel * dt

		self.flappy_vel_y = max(self.flappy_vel_y, -1500)

		self.flappy_y += self.flappy_vel_y * dt
		self.flappy_y = clamp(self.flappy_y, -500, +1000)

		self.flappy_t_since_jump += dt
		
		self._dbg_t += dt

	def calc_flappy_ori(self):
		return map_clamp(self.flappy_t_since_jump,  0.6, 1.0,  -8, 90)
	def calc_flappy_flap_anim(self): # wing_ori
		t = map(self.flappy_t_since_jump,  0.0, 0.13)
		t = clamp(t)
		
		t = abs(-t +0.5) * 2
		
		return lerp(-60,0, t)

	def draw_pipes(self):
		
		def draw_pipe(x, gap_y, gap):
			draw_sprite(pipe_top,		(x, gap_y + gap/2))
			draw_sprite(pipe_bottom,	(x, gap_y - gap/2))

			#draw_rect((x, gap_y + gap/2), (pipe_top.width /sprite_scale, 9999))
			#draw_rect((x, gap_y - gap/2 -9999), (pipe_top.width /sprite_scale, 9999))

		for pipe in self.pipes:
			draw_pipe(pipe[0] - self.dist, pipe[1], self.pipe_gap)
	
	def draw(self):
		wnd.clear()
	
		#
		draw_sprite(background, (0,0))

		#
		flappy_ori = self.calc_flappy_ori()
		flappy_wing_ori = self.calc_flappy_flap_anim()

		draw_sprite(flappy_body, (46,self.flappy_y), ori=flappy_ori, rotation_axis=flappy_rotation_axis) # rotate body and wings around same axis, so that they match up
		draw_sprite(flappy_wings, (46,self.flappy_y), ori=flappy_ori + flappy_wing_ori, rotation_axis=flappy_rotation_axis)
		
		#
		self.draw_pipes()

		#
		ground_x = -(self.dist % self.screen_width)

		draw_sprite(ground, (ground_x, 0))
		draw_sprite(ground, (ground_x +self.screen_width, 0))

		#
		ldist.text = "dist: %4d" % self.dist
		ldist.draw()

		#draw_graph((0,0), (wnd.width, wnd.height), lambda x:
		#	 self.random_pipe_height(x + self.dist/self.screen_width) / (wnd.height/sprite_scale))

	def jump(self):
		self.flappy_vel_y = self.flappy_jump_vel_y

		self.flappy_t_since_jump = 0

#########

game = Game()

def update(dt):
	game.update(1 / 60) # fixed dt to allow speeing up game

@wnd.event
def on_draw():
	game.draw()

@wnd.event
def on_key_press(symbol, modifiers):
	if symbol == key.R:
		game.reset()
	else:
		game.jump()
		
@wnd.event
def on_mouse_press(x, y, button, modifiers):
    game.jump()

pg.clock.schedule_interval(update, 1 / 60)

pg.app.run()
