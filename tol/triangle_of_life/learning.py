import trollius
from trollius import From, Return, Future
from Queue import Queue

# sdfbuilder
from sdfbuilder.math import Vector3
from sdfbuilder import Pose, Model, Link, SDF

# Revolve
from revolve.util import multi_future, wait_for
from revolve.angle import Tree
# ToL
from ..config import parser
from ..manage import World
from ..logging import logger, output_console
from . import Timers
from .encoding import Mutator, Crossover
from .convert import NeuralNetworkParser


class RobotLearner:

    # TODO self.produce_new_generation()
    # TODO neuron parameters mutation

    # TODO self.get_fitness()
    # TODO self.update_fitness()

    def __init__(self, world, robot, body_spec, brain_spec, mutator, population_size, evaluation_time, max_num_generations):
        self.robot = robot
        self.world = world
        self.active_brain = None
        self.innovation_number = 0
        self.fitness = 0
        self.pop_size = population_size
        self.evaluation_time = evaluation_time

        self.brain_spec = brain_spec
        self.body_spec = body_spec

        self.nn_parser = NeuralNetworkParser(brain_spec)
        self.mutator = mutator

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


    @trollius.coroutine
    def activate_brain(self, brain):
        print "activating brain now"
        self.active_brain = brain
        yield From(self.insert_brain(brain))


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


    @trollius.coroutine
    def insert_brain(self, brain_genotype):
        print "inserting brain now"
        pb_robot = self.robot.tree.to_robot()
        pb_body = pb_robot.body
        pb_brain = self.nn_parser.genotype_to_brain(brain_genotype)

        # delete robot with old brain:
        yield From(self.world.delete_robot(self.robot))

        # create and insert robot with new brain:
        tree = Tree.from_body_brain(pb_body, pb_brain, self.body_spec)
        pose = Pose(position=Vector3(0, 0, 0))
        self.robot = yield From(wait_for(self.world.insert_robot(tree, pose)))


    def reset_fitness(self):
        self.fitness = 0


    def update_fitness(self):
        self.fitness = 0


    def get_fitness(self):
        return self.fitness


    @trollius.coroutine
    def update(self):
        """
        this method should be called from the main loop
        it returns True if learning is over

        :return: bool
        """

        # when evaluation is over:
        if self.timers.is_it_time('evaluate', self.evaluation_time, self.world.last_time):

            print "Evaluation over"

            self.brain_fitness[self.active_brain] = self.get_fitness()
            self.reset_fitness()

            # if all brains are evaluated, produce new generation:
            if self.evaluation_queue.empty():
                self.produce_new_generation()
                self.generation_number += 1

            # else continue evaluating brains from the queue:
            else:
                print "loading new brain"
                next_brain = self.evaluation_queue.get()
                yield From(self.activate_brain(next_brain))

            self.timers.reset('evaluate', self.world.last_time)

        # continue evaluation:
        self.update_fitness()

        # if termination criteria are met, return True:
        if self.generation_number >= self.max_generations:
            raise Return(True)

        else:
            raise Return(False)


    def produce_new_generation(self):
        brain_fitness_list = [(br, fit) for br, fit in self.brain_fitness.iteritems()]
        best_brains = sorted(brain_fitness_list, key = lambda elem: elem[1], reverse = True)[:self.pop_size]



    # this method should be called when the learning is over to get a robot with the best brain
    def get_final_robot(self):
        brain_fitness_list = [(br, fit) for br, fit in self.brain_fitness.iteritems()]
        best_brain = sorted(brain_fitness_list, key = lambda elem: elem[1], reverse = True)[0]

        self.activate_brain(best_brain)
        return self.robot


    def robot_to_genotype(self, robot):
        pb_robot = robot.tree.to_robot()
        return self.nn_parser.brain_to_genotype(pb_robot.brain, self.mutator)
