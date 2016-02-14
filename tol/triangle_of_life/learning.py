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


# TODO implement insertion of a brain into a robot (convert genotype into protobuf brain and then create tree and insert robot into the world)

class RobotLearner:

    # TODO self.insert_brain(brain)
    # TODO self.produce_new_generation()

    # TODO self.get_fitness()
    # TODO self.update_fitness()

    def __init__(self, world, robot, mutator, nn_parser, population_size, max_num_generations):
        self.robot = robot
        self.world = world
        self.active_brain = None
        self.innovation_number = 0
        self.fitness = 0
        self.pop_size = population_size

        self.mutator = mutator
        self.nn_parser = nn_parser

        self.timers = Timers(['evaluate'], self.world.last_time)

        brain_population = self.get_init_brains()

        # FOR DEBUG
        ##########################################
        for br in brain_population:
            print "neurons:"
            n_gs, c_gs = br.to_lists()
            for n_g in n_gs:
                print n_g
            print "connections:"
            for c_g in c_gs:
                print c_g
            print ""
            print ""
        ##########################################


        self.evaluation_queue = Queue()

        for br in brain_population:
            self.evaluation_queue.put(br)

        self.brain_fitness = {}

        first_brain = self.evaluation_queue.get()
        self.activate_brain(first_brain)

        self.generation_number = 0
        self.max_generations = max_num_generations


    def activate_brain(self, brain):
        self.active_brain = brain
        self.insert_brain(brain)


    def get_init_brains(self):
        init_genotype = self.robot_to_genotype(self.robot)

        # FOR DEBUG
        #########################################
        print "initial brain:"

        n_gs, c_gs = init_genotype.to_lists()
        print "neurons:"
        for n_g in n_gs:
            print n_g
        print "connections:"
        for c_g in c_gs:
            print c_g
        print ""
        print ""
        ##########################################


        init_pop = []
        for _ in range(self.pop_size):
            mutated_genotype = init_genotype.copy()

            self.mutator.mutate_weights(genotype=mutated_genotype, probability=0.2, sigma=1)
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


    def robot_to_genotype(self, robot):
        pb_robot = robot.tree.to_robot()
        return self.nn_parser.robot_to_genotype(pb_robot, self.mutator)