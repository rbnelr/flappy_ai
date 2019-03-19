from collections import namedtuple

from mymath import *
import math

AAEllipse = namedtuple("Ellipse", "pos size")
AABB = namedtuple("AABB", "min max")

# check if two shapes overlap
# no penetration vector
# no predicted collision detection based on movement
def check(a, b):
	if		isinstance(a, AAEllipse)	and isinstance(b, AABB):
		return check_aaellipse_aabb(a,b)
	elif	isinstance(a, AABB)			and isinstance(b, AAEllipse):
		return check_aaellipse_aabb(b,a)
	else:
		raise ValueError("types not supported check({} {})".format( a.__class__.__name__, b.__class__.__name__ ))

def check_aaellipse_aabb(a, b):
	
	px = a.pos[0]
	py = a.pos[1]
	
	minx = b.min[0]
	miny = b.min[1]
	
	maxx = b.max[0]
	maxy = b.max[1]

	nearest_x = clamp(px, minx, maxx)
	nearest_y = clamp(py, miny, maxy)

	seper_x = px - nearest_x
	seper_y = py - nearest_y

	# scale offset into size of ellipse (ellipse has size (1,1) in this space)
	seper_scaled_x = seper_x / a.size[0]
	seper_scaled_y = seper_y / a.size[1] 

	dist = math.sqrt(seper_scaled_x * seper_scaled_x + seper_scaled_y * seper_scaled_y)

	return dist <= 1
