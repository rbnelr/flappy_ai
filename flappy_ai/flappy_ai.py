import pyglet as pg
import pyglet.gl as gl
from pyglet.window import key
from collections import deque

from mymath import *

def draw_rect(pos, size):
	pg.graphics.draw(4, pg.gl.GL_QUADS, ('v2f', (	pos[0],				pos[1],
													pos[0] + size[0],	pos[1],
													pos[0] + size[0],	pos[1] + size[1],
													pos[0],				pos[1]
													)))
#def draw_graph(pos_screen, size, func): # func(x) -> x, y in [0,1]
#	pg.graphics.draw(4, pg.gl.GL_QUADS, ('v2f', (	pos[0],				pos[1],
#													pos[0] + size[0],	pos[1],
#													pos[0] + size[0],	pos[1] + size[1],
#													pos[0],				pos[1]
#													)))

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

		self.pipes = deque()
		self.pipes.append((150, 100))
		self.pipes.append((250, 140))
		self.pipes.append((350, 90))

		self._dbg_t = 0

	def update(self, dt):

		self.dist += self.speed * dt

		if self.flappy_y < 80 and self.flappy_vel_y < 0:
			self.jump()

		self.flappy_vel_y += self.grav_accel * dt

		self.flappy_vel_y = max(self.flappy_vel_y, -1500)

		self.flappy_y += self.flappy_vel_y * dt

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
		
		def draw_pipe(x, gap_y, gap=40):
			draw_sprite(pipe_top,		(x, gap_y + gap/2))
			draw_sprite(pipe_bottom,	(x, gap_y - gap/2))

		for pipe in self.pipes:
			draw_pipe(pipe[0] - self.dist, pipe[1])

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
		screen_width = ground.width / sprite_scale;
		ground_x = -(self.dist % screen_width)

		draw_sprite(ground, (ground_x, 0))
		draw_sprite(ground, (ground_x +screen_width, 0))

		#
		ldist.text = "dist: %4d" % self.dist
		ldist.draw()

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
