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
from ..config import parser
from ..manage import World
from ..logging import logger, output_console
from . import Timers
from .encoding import Crossover, validate_genotype
from .convert import NeuralNetworkParser



class RobotLearner:

    # TODO: check correctness of fitness in gazebo (visually)

    def __init__(self, world, robot, body_spec, brain_spec, mutator,
                 population_size, tournament_size, evaluation_time, max_num_generations):
        self.robot = robot
        self.active_brain = None
        self.fitness = 0
        self.last_position = Vector3(0,0,0)

        self.pop_size = population_size
        self.tournament_size = tournament_size
        if self.tournament_size > self.pop_size:
            self.tournament_size = self.pop_size

        self.evaluation_time = evaluation_time

        self.brain_spec = brain_spec
        self.body_spec = body_spec

        self.nn_parser = NeuralNetworkParser(brain_spec)
        self.mutator = mutator

        self.timers = Timers(['evaluate'], world.last_time)
        self.evaluation_queue = deque()
        self.brain_fitness = {}
        self.generation_number = 0
        self.max_generations = max_num_generations

        self.total_brains_evaluated = 0


    @trollius.coroutine
    def initialize(self, world, data=None):

        # if we are not restoring:
        if data is None:
            brain_population = self.get_init_brains()
            for br in brain_population:
                validate_genotype(br, "initial generation created invalid genotype")
                self.evaluation_queue.append(br)

            first_brain = self.evaluation_queue.popleft()

            yield From(self.activate_brain(world, first_brain))
        # if we are restoring:
        else:
            self.unpack_data(data)
            yield From(self.activate_brain(world, data['active_brain']))




    @trollius.coroutine
    def activate_brain(self, world, brain):

        # pause world:
        yield From(world.pause(True))
        self.active_brain = brain
        yield From(self.insert_brain(world, brain))

        # unpause world:
        yield From(world.pause(False))


    def get_init_brains(self):
        init_genotype = self.robot_to_genotype(self.robot)

        init_pop = []
        for _ in range(self.pop_size):
            mutated_genotype = init_genotype.copy()

            self.mutator.mutate_weights(genotype=mutated_genotype, probability=0.2, sigma=1)

            self.mutator.mutate_neuron_params(genotype=mutated_genotype, probability=0.2)
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
        diff = abs(self.last_position - current_position)
        self.last_position = current_position
        self.fitness += diff


    def get_fitness(self):
        if abs(self.last_position - Vector3(0,0,0)) > 0.001:
            return self.fitness
        else:
            return 0
        


    @trollius.coroutine
    def update(self, world):
        """
        this method should be called from the main loop
        it returns True if learning is over

        :return: bool
        """

        # when evaluation is over:
        if self.timers.is_it_time('evaluate', self.evaluation_time, world.last_time):

            print "Evaluation over"
            self.total_brains_evaluated += 1

            print "%%%%%%%%%%%%%%%%%%\n\nEvaluated {0} brains".format(self.total_brains_evaluated)
            print "last evaluated: {0}".format(self.active_brain)
            print "queue length = {0}".format(len(self.evaluation_queue))
            print "fitness (distance covered): {0}\n\n%%%%%%%%%%%%%%%%%%".format(self.fitness )
            self.brain_fitness[self.active_brain] = self.get_fitness()
            self.reset_fitness()

            # # make snapshot (freezes when evaluation queue is empty:
            # yield From(world.create_snapshot())

            # if all brains are evaluated, produce new generation:
            if len(self.evaluation_queue) == 0:

                # this method fills the evaluation queue with new brains:
                self.produce_new_generation()
                self.generation_number += 1


            # continue evaluating brains from the queue:
            next_brain = self.evaluation_queue.popleft()
            yield From(self.activate_brain(world, next_brain))

            self.timers.reset('evaluate', world.last_time)

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

        parent_pairs = []
        # select parents:
        for _ in range(self.pop_size):
            selected = self.select_for_tournament(brain_fitness_list)

            parent_a = selected[0]
            parent_b = selected[1]

            # first in pair must be the best of two:
            parent_pairs.append((parent_a[0], parent_b[0]))

        for pair in parent_pairs:

            # apply crossover:
            print "applying crossover..."
            child_genotype = Crossover.crossover(pair[0], pair[1])
            validate_genotype(child_genotype, "crossover created invalid genotype")
            print "crossover successful"


            # apply mutations:

            print "applying weight mutations..."
            self.mutator.mutate_weights(genotype=child_genotype, probability=0.2, sigma=1)
            validate_genotype(child_genotype, "weight mutation created invalid genotype")
            print "weight mutation successful"


            print "applying neuron parameters mutations..."
            self.mutator.mutate_neuron_params(genotype=child_genotype, probability=0.2)
            validate_genotype(child_genotype, "neuron parameters mutation created invalid genotype")
            print "neuron parameters mutation successful"


            if random.random() < 1.0: # FOR DEBUG : increased probability of structural mutation
                print "applying structural mutation..."

                if len(child_genotype.connection_genes) == 0:
                    print "inserting new CONNECTION..."
                    self.mutator.add_connection_mutation(child_genotype, self.mutator.new_connection_sigma)
                    validate_genotype(child_genotype, "inserting new CONNECTION created invalid genotype")
                    print "inserting new CONNECTION successful"

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


            # self.mutator.mutate_structure(genotype=child_genotype, probability=0.1)

            # if validate_genotype(child_genotype, "structural mutation created invalid genotype"):
            #     print "structural mutation successful"

            self.evaluation_queue.append(child_genotype)


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


    # for pickling for snapshot:
    def pack_data(self):
        data = {}
        data['fitness'] = self.fitness
        data['population_size'] = self.pop_size
        data['tournament_size'] = self.tournament_size
        data['evaluation_time'] = self.evaluation_time
        data['generation_number'] = self.generation_number
        data['max_generations'] = self.max_generations

        data['robot'] = self.robot
        data['timers'] = self.timers

        data['brain_fitness'] = self.brain_fitness
        data['active_brain'] = self.active_brain

        data['evaluation_queue'] = self.evaluation_queue
        data['brains_evaluated'] = self.total_brains_evaluated
        data['last_position'] = self.last_position

        return data


    # for unpickling from snapshot:
    def unpack_data(self, data):
        self.robot = data['robot']
        self.fitness = data['fitness']
        self.pop_size = data['population_size']
        self.tournament_size = data['tournament_size']
        self.evaluation_time = data['evaluation_time']
        self.timers = data['timers']

        self.brain_fitness = data['brain_fitness']
        self.generation_number = data['generation_number']
        self.max_generations = data['max_generations']


        self.evaluation_queue = data['evaluation_queue']
        self.total_brains_evaluated = data['brains_evaluated']
        self.last_position = data['last_position']
