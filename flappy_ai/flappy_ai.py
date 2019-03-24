from collections import deque, namedtuple
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

def draw_sprite(sprite, pos_screen_px, ori=0, alpha=255): # rotation_axis position inside of sprite in sprite pixels
	pos = pos_screen_px
	
	pos = (pos[0] * sprite_scale, pos[1] * sprite_scale) # place in pixel based global space
	pos = (pos[0] - sprite.origin[0] * sprite.scale_x, pos[1] - sprite.origin[1] * sprite.scale_y)
	
	rotation = ori # degrees
	
	axis_offset = rotate2(-rotation, (sprite.origin[0] * sprite.scale_x, sprite.origin[1] * sprite.scale_y))
	axis_offset = (axis_offset[0] -sprite.origin[0] * sprite.scale_x, axis_offset[1] -sprite.origin[1] * sprite.scale_y)

	pos = (pos[0] - axis_offset[0], pos[1] - axis_offset[1]) # correct for rotation_axis
	
	sprite.update(pos[0], pos[1], rotation)

	sprite.opacity = alpha

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

text_rows = {}

labels_batch = pg.graphics.Batch()

_labels_cache = {}
def gen_text_rows():
	for row, text in text_rows.items():
		if row not in _labels_cache:
			_labels_cache[row] = pg.text.Label(font_name="Consolas", font_size=14, color=(0,0,0,255), batch=labels_batch)
		l = _labels_cache[row]

		l.text = text
		l.y = background.height -16 * (row +1)

wnd = pg.window.Window(width=background.width, height=background.height, caption="Flappy AI")

###########
class Player:
	class Control:
		def __init__(self):
			self.jump = False

			self.fitness = 0

		def update(self, dt, ai_vision):
			pass

	class State(Enum):
		playing = 0
		crashing = 1
		crashed = 2

	def __init__(self, playing_flappy_x, initial_vel_y, control):
		self.control = control

		self.state = Player.State.playing

		self.x = playing_flappy_x
	
		self.y = 100.0

		self.vel_y = initial_vel_y

		self.t_since_jump = 0
		self.t_since_crashed = 0

		self.dist_score = 0
		self.score = 0
		self.crash_near_hole_ratio = 0
		
	def score_point(self):
		self.score += 1

	def calc_ori(self):
		return map_clamp(self.t_since_jump,  0.6, 1.0,  -8, 90)
	def calc_flap_anim(self): # wing_ori
		t = map(self.t_since_jump,  0.0, 0.13)
		t = clamp(t)
		
		t = abs(-t +0.5) * 2
		
		return lerp(-60,0, t)

human_player = Player.Control()

####
import neat_algo
from neat_algo import AI_Perceptrons

class Game_Round:
	def __init__(self, player_inputs, generation=None):
		self.playing_flappy_x = 46 # where flappy is while player is playing (when player is crashing/crashed his x  )
		
		self.flappy_jump_vel_y = 120
		
		self.players = [ Player(self.playing_flappy_x, self.flappy_jump_vel_y / 2, inp) for inp in player_inputs ]

		self.displayed_player = self.players[0] if self.players else None

		self.grav_accel = -400

		self.dist = 0
		self.speed = 70 # 70
		
		self.noise_seed = random.uniform(0,1000)
		self.pipe_noise_x = 0

		self.screen_width = ground.width / sprite_scale;
		self.screen_height = background.height / sprite_scale;
		self.pipes_seperation = self.screen_width * 0.7 # 0.7
		self.pipe_gap = 40 # 40

		self.pipe_w = pipe_top.width /sprite_scale

		self.pipes = deque()

		self.generation = generation

		self._dbg_t = 0
		
	def need_to_gen_pipe_x(self):
		#return False, 0 # disable pipes

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
		
		for pipe in self.pipes:
			if not pipe.passed and self.dist + self.playing_flappy_x >= pipe.x + self.pipe_w / 2:
				pipe.passed = True
			
				for player in self.players:
					if player.state == Player.State.playing:
						player.score_point() # alive players get point if they passed pipe

		

	def players_crashed(self):
		return (pl.state == Player.State.crashed for pl in self.players)

	def collide_flappy(self, player):
		flappy_collider = collision.AAEllipse(pos=(player.x, player.y), size=(9 * flappy_body.scale_x / sprite_scale, 8.5 * flappy_body.scale_y / sprite_scale))
		
		ground_collider = collision.AABB(min=(-math.inf, -math.inf), max=(+math.inf, +ground.height / sprite_scale))

		colliding = collision.check(flappy_collider, ground_collider)
		
		if colliding and player.state == Player.State.playing:
			player.crash_near_hole_ratio = 0
		
		if not colliding and player.state == Player.State.playing:
			for pipe in self.pipes:

				x = pipe.x - self.dist

				pipe_top_collider		= collision.AABB(min=(x, pipe.y + pipe.gap/2), max=(x +self.pipe_w, +math.inf))
				pipe_bottom_collider	= collision.AABB(min=(x, -math.inf), max=(x +self.pipe_w, pipe.y - pipe.gap/2))
				
				colliding = colliding or collision.check(flappy_collider, pipe_top_collider)
				colliding = colliding or collision.check(flappy_collider, pipe_bottom_collider)

				if colliding and player.state == Player.State.playing:
					player.crash_near_hole_ratio = 1 - (abs(player.y -pipe.y) / self.screen_height)
					break

		if player.state == Player.State.playing and colliding:
			player.state = Player.State.crashing
			player.collided_dist = self.dist
			player.vel_y = self.flappy_jump_vel_y * 0.3

		elif player.state == Player.State.crashing and colliding:
			player.state = Player.State.crashed
		
		# prevent flappy from penetration ground
		player.y = max(player.y, ground_collider.max[1] + flappy_collider.size[1])

		return colliding

	def dbg_draw_colliders(self):
		flappy_colliders = [collision.AAEllipse(pos=(player.x, player.y), size=(9 * flappy_body.scale_x / sprite_scale, 8.5 * flappy_body.scale_y / sprite_scale)) for player in self.players]
		
		ground_collider = collision.AABB(min=(-math.inf, -math.inf), max=(+math.inf, +ground.height / sprite_scale))

		colliding = collision.check(flappy_collider, ground_collider)
		
		#if self.state == Player.State.playing:
		for pipe in self.pipes:
			x = pipe.x - self.dist

			draw_rect((x * sprite_scale, (pipe.y + pipe.gap/2) * sprite_scale), (self.pipe_w * sprite_scale, 9999 * sprite_scale))
			draw_rect((x * sprite_scale, (pipe.y - pipe.gap/2 -9999) * sprite_scale), (self.pipe_w * sprite_scale, 9999 * sprite_scale))

		draw_rect((-999 * sprite_scale, -999 * sprite_scale), ((999*2 +ground.width / sprite_scale) * sprite_scale, (ground.height / sprite_scale + 999) * sprite_scale))

		for flappy_collider in flappy_colliders:
			draw_circle((flappy_collider.pos[0] * sprite_scale, flappy_collider.pos[1] * sprite_scale), (flappy_collider.size[0] * sprite_scale, flappy_collider.size[1] * sprite_scale), col = (255,255,40,180) if colliding else (40,255,40,180))
	
	def update(self, dt):

		self.dist += self.speed * dt

		self.update_pipes()
		
		next_pipe = -1
		for i, pipe in enumerate(self.pipes):
			if ((pipe.x - self.dist) - self.playing_flappy_x) > 0:
				next_pipe = i
				break
		
		prev_pipe = self.pipes[next_pipe-1] if next_pipe > 0 else None
		next_pipe = self.pipes[next_pipe] if next_pipe >= 0 else None

		for pl in self.players:
			ai_vision = AI_Perceptrons(
					(next_pipe.x - self.dist) - pl.x				if next_pipe else +math.inf,
					(prev_pipe.x - self.dist) - pl.x + self.pipe_w 	if prev_pipe else -math.inf,
					pl.y,
					pl.y - (next_pipe.y - next_pipe.gap/2)			if next_pipe else -math.inf,
					pl.y - (next_pipe.y + next_pipe.gap/2)			if next_pipe else +math.inf,
				)

			
			pl.control.update(dt, ai_vision)
			
			if pl is self.displayed_player:
				self.displ_ai_vision = ai_vision

			if pl.state != Player.State.crashed:
				
				if pl.control.jump and pl.state == Player.State.playing:
					pl.vel_y = self.flappy_jump_vel_y
					
					pl.t_since_jump = 0
				pl.control.jump = False

				pl.vel_y += self.grav_accel * dt

				pl.vel_y = max(pl.vel_y, -1500)

				pl.y += pl.vel_y * dt
				pl.y = clamp(pl.y, -500, +1000)

				self.collide_flappy(pl)
		
			if pl.state != Player.State.playing:
				pl.x = self.playing_flappy_x + pl.collided_dist - self.dist
			
			if pl.state == Player.State.playing:
				pl.dist_score = math.floor(self.dist / 10)

			if pl.state == Player.State.crashed:
				pl.t_since_crashed += dt
				
			pl.control.fitness = neat_algo.calc_fitness(pl.score, pl.dist_score, pl.state != Player.State.playing, pl.crash_near_hole_ratio)

			pl.t_since_jump += dt
		
		self.players[:] = [x for x in self.players if x.t_since_crashed < 2] # remove players who have crashed from simulation and drawing after a short while

		active_players = [p for p in self.players if p.state == Player.State.playing]
		self.displayed_player = active_players[0] if active_players else None # update displayed player

		self._dbg_t += dt

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

		# draw all players with weak alpha and displayed player with full alpha on top
		def draw_player(player, alpha):
			ori = player.calc_ori()
			wing_ori = player.calc_flap_anim()

			draw_sprite(flappy_body, (player.x,player.y), ori=ori, alpha=alpha) # rotate body and wings around same axis, so that they match up
			draw_sprite(flappy_wings, (player.x,player.y), ori=ori + wing_ori, alpha=alpha)
		
		for player in (p for p in self.players[0:30] if p is not self.displayed_player):
			draw_player(player, 80)

		if self.displayed_player:
			draw_player(self.displayed_player, 255)
		
		#
		self.draw_pipes()

		#
		ground_x = -(self.dist % self.screen_width)

		draw_sprite(ground, (ground_x, 0))
		draw_sprite(ground, (ground_x +self.screen_width, 0))

		#
		try:
			text_rows[0] = "dist: %4d"			% self.displayed_player.dist_score
			text_rows[1] = "score: %3d"			% self.displayed_player.score
			text_rows[2] = "fitness: %3.2f"		% self.displayed_player.control.fitness
			text_rows[3] = "cnhr: %1.2f"		% self.displayed_player.crash_near_hole_ratio
		except:
			pass
		
		try:
			text_rows[4] = "act: %1.2f thrs: %1.2f" % (displayed_player().control.jump_act, displayed_player().control.jump_thres)
		except:
			pass

		text_rows[5] = "[R]       Restart"
		text_rows[6] = "[Any Key] Flap Wings"

		text_rows[7] = "generation: %3d" % self.generation

		text_rows[8] = "active players: %3d" % sum(p.state == Player.State.playing for p in self.players)
		
		text_rows[9] = "dist x: %3.2f pdist x: %3.2f  y: %3.2f dist yl: %3.2f dist yh: %3.2f" % self.displ_ai_vision if hasattr(self, "displ_ai_vision") else ("-")*3
		
		gen_text_rows()
		labels_batch.draw()

		#self.dbg_draw_colliders()

#########

class Evolved_AI(Player.Control):
	
	def __init__(self, nn):
		super(Evolved_AI, self).__init__()

		self.t_since_jump = 0
		self.nn = nn
		
	def update(self, dt, ai_vision):
		self.jump_act = self.nn.activate(ai_vision)[0]
		
		self.jump_thres = 1.0 / (6 * self.t_since_jump + 1) # output neuron actiovations needs to be less to trigger a jump the longer a jump was not triggered
		# this should allow the output neuron to get frequency control over jumping instead of binary control (binary = never jump / jump every frame)

		#if self.jump_act >= self.jump_thres:
		#	self.jump = True
		#	self.t_since_jump = 0

		if self.jump_act >= 0.5:
			self.jump = True
			self.t_since_jump = 0

		self.t_since_jump += dt

class App:
	def __init__(self):
		self.generation = -1
		self.new_round()

	def new_round(self):
		self.generation += 1

		fitnesses = [ ai.fitness for ai in self.ai_players ] if hasattr(self, "ai_players") else None
		self.ai_players = [ Evolved_AI(nn) for nn in neat_algo.evolution_step(fitnesses) ]

		self.players = []
		#self.players += [human_player]
		self.players += self.ai_players

		self.round = Game_Round(self.players, self.generation)
		
	def update(self, dt):
		self.round.update(dt)

		if all( self.round.players_crashed() ):
			self.new_round()

	def draw(self):
		self.round.draw()

app = App()

def update(dt):

	#for i in range(1):
	app.update(1 / 60) # fixed dt to allow speeing up game

@wnd.event
def on_draw():
	app.draw()

@wnd.event
def on_key_press(symbol, modifiers):
	if symbol == key.R:
		app.new_round()
	else:
		human_player.jump = True
		
@wnd.event
def on_mouse_press(x, y, button, modifiers):
	human_player.jump = True

pg.clock.schedule_interval(update, 1 / 60)

pg.app.run()

#import cProfile
#cProfile.run('pg.app.run()', sort="cumtime")
