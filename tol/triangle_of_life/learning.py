import os
import trollius
from trollius import From, Return, Future
from collections import deque
import random

# sdfbuilder
from sdfbuilder.math import Vector3
from sdfbuilder import Pose, Model, Link, SDF

# Revolve
from revolve.util import multi_future, wait_for
from revolve.angle import Tree

# ToL
from . import Timers
from .encoding import Crossover, validate_genotype
from .convert import NeuralNetworkParser



class RobotLearner:

    def __init__(self, world, robot, body_spec, brain_spec, mutator,
                 population_size, tournament_size, num_children, evaluation_time,
                 evaluation_time_sigma,
                 weight_mutation_probability, weight_mutation_sigma,
                 param_mutation_probability, param_mutation_sigma,
                 structural_mutation_probability, max_num_generations):
        self.robot = robot
        self.active_brain = None
        self.fitness = 0
        self.last_position = Vector3(0,0,0)

        self.brain_spec = brain_spec
        self.body_spec = body_spec

        self.nn_parser = NeuralNetworkParser(brain_spec)
        self.mutator = mutator

 #       self.timers = Timers(['evaluate'], world.last_time)
        self.timers = Timers(['evaluate'], 0)
        self.evaluation_queue = deque()
        self.brain_fitness = {}
        self.generation_number = 0

        self.total_brains_evaluated = 0

        # experiment parameters:
        self.pop_size = population_size
        if self.pop_size < 2:
            self.pop_size = 2

        self.tournament_size = tournament_size
        if self.tournament_size > self.pop_size:
            self.tournament_size = self.pop_size
        if self.tournament_size < 2:
            self.tournament_size = 2

        self.num_children = num_children

        self.evaluation_time = evaluation_time
        self.evaluation_time_sigma = evaluation_time_sigma
        self.evaluation_time_actual = evaluation_time

        self.weight_mutation_probability = weight_mutation_probability
        self.weight_mutation_sigma = weight_mutation_sigma
        self.param_mutation_probability = param_mutation_probability
        self.param_mutation_sigma = param_mutation_sigma
        self.structural_mutation_probability = structural_mutation_probability
        self.max_generations = max_num_generations


    @trollius.coroutine
    def initialize(self, world):

        brain_population = self.get_init_brains()
        for br in brain_population:
            validate_genotype(br, "initial generation created invalid genotype")
            self.evaluation_queue.append(br)

        first_brain = self.evaluation_queue.popleft()

        yield From(self.activate_brain(world, first_brain))



    @trollius.coroutine
    def activate_brain(self, world, brain):

        # pause world:
        yield From(world.pause(True))
        yield From(self.insert_brain(world, brain))
        self.active_brain = brain
        # unpause world:
        yield From(world.pause(False))


    def get_init_brains(self):
        init_genotype = self.robot_to_genotype(self.robot)

        # FOR DEBUG
        ##########################################
        print "initial genotype:"
        print init_genotype.debug_string(True)
        ##########################################
        init_pop = []
        for _ in range(self.pop_size):
            mutated_genotype = init_genotype.copy()

            self.mutator.mutate_weights(
                genotype=mutated_genotype,
                probability=self.weight_mutation_probability,
                sigma=self.weight_mutation_sigma)

            self.mutator.mutate_neuron_params(
                genotype=mutated_genotype,
                probability=self.param_mutation_probability,
                sigma=self.param_mutation_sigma)

            init_pop.append(mutated_genotype)

        return init_pop


    @trollius.coroutine
    def insert_brain(self, world, brain_genotype):
        pb_robot = self.robot.tree.to_robot()
        pb_body = pb_robot.body
        pb_brain = self.nn_parser.genotype_to_brain(brain_genotype)

        # delete robot with old brain:
        yield From(world.delete_robot(self.robot))

        # create and insert robot with new brain:
        tree = Tree.from_body_brain(pb_body, pb_brain, self.body_spec)
        pose = Pose(position=Vector3(0, 0, 0))
        self.robot = yield From(wait_for(world.insert_robot(tree, pose)))
        yield From(world.pause(False))


    def reset_fitness(self):
        self.last_position = Vector3(0,0,0)
        self.fitness = 0


    def update_fitness(self):
        current_position = self.robot.last_position
        # diff = abs(self.last_position - current_position)
        # self.last_position = current_position
        # self.fitness += diff

        displacement = abs(Vector3(0,0,0) - current_position)
        self.fitness = displacement


    def get_fitness(self):
        # if abs(self.last_position - Vector3(0,0,0)) > 0.001:
        #     return self.fitness
        # else:
        #     return 0
        return self.fitness
        


    @trollius.coroutine
    def update(self, world):
        """
        this method should be called from the main loop
        it returns True if learning is over

        :return: bool
        """

        # # FOR DEBUG
        # ################################################
        # print "world time: " + str(world.last_time)
        # print "timer time: " + str(self.timers.get_last_time('evaluate'))
        # ################################################



        # when evaluation is over:
        if self.timers.is_it_time('evaluate', self.evaluation_time_actual, world.last_time):


            # # FOR DEBUG
            # ################################################
            # print "world time: " + str(world.last_time)
            # print "timer time: " + str(self.timers.get_last_time('evaluate'))
            # ################################################


            print "Evaluation over"
            self.total_brains_evaluated += 1

            print "%%%%%%%%%%%%%%%%%%\n\nEvaluated {0} brains".format(self.total_brains_evaluated)
            print "last evaluated: {0}".format(self.active_brain)
            print "queue length = {0}".format(len(self.evaluation_queue))
            print "fitness (distance covered): {0}".format(self.fitness )
            print "evaluation time was {0}s".format(self.evaluation_time_actual)
            print "simulation time: {0}\n\n%%%%%%%%%%%%%%%%%%".format(world.last_time)

            self.brain_fitness[self.active_brain] = self.get_fitness() / self.evaluation_time_actual

            # make snapshot (freezes when evaluation queue is empty:
            yield From(world.create_snapshot())

            # if all brains are evaluated, produce new generation:
            if len(self.evaluation_queue) == 0:

                # this method fills the evaluation queue with new brains:
                self.produce_new_generation()
                self.generation_number += 1

            # continue evaluating brains from the queue:
            next_brain = self.evaluation_queue[0]
            yield From(self.activate_brain(world, next_brain))

            self.evaluation_queue.popleft()

            self.timers.reset('evaluate', world.last_time)

            self.reset_fitness()
            # randomize evaluation time:
            self.evaluation_time_actual = self.evaluation_time + \
                        random.gauss(0, self.evaluation_time_sigma)

            if self.evaluation_time_actual < 0:
                self.evaluation_time_actual = 0.5


        # continue evaluation:
        self.update_fitness()

        # if termination criteria are met, return True:
        if self.generation_number >= self.max_generations:
            raise Return(True)

        else:
            raise Return(False)


    def produce_new_generation(self):
        brain_fitness_list = [(br, fit) for br, fit in self.brain_fitness.items()]
        # do not store information about old generations:
        self.brain_fitness.clear()

        # sort parents from best to worst:
        brain_fitness_list = sorted(brain_fitness_list, key = lambda elem: elem[1], reverse=True)

        # select the best ones:
        brain_fitness_list_best = [brain_fitness_list[i] for i in range(self.pop_size - self.num_children)]

        parent_pairs = []

        # create children:
        for _ in range(self.num_children):

            # select for tournament only from the best parents:
            selected = self.select_for_tournament(brain_fitness_list_best)

            # # OR

            # # select for tournament from all parents:
            # selected = self.select_for_tournament(brain_fitness_list)


            # select 2 best parents from the tournament:
            parent_a = selected[0]
            parent_b = selected[1]

            # first in pair must be the best of two:
            parent_pairs.append((parent_a, parent_b))

        log_file_path = os.path.dirname(os.path.abspath(__file__))+'/../../scripts/learning-test/genotypes.log'

        genotype_log_file = open(log_file_path, "a")
        for i, pair in enumerate(parent_pairs):

            print "\nchild #{0}\nSELECTED PARENTS:".format(str(i+1))
            print str(pair[0][0]) + ", fitness = " + str(pair[0][1])
            print str(pair[1][0]) + ", fitness = " + str(pair[1][1])

            # genotype_log_file.write(pair[0][0].debug_string(True))
            # genotype_log_file.write("\nfitness = " + str(pair[0][1]) + "\n\n")
            #
            # genotype_log_file.write(pair[1][0].debug_string(True))
            # genotype_log_file.write("\nfitness = " + str(pair[1][1]) + "\n\n")

            # apply crossover:
            print "applying crossover..."
            child_genotype = Crossover.crossover(pair[0][0], pair[1][0])
            validate_genotype(child_genotype, "crossover created invalid genotype")
            print "crossover successful"


            # apply mutations:

            print "applying weight mutations..."
            self.mutator.mutate_weights(
                genotype=child_genotype,
                probability=self.weight_mutation_probability,
                sigma=self.weight_mutation_sigma)
            validate_genotype(child_genotype, "weight mutation created invalid genotype")
            print "weight mutation successful"


            print "applying neuron parameters mutations..."
            self.mutator.mutate_neuron_params(
                genotype=child_genotype,
                probability=self.param_mutation_probability,
                sigma=self.param_mutation_sigma)
            validate_genotype(child_genotype, "neuron parameters mutation created invalid genotype")
            print "neuron parameters mutation successful"


            # apply structural mutations:
            if random.random() < self.structural_mutation_probability:
                print "applying structural mutation..."

                # if no connections, add connection
                if len(child_genotype.connection_genes) == 0:
                    print "inserting new CONNECTION..."
                    self.mutator.add_connection_mutation(child_genotype, self.mutator.new_connection_sigma)
                    validate_genotype(child_genotype, "inserting new CONNECTION created invalid genotype")
                    print "inserting new CONNECTION successful"

                # otherwise add connection or neuron with equal probability
                else:
                    if random.random() < 0.5:
                        print "inserting new CONNECTION..."
                        self.mutator.add_connection_mutation(child_genotype, self.mutator.new_connection_sigma)
                        validate_genotype(child_genotype, "inserting new CONNECTION created invalid genotype")
                        print "inserting new CONNECTION successful"

                    else:
                        print "inserting new NEURON..."
                        self.mutator.add_neuron_mutation(child_genotype)
                        validate_genotype(child_genotype, "inserting new NEURON created invalid genotype")
                        print "inserting new NEURON successful"

            self.evaluation_queue.append(child_genotype)


        # bringing the best parents into next generation:
        for i in range(self.pop_size - self.num_children):
            print "saving parent #{0}, fitness = {1}".format(str(i+1), brain_fitness_list_best[i][1])
            self.evaluation_queue.append(brain_fitness_list_best[i][0])

        # Log best 3 genotypes in this generation:
        genotype_log_file.write("generation #{0}\n".format(self.generation_number))
        for i in range(3):
            genotype_log_file.write("fitness = {0}\n".format(brain_fitness_list[i][1]))
            genotype_log_file.write(brain_fitness_list[i][0].to_yaml())
            genotype_log_file.write("\n")

        genotype_log_file.close()


    def select_for_tournament(self, candidates):

        selected = sorted(random.sample(candidates, self.tournament_size), key = lambda elem: elem[1], reverse=True)
        return selected


    # this method should be called when the learning is over to get a robot with the best brain
    def get_final_robot(self, world):
        brain_fitness_list = [(br, fit) for br, fit in self.brain_fitness.iteritems()]
        best_brain = sorted(brain_fitness_list, key = lambda elem: elem[1], reverse = True)[0]

        self.activate_brain(world, best_brain)
        return self.robot


    def robot_to_genotype(self, robot):
        pb_robot = robot.tree.to_robot()
        return self.nn_parser.brain_to_genotype(pb_robot.brain, self.mutator)
