from collections import namedtuple

import neat
import random

perceptron_names = [ "prev_dist_x", "dist_x", "y", "dist_yl", "dist_yh" ]
AI_Perceptrons = namedtuple("AI_Perceptrons", perceptron_names)


config = neat.Config(	neat.DefaultGenome, neat.DefaultReproduction,
						neat.DefaultSpeciesSet, neat.DefaultStagnation,
						"neat_config.py" )
#config.genome_config.input_keys = perceptron_names

pop = neat.Population(config)

pop.add_reporter(neat.StdOutReporter(True))
pop.add_reporter(neat.StatisticsReporter())
#pop.add_reporter(neat.Checkpointer(5))

#node_names = { -1:'Dist to pipe x', -2:'Dist to pipe bottom y', -3:'Dist to pipe top y', 0:'jump' }
#
#for genome in pop.population:
#	visualize.draw_net(config, genome, True, node_names=node_names)

from neat_manual_looping import *

generations = neat_manual_looping(pop)
generations.send(None)

def evolution_step(fitnesses=None):
	nns = []
	
	try:
		for genome_id, genome in generations.send(fitnesses):
			nn = neat.nn.FeedForwardNetwork.create(genome, config)

			nns.append(nn)
		return nns
	except Exception as ex:
		pass

def calc_fitness(score, dist_score, crashed, crash_near_hole_ratio):
	return	score * 10 + dist_score	\
			-crashed * 20 + crash_near_hole_ratio * 10
			#+random.uniform(-0.5,+0.5) # maybe actually make genomes not all identical ??
