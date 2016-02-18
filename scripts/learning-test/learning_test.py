import random
import os
import sys
import logging
import argparse
import math
import csv
import logging
import shutil

from revolve.build.util import in_cm, in_mm
from revolve.util import Time

from pygazebo.pygazebo import DisconnectError
from trollius.py33_exceptions import ConnectionResetError, ConnectionRefusedError

# Add "tol" directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__))+'/../')

# Trollius / Pygazebo
import trollius
from trollius import From, Return, Future
from pygazebo.msg.request_pb2 import Request

# sdfbuilder
from sdfbuilder.math import Vector3
from sdfbuilder import Pose, Model, Link, SDF

# Revolve
from revolve.util import multi_future, wait_for
from revolve.convert.yaml import yaml_to_robot
from revolve.angle import Tree

#ToL
from tol.config import parser
from tol.manage import World
from tol.logging import logger, output_console
from tol.spec import get_body_spec, get_brain_spec
from tol.triangle_of_life import RobotLearner
from tol.triangle_of_life.encoding import Mutator, Crossover
from tol.triangle_of_life.convert import NeuralNetworkParser



# Log output to console
output_console()
logger.setLevel(logging.DEBUG)

parent_color = (1, 0, 0, 0.5)
child_color = (0, 1, 0, 0.5)


# braim population size:
pop_size = 10


spider_yaml = '''
---
body:
  id          : Core
  type        : Core
  children:
    0:
      id: Brick11
      type: FixedBrick
      children:
        1:
          id: Hinge11
          type: ActiveHinge
          children:
            1:
              id: Hinge12
              type: ActiveHinge
    1:
      id: Brick21
      type: FixedBrick
      children:
        1:
          id: Hinge21
          type: ActiveHinge
          children:
            1:
              id: Hinge22
              type: ActiveHinge
    2:
      id: Brick31
      type: FixedBrick
      children:
        1:
          id: Hinge31
          type: ActiveHinge
          children:
            1:
              id: Hinge32
              type: ActiveHinge
    3:
      id: Brick41
      type: FixedBrick
      children:
        1:
          id: Hinge41
          type: ActiveHinge
          children:
            1:
              id: Hinge42
              type: ActiveHinge

'''

snake_yaml = '''
---
body:
  id          : Core
  type        : Core
  children:
    0:
      id: Hinge11
      type: FixedBrick
      children:
        1:
          id: Hinge12
          type: ActiveHinge
          children:
            1:
              id: Hinge13
              type: ActiveHinge
              children:
                1:
                  id: Hinge14
                  type: ActiveHinge
                  children:
                    1:
                      id: Hinge15
                      type: ActiveHinge
    1:
      id: Hinge21
      type: FixedBrick
      children:
        1:
          id: Hinge22
          type: ActiveHinge
          children:
            1:
              id: Hinge23
              type: ActiveHinge
              children:
                1:
                  id: Hinge24
                  type: ActiveHinge
                  children:
                    1:
                      id: Hinge25
                      type: ActiveHinge

'''


class LearningManager(World):
    def __init__(self, conf, _private):
        super(LearningManager, self).__init__(conf, _private)

        self.fitness_filename = None
        self.fitness_file = None
        self.write_fitness = None
        self.learner_list = []

        if self.output_directory:
            self.fitness_filename = os.path.join(self.output_directory, 'fitness.csv')

            if self.do_restore:
                shutil.copy(self.fitness_filename + '.snapshot', self.fitness_filename)
                self.fitness_file = open(self.fitness_filename, 'ab', buffering=1)
                self.write_fitness = csv.writer(self.fitness_file, delimiter=',')
            else:
                self.fitness_file = open(self.fitness_filename, 'wb', buffering=1)
                self.write_fitness = csv.writer(self.fitness_file, delimiter=',')
                self.write_fitness.writerow(['t_sim', 'robot_id', 'age', 'displacement',
                                             'vel', 'dvel', 'fitness'])


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
        Copy the fitness file in the snapshot
        :return:
        """
        ret = yield From(super(LearningManager, self).create_snapshot())
        if not ret:
            raise Return(ret)

        self.fitness_file.flush()
        shutil.copy(self.fitness_filename, self.fitness_filename + '.snapshot')


    @trollius.coroutine
    def get_snapshot_data(self):
        data = yield From(super(LearningManager, self).get_snapshot_data())
        data['learners'] = self.learner_list
        raise Return(data)


    def restore_snapshot(self, data):
        yield From(super(LearningManager, self).restore_snapshot(data))
        self.learner_list = data['learners']


    def add_learner(self, learner):
        self.learner_list.append(learner)


    @trollius.coroutine
    def run(self, conf):

        yield From(self.pause(False))

        if not self.do_restore:
            bot_yaml = spider_yaml

            body_spec = get_body_spec(conf)
            brain_spec = get_brain_spec(conf)

            mutator = Mutator()
            pose = Pose(position=Vector3(0, 0, 0))

            bot = yaml_to_robot(body_spec, brain_spec, bot_yaml)
            tree = Tree.from_body_brain(bot.body, bot.brain, body_spec)

            robot = yield From(wait_for(self.insert_robot(tree, pose)))

            print("new robot id = %d" % robot.robot.id)

            learner = RobotLearner(world=self,
                                   robot=robot,
                                   body_spec=body_spec,
                                   brain_spec=brain_spec,
                                   mutator=mutator,
                                   population_size=pop_size,
                                   evaluation_time=10, # simulation seconds
                                   max_num_generations=1000)

            # add callback for finished evaluation (not sure if this will work):
            learner.on_evaluation_finished = self.create_snapshot()
            self.add_learner(learner)
        else:
            print "WORLD RESTORED FROM {0}".format(self.world_snapshot_filename)
            print "STATE RESTORED FROM {0}".format(self.snapshot_filename)


        # Request callback for the subscriber
        def callback(data):
            req = Request()
            req.ParseFromString(data)

        subscriber = self.manager.subscribe(
            '/gazebo/default/request', 'gazebo.msgs.Request', callback)
        yield From(subscriber.wait_for_connection())

        # run loop:
        while True:
            for learner in self.learner_list:
                result = yield From(learner.update())



@trollius.coroutine
def run():
    conf = parser.parse_args()
    conf.min_parts = 1
    conf.max_parts = 3
    conf.arena_size = (3, 3)
    conf.max_lifetime = 99999
    conf.initial_age_mu = 99999
    conf.initial_age_sigma = 1
    conf.age_cutoff = 99999
    conf.pose_update_frequency = 20

    world = yield From(LearningManager.create(conf))

    print "WORLD CREATED"
    yield From(world.run(conf))




def main():

    print "START"

    def handler(loop, context):
        exc = context['exception']
        if isinstance(exc, DisconnectError) or isinstance(exc, ConnectionResetError):
            print("Got disconnect / connection reset - shutting down.")
            sys.exit(0)

        raise context['exception']

    try:
        loop = trollius.get_event_loop()
        loop.set_debug(enabled=True)
#        logging.basicConfig(level=logging.DEBUG)
        loop.set_exception_handler(handler)
        loop.run_until_complete(run())
        print "FINISH"

    except KeyboardInterrupt:
        print("Got Ctrl+C, shutting down.")
    except ConnectionRefusedError:
        print("Connection refused, are the world and the analyzer loaded?")

if __name__ == '__main__':
    main()
