import neat

from neat.reporting import ReporterSet
from neat.math_util import mean
from neat.six_util import iteritems, itervalues

# modified code from neat lib to allow for manual looping through generations
def neat_manual_looping(pop, generation_limit=None):
	if pop.config.no_fitness_termination and (generation_limit is None):
		raise RuntimeError("Cannot have no generational limit with no fitness termination")

	yield

	k = 0
	while generation_limit is None or k < generation_limit:
		k += 1

		pop.reporters.start_generation(pop.generation)

		genomes = list(iteritems(pop.population))

		finesses = yield genomes

		for (genome_id, genome), fitness in zip(genomes, finesses):
			genome.fitness = fitness

		# Gather and report statistics.
		best = None
		for g in itervalues(pop.population):
			if best is None or g.fitness > best.fitness:
				best = g
		pop.reporters.post_evaluate(pop.config, pop.population, pop.species, best)

		# Track the best genome ever seen.
		if pop.best_genome is None or best.fitness > pop.best_genome.fitness:
			pop.best_genome = best

		if not pop.config.no_fitness_termination:
			# End if the fitness threshold is reached.
			fv = pop.fitness_criterion(g.fitness for g in itervalues(pop.population))
			if fv >= pop.config.fitness_threshold:
				pop.reporters.found_solution(pop.config, pop.generation, best)
				break

		# Create the next generation from the current generation.
		pop.population = pop.reproduction.reproduce(pop.config, pop.species,
														pop.config.pop_size, pop.generation)

		# Check for complete extinction.
		if not pop.species.species:
			pop.reporters.complete_extinction()

			# If requested by the user, create a completely new population,
			# otherwise raise an exception.
			if pop.config.reset_on_extinction:
				pop.population = pop.reproduction.create_new(pop.config.genome_type,
																pop.config.genome_config,
																pop.config.pop_size)
			else:
				raise CompleteExtinctionException()

		# Divide the new population into species.
		pop.species.speciate(pop.config, pop.population, pop.generation)

		pop.reporters.end_generation(pop.config, pop.population, pop.species)

		pop.generation += 1

	if pop.config.no_fitness_termination:
		pop.reporters.found_solution(pop.config, pop.generation, pop.best_genome)

