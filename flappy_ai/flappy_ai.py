from collections import deque
from enum import Enum

import pyglet as pg
import pyglet.gl as gl
from pyglet.window import key
import noise
import random

from mymath import *
from drawing_util import *
import collision_util as collision

images = {} # image caching

sprite_scale = 5

def load_sprite(name, relative_scale=1, flip_y=False, origin=(0,0)):
	if name not in images:
		images[name] = pg.resource.image(name)
	
	img = images[name]

	scale = sprite_scale * relative_scale

	sprite = pg.sprite.Sprite(img)
	sprite.scale_x = scale
	sprite.scale_y = -scale if flip_y else scale

	sprite.origin = origin

	# enable nearest filtering, ugly but works
	gl.glEnable(gl.GL_TEXTURE_2D)
	gl.glBindTexture(gl.GL_TEXTURE_2D, sprite._texture.id)
	gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_NEAREST)

	return sprite

def draw_sprite(sprite, pos_screen_px, ori=0): # rotation_axis position inside of sprite in sprite pixels
	pos = pos_screen_px
	
	pos = (pos[0] * sprite_scale, pos[1] * sprite_scale) # place in pixel based global space
	pos = (pos[0] - sprite.origin[0] * sprite.scale_x, pos[1] - sprite.origin[1] * sprite.scale_y)
	
	rotation = ori # degrees
	
	axis_offset = rotate2(-rotation, (sprite.origin[0] * sprite.scale_x, sprite.origin[1] * sprite.scale_y))
	axis_offset = (axis_offset[0] -sprite.origin[0] * sprite.scale_x, axis_offset[1] -sprite.origin[1] * sprite.scale_y)

	pos = (pos[0] - axis_offset[0], pos[1] - axis_offset[1]) # correct for rotation_axis
	
	sprite.update(pos[0], pos[1], rotation)
	sprite.draw()

flappy_rotation_axis = (14,9) # px in sprite

# https://www.piskelapp.com/p/agxzfnBpc2tlbC1hcHByEwsSBlBpc2tlbBiAgKC63bP_Cww/edit
flappy_body = load_sprite("flappy_body.png", 3/5, origin=flappy_rotation_axis)
flappy_wings = load_sprite("flappy_wings.png", 3/5, origin=flappy_rotation_axis)

background = load_sprite("background.png")
ground = load_sprite("ground.png")
pipe_top = load_sprite("pipe.png")
pipe_bottom = load_sprite("pipe.png", flip_y=True)

#test = load_sprite("test.png", relative_scale=2, origin=(16,16))

ldist = pg.text.Label(y = background.height -24, font_name="Consolas", font_size=20, color=(0,0,0,255))
lscore = pg.text.Label(y = ldist.y -20, font_name="Consolas", font_size=20, color=(0,0,0,255))

lrestart = pg.text.Label(text="[R]       Restart", y = ldist.y -54, font_name="Consolas", font_size=20, color=(0,0,0,255))
ljumpkey = pg.text.Label(text="[Any Key] Flap Wings", y = ldist.y -78, font_name="Consolas", font_size=20, color=(0,0,0,255))

wnd = pg.window.Window(width=background.width, height=background.height, caption="Flappy AI")

###########
class Player:
	class State(Enum):
		playing = 0
		crashing = 1
		crashed = 2

class Game:
	def __init__(self):
		self.reset()

	def reset(self):
		self.playing_flappy_x = 46 # where flappy is while player is playing (when player has )
		self.flappy_x = self.playing_flappy_x

		self.flappy_jump_vel_y = 120

		self.flappy_y = 100.0
		self.flappy_vel_y = self.flappy_jump_vel_y / 2

		self.state = Player.State.playing

		self.flappy_t_since_jump = 0

		self.grav_accel = -400

		self.dist = 0

		self.dist_score = 0
		self.score = 0

		self.speed = 70 # 70
		
		self.noise_seed = random.uniform(0,1000)
		self.pipe_noise_x = 0

		self.screen_width = ground.width / sprite_scale;
		self.pipes_seperation = self.screen_width * 0.7 # 0.7
		self.pipe_gap = 40 # 40

		self.pipe_w = pipe_top.width /sprite_scale

		self.pipes = deque()

		self._dbg_t = 0

	def score_point(self):
		self.score += 1
		
	def need_to_gen_pipe_x(self):
		
		if len(self.pipes) == 0:
			gen_pipe = True
			next_pipe_x = 150
		else:
			last_pipe_x = self.pipes[-1].x
			next_pipe_x = last_pipe_x + self.pipes_seperation
		
			# generate next pipe when it enters to the right of the screen
			pipe_left = next_pipe_x

			gen_pipe = self.dist + self.screen_width >= pipe_left

		return gen_pipe, next_pipe_x
	def pipe_left_screen(self, pipe):
		pipe_right = pipe.x + self.pipe_w
		return self.dist > pipe_right

	# generate height of tube based on perlin/simplex noise to keep tubes from looking too random
	#  noise_x should be continous, increate by 1 per tube or by 1.5, 2, etc. to increase the frequency of the variation to vary difficulty after a time
	def random_pipe_height(self, noise_x): # 
		
		#rand = abs(noise_x % 2 -1) * 2 -1 # [-1,1]
		rand = noise.snoise2(noise_x, self.noise_seed)

		lowest = ground.height/sprite_scale + self.pipe_gap/2 + 10
		highest = 192 - self.pipe_gap/2 - 10

		return map(rand, -1,1, lowest,highest)
	
	class Pipe:
		def __init__(self, x,y, gap):
			self.x = x
			self.y = y
			self.gap = gap
			self.passed = False

	def update_pipes(self):

		while len(self.pipes) > 0 and self.pipe_left_screen(self.pipes[0]):
			self.pipes.popleft()

		while True:
			gen_pipe, next_pipe_x = self.need_to_gen_pipe_x()

			if not gen_pipe:
				break
			
			y = self.random_pipe_height(self.pipe_noise_x)
			self.pipes.append(self.Pipe(next_pipe_x, y, self.pipe_gap))

			self.pipe_noise_x += self.pipes_seperation / self.screen_width
			
		if self.state == Player.State.playing:
			for pipe in self.pipes:
				if not pipe.passed and self.dist + self.flappy_x >= pipe.x + self.pipe_w / 2:
					pipe.passed = True
					self.score_point()
	
	def collide_flappy(self):
		flappy_collider = collision.AAEllipse(pos=(self.flappy_x, self.flappy_y), size=(9 * flappy_body.scale_x / sprite_scale, 8.5 * flappy_body.scale_y / sprite_scale))
		
		ground_collider = collision.AABB(min=(-math.inf, -math.inf), max=(+math.inf, +ground.height / sprite_scale))

		colliding = collision.check(flappy_collider, ground_collider)
		
		if self.state == Player.State.playing:
			for pipe in self.pipes:

				x = pipe.x - self.dist

				pipe_top_collider		= collision.AABB(min=(x, pipe.y + pipe.gap/2), max=(x +self.pipe_w, +math.inf))
				pipe_bottom_collider	= collision.AABB(min=(x, -math.inf), max=(x +self.pipe_w, pipe.y - pipe.gap/2))
				
				colliding = colliding or collision.check(flappy_collider, pipe_top_collider)
				colliding = colliding or collision.check(flappy_collider, pipe_bottom_collider)

		if self.state == Player.State.playing and colliding:
			self.state = Player.State.crashing
			self.collided_dist = self.dist
			self.flappy_vel_y = self.flappy_jump_vel_y * 0.3

		elif self.state == Player.State.crashing and colliding:
			self.state = Player.State.crashed
		
		# prevent flappy from penetration ground
		self.flappy_y = max(self.flappy_y, ground_collider.max[1] + flappy_collider.size[1])

		return colliding

	def dbg_draw_colliders(self):
		flappy_collider = collision.AAEllipse(pos=(self.flappy_x, self.flappy_y), size=(9 * flappy_body.scale_x / sprite_scale, 8.5 * flappy_body.scale_y / sprite_scale))
		
		ground_collider = collision.AABB(min=(-math.inf, -math.inf), max=(+math.inf, +ground.height / sprite_scale))

		colliding = collision.check(flappy_collider, ground_collider)
		
		if self.state == Player.State.playing:
			for pipe in self.pipes:
				x = pipe.x - self.dist

				draw_rect((x * sprite_scale, (pipe.y + pipe.gap/2) * sprite_scale), (self.pipe_w * sprite_scale, 9999 * sprite_scale))
				draw_rect((x * sprite_scale, (pipe.y - pipe.gap/2 -9999) * sprite_scale), (self.pipe_w * sprite_scale, 9999 * sprite_scale))

		draw_rect((-999 * sprite_scale, -999 * sprite_scale), ((999*2 +ground.width / sprite_scale) * sprite_scale, (ground.height / sprite_scale + 999) * sprite_scale))

		draw_circle((flappy_collider.pos[0] * sprite_scale, flappy_collider.pos[1] * sprite_scale), (flappy_collider.size[0] * sprite_scale, flappy_collider.size[1] * sprite_scale), col = (255,255,40,180) if colliding else (40,255,40,180))

	def update(self, dt):

		self.dist += self.speed * dt# * (0.3 if self.state != Player.State.playing else 1)

		self.update_pipes()
		
		if self.state != Player.State.crashed:
			self.flappy_vel_y += self.grav_accel * dt

			self.flappy_vel_y = max(self.flappy_vel_y, -1500)

			self.flappy_y += self.flappy_vel_y * dt
			self.flappy_y = clamp(self.flappy_y, -500, +1000)

			self.collide_flappy()
		
		if self.state != Player.State.playing:
			self.flappy_x = self.playing_flappy_x + self.collided_dist - self.dist
			
		if self.state == Player.State.playing:
			self.dist_score = self.dist

		self.flappy_t_since_jump += dt
		
		self._dbg_t += dt

	def jump(self):
		if self.state == Player.State.playing:
			self.flappy_vel_y = self.flappy_jump_vel_y

			self.flappy_t_since_jump = 0

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

		for pipe in self.pipes:
			draw_pipe(pipe.x - self.dist, pipe.y, pipe.gap)
	
	def draw(self):
		wnd.clear()
	
		#
		draw_sprite(background, (0,0))

		#
		flappy_ori = self.calc_flappy_ori()
		flappy_wing_ori = self.calc_flappy_flap_anim()

		draw_sprite(flappy_body, (self.flappy_x,self.flappy_y), ori=flappy_ori) # rotate body and wings around same axis, so that they match up
		draw_sprite(flappy_wings, (self.flappy_x,self.flappy_y), ori=flappy_ori + flappy_wing_ori)
		
		#
		self.draw_pipes()

		#
		ground_x = -(self.dist % self.screen_width)

		draw_sprite(ground, (ground_x, 0))
		draw_sprite(ground, (ground_x +self.screen_width, 0))

		#
		ldist.text = "dist: %4d" % self.dist_score
		ldist.draw()
		
		lscore.text = "score: %3d" % self.score
		lscore.draw()
		
		lrestart.draw()
		ljumpkey.draw()

		#self.dbg_draw_colliders()

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
