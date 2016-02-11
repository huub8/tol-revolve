import math
import random
import trollius
from trollius import From, Return, Future
from Queue import Queue

# Revolve / sdfbuilder
from sdfbuilder.math import Vector3
from sdfbuilder import Pose, Model, Link, SDF

# ToL
from ..config import parser
from ..manage import World
from . import Timers
from ..logging import logger, output_console
from revolve.util import multi_future



# TODO mutate_weights(genotype)
# TODO robot_to_genotype(robot)

# TODO implement brain genetic encoding
# TODO implement conversion from Tree to brain genetic encoding
# TODO implement insertion of a brain into a robot

class RobotLearner:

    # TODO self.insert_brain(brain)
    # TODO self.produce_new_generation()

    # TODO self.get_fitness()
    # TODO self.update_fitness()

    def __init__(self ,world, population, robot, population_size, max_num_generations):
        self.robot = robot
        self.world = world
        self.population = population
        self.active_brain = None
        self.innovation_number = 0
        self.fitness = 0

        self.timers = Timers(['evaluate'], self.world.last_time)

        brain_population = get_init_brains()

        self.evaluation_queue = Queue()

        for br in brain_population:
            self.evaluation_queue.put(br)

        self.brain_fitness = {}

        self.pop_size = population_size

        first_brain = self.evaluation_queue.get()
        self.activate_brain(first_brain)

        self.generation_number = 0
        self.max_generations = max_num_generations


    def activate_brain(self, brain):
        self.active_brain = brain
        self.insert_brain(brain)


    def get_init_brains(self):
        init_genotype = robot_to_genotype(self.robot)

        init_pop = []
        for _ in range(self.pop_size):
            mutated_genotype = mutate_weights(init_genotype)
            init_pop.append(mutated_genotype)

        return init_pop


    def reset_fitness(self):
        self.fitness = 0


    # this method should be called from the main loop
    # it returns True if learning is over
    def update(self):

        # when evaluation is over:
        if self.timers.is_it_time('evaluate', self.evaluation_time, self.world.last_time):

            self.brain_fitness[self.active_brain] = self.get_fitness()
            self.reset_fitness()

            # if all brains are evaluated, produce new generation:
            if self.evaluation_queue.empty():
                self.produce_new_generation()
                self.generation_number += 1

            # else continue evaluating brains from the queue:
            else:
                next_brain = self.evaluation_queue.get()
                self.activate_brain(next_brain)

            self.timers.reset('evaluate', self.world.last_time)

        # continue evaluation:
        self.update_fitness()

        # if termination criteria is met, return True:
        if self.generation_number >= self.max_generations:
            return True

        else:
            return False


    # this method should be called when the learning is over to get a robot with the best brain
    def get_final_robot(self):
        brain_fitness_list = [(br, fit) for br, fit in self.brain_fitness.iteritems()]
        best_brain = sorted(brain_fitness_list, key = lambda elem: elem[1], reverse = True)[0]

        self.activate_brain(best_brain)
        return self.robot
