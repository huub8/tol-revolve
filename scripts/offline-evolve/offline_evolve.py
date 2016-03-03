# Offline evolution scheme
# - We use a population of constant size 10
# - Each robot is evaluated for 20 seconds, though we may vary this number
# - The average speed during this evaluation is the fitness
# - We do parent selection using a binary tournament: select two parents at
#   random, the one with the best fitness is parent 1, repeat for parent 2.
# - Using this mechanism, we generate 10 children
# - After evaluation of the children, we either do:
# -- Plus scheme, sort *all* robots by fitness
# -- Comma scheme, get rid of the parents and continue with children only
from __future__ import absolute_import
import sys
import time
import os
import shutil
import random
import csv
import itertools
import logging
import trollius
from trollius import From, Return

from sdfbuilder import Pose
from sdfbuilder.math import Vector3

from revolve.util import wait_for

from tol.manage.robot import Robot
from tol.config import parser
from tol.manage import World
from tol.logging import logger, output_console

# Log output to console
output_console()
logger.setLevel(logging.DEBUG)

# Add offline evolve arguments
parser.add_argument(
    '--population-size',
    default=10, type=int,
    help="Population size in each generation."
)

parser.add_argument(
    '--num-children',
    default=10, type=int,
    help="The number of children produced in each generation."
)

parser.add_argument(
    '--keep-parents',
    default=True, type=lambda v: v.lower() == "true" or v == "1",
    help="Whether or not to discard the parents after each generation. This determines the strategy, + or ,."
)

parser.add_argument(
    '--num-generations',
    default=60, type=int,
    help="The number of generations to simulate."
)

parser.add_argument(
    '--disable-evolution',
    default=False, type=lambda v: v.lower() == "true" or v == "1",
    help="Useful as a baseline test - if set to true, new robots are generated"
         " every time rather than evolving them."
)

parser.add_argument(
    '--num-evolutions',
    default=8, type=int,
    help="The number of times to repeat the experiment."
)

parser.add_argument(
    '--max-mating-attempts',
    default=5, type=int,
    help="Maximum number of mating attempts between two parents."
)

parser.add_argument(
    '--evaluation-threshold',
    default=5.0, type=float,
    help="Maximum number of seconds one evaluation can take before the "
         "decision is made to restart from snapshot. The assumption is "
         "that the world may have become slow and restarting will help."
)


class OfflineEvoManager(World):
    """
    Extended world manager for the offline evolution script
    """
    def __init__(self, conf, _private):
        """

        :param conf:
        :param _private:
        :return:
        """
        super(OfflineEvoManager, self).__init__(conf, _private)

        self.generations_filename = None
        self.generations_file = None
        self.write_generations = None

        self._snapshot_data = {}

        if self.output_directory:
            self.generations_filename = os.path.join(self.output_directory, 'generations.csv')

            if self.do_restore:
                shutil.copy(self.generations_filename+'.snapshot', self.generations_filename)
                self.generations_file = open(self.generations_filename, 'ab', buffering=1)
                self.write_generations = csv.writer(self.generations_file, delimiter=',')
            else:
                self.generations_file = open(self.generations_filename, 'wb', buffering=1)
                self.write_generations = csv.writer(self.generations_file, delimiter=',')
                self.write_generations.writerow(['run', 'gen', 'robot_id', 'vel', 'dvel', 'fitness', 't_eval'])

    def robots_header(self):
        return Robot.header()

    @classmethod
    @trollius.coroutine
    def create(cls, conf):
        """
        Coroutine to instantiate a Revolve.Angle WorldManager
        :param conf:
        :return:
        """
        self = cls(_private=cls._PRIVATE, conf=conf)
        yield From(self._init())
        raise Return(self)

    @trollius.coroutine
    def create_snapshot(self):
        """
        Copy the generations file in the snapshot
        :return:
        """
        ret = yield From(super(OfflineEvoManager, self).create_snapshot())
        if not ret:
            raise Return(ret)

        self.generations_file.flush()
        shutil.copy(self.generations_filename, self.generations_filename+'.snapshot')

    @trollius.coroutine
    def get_snapshot_data(self):
        """
        :return:
        """
        data = yield From(super(OfflineEvoManager, self).get_snapshot_data())
        data.update(self._snapshot_data)
        raise Return(data)

    @trollius.coroutine
    def evaluate_pair(self, tree, bbox, parents=None):
        """
        Evaluates a single robot tree.
        :param tree:
        :param bbox:
        :param parents:
        :return: Evaluated Robot object
        """
        # Pause the world just in case it wasn't already
        yield From(wait_for(self.pause(True)))

        pose = Pose(position=Vector3(0, 0, -bbox.min.z))
        fut = yield From(self.insert_robot(tree, pose, parents))
        robot = yield From(fut)

        max_age = self.conf.evaluation_time + self.conf.warmup_time

        # Unpause the world to start evaluation
        yield From(wait_for(self.pause(False)))

        before = time.time()

        while True:
            if robot.age() >= max_age:
                break

            # Sleep for the pose update frequency, which is about when
            # we expect a new age update.
            yield From(trollius.sleep(1.0 / self.pose_update_frequency))

        yield From(wait_for(self.delete_robot(robot)))
        yield From(wait_for(self.pause(True)))

        diff = time.time() - before
        if diff > self.conf.evaluation_threshold:
            sys.stderr.write("Evaluation threshold exceeded, shutting down with nonzero status code.\n")
            sys.exit(1)

        raise Return(robot)

    @trollius.coroutine
    def evaluate_population(self, trees, bboxes, parents=None):
        """
        :param trees:
        :param bboxes:
        :param parents:
        :return:
        """
        if parents is None:
            parents = [None for _ in trees]

        pairs = []
        print("Evaluating population...")
        for tree, bbox, par in itertools.izip(trees, bboxes, parents):
            print("Evaluating individual...")
            before = time.time()
            robot = yield From(self.evaluate_pair(tree, bbox, par))
            pairs.append((robot, time.time() - before))
            print("Done.")

        print("Done evaluating population.")
        raise Return(pairs)

    @trollius.coroutine
    def produce_generation(self, parents):
        """
        Produce the next generation of robots from
        the current.
        :param parents:
        :return:
        """
        print("Producing generation...")
        trees = []
        bboxes = []
        parent_pairs = []

        while len(trees) < self.conf.num_children:
            print("Producing individual...")
            p1, p2 = select_parents(parents)

            for j in xrange(self.conf.max_mating_attempts):
                pair = yield From(self.attempt_mate(p1, p2))
                if pair:
                    trees.append(pair[0])
                    bboxes.append(pair[1])
                    parent_pairs.append((p1, p2))
                    break

            print("Done.")

        print("Done producing generation.")
        raise Return(trees, bboxes, parent_pairs)

    def log_generation(self, evo, generation, pairs):
        """
        :param evo: The evolution run
        :param generation:
        :param pairs: List of tuples (robot, evaluation wallclock time)
        :return:
        """
        print("================== GENERATION %d ==================" % generation)
        if not self.generations_file:
            return

        for robot, t_eval in pairs:
            self.write_generations.writerow([evo, generation, robot.robot.id, robot.velocity(),
                                             robot.displacement_velocity(), robot.fitness(), t_eval])

    @trollius.coroutine
    def run(self):
        """
        :return:
        """
        conf = self.conf

        if self.do_restore:
            # Recover from a previously cancelled / crashed experiment
            data = self.do_restore
            evo_start = data['evo_start']
            gen_start = data['gen_start']
            pairs = data['local_pairs']
        else:
            # Start at the first experiment
            evo_start = 1
            gen_start = 1
            pairs = None

        for evo in range(evo_start, conf.num_evolutions + 1):
            if not pairs:
                # Only create initial population if we are not restoring from
                # a previous experiment.
                trees, bboxes = yield From(self.generate_population(conf.population_size))
                pairs = yield From(self.evaluate_population(trees, bboxes))
                self.log_generation(evo, 0, pairs)

            for generation in xrange(gen_start, conf.num_generations):
                if (generation % 5) == 0:
                    # Snapshot every 2 generations
                    self._snapshot_data = {
                        "local_pairs": pairs,
                        "gen_start": generation,
                        "evo_start": evo
                    }
                    yield From(self.create_snapshot())
                    print("Created snapshot of experiment state.")

                # Produce the next generation and evaluate them
                robots = [p[0] for p in pairs]
                if conf.disable_evolution:
                    child_trees, child_bboxes = yield From(
                        self.generate_population(conf.population_size))
                    parent_pairs = None
                else:
                    child_trees, child_bboxes, parent_pairs = yield From(self.produce_generation(robots))

                child_pairs = yield From(self.evaluate_population(child_trees, child_bboxes, parent_pairs))

                if conf.keep_parents:
                    pairs += child_pairs
                else:
                    pairs = child_pairs

                # Sort the bots and reduce to population size
                pairs = sorted(pairs, key=lambda r: r[0].fitness(), reverse=True)[:conf.population_size]
                self.log_generation(evo, generation, pairs)

            # Clear "restore" parameters
            gen_start = 1
            pairs = None

        yield From(self.teardown())

    @trollius.coroutine
    def teardown(self):
        """
        :return:
        """
        yield From(super(OfflineEvoManager, self).teardown())
        if self.generations_file:
            self.generations_file.close()


def select_parent(parents):
    """
    Select a parent using a binary tournament.
    :param parents:
    :return:
    """
    p = random.sample(parents, 2)
    return p[0] if p[0].velocity() > p[1].velocity() else p[1]


def select_parents(parents):
    """
    :param parents:
    :return:
    """
    p1 = select_parent(parents)
    p2 = p1
    while p2 == p1:
        p2 = select_parent(parents)

    return p1, p2


@trollius.coroutine
def run():
    """
    :return:
    """
    conf = parser.parse_args()
    world = yield From(OfflineEvoManager.create(conf))
    yield From(world.run())


def main():
    try:
        loop = trollius.get_event_loop()
        loop.run_until_complete(run())
    except KeyboardInterrupt:
        print("Got Ctrl+C, shutting down.")


if __name__ == '__main__':
    main()
