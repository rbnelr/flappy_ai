import math

def clamp(x, a=0, b=1):
	return min(max(x,a), b)

def lerp(a, b, t):
	return (1 -t) * a + t * b

def map(x, a_in, b_in, a_out=0, b_out=1):
	return (x -a_in) / (b_in - a_in) * (b_out -a_out) + a_out

def map_clamp(x, a_in, b_in, a_out=0, b_out=1):
	return clamp((x -a_in) / (b_in - a_in), 0,1) * (b_out -a_out) + a_out

def rotate2(ang, v):
	c = math.cos(math.radians(ang))
	s = math.sin(math.radians(ang))
	return (v[0] * +c + v[1] * -s,
			v[0] * +s + v[1] * +c)