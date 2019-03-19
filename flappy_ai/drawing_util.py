import pyglet as pg
import pyglet.gl as gl

from mymath import *

def draw_rect(pos, size, col=(255,30,30,200)):
	
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

def draw_circle(pos, size, col=(255,30,30,200), res=128):
	
	gl.glEnable(gl.GL_BLEND)
	gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)

	poss = []

	for i in range(res):
		t0 = i / res
		t1 = (i+1) / res
		
		v0 = rotate2(t0 * 360, (1,0))
		v1 = rotate2(t1 * 360, (1,0))

		poss += pos
		poss += (pos[0] + v0[0] * size[0],	pos[1] + v0[1] * size[1])
		poss += (pos[0] + v1[0] * size[0],	pos[1] + v1[1] * size[1])

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

