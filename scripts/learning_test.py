import random
import os
import sys
import logging
import argparse
import math

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


parser.add_argument("-s", "--seed", default=-1, help="Supply a random seed", type=int)
parser.add_argument("-n", "--num-initial-bots", default=3,
                    help="Number of initial bots", type=int)
parser.add_argument("-f", "--fast", help="Short reproduction wait.",
                    action="store_true")

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

@trollius.coroutine
def run_server(conf):
    """

    :param args:
    :return:
    """
 #   conf.proposal_threshold = 0
 #   conf.output_directory = None
    conf.min_parts = 1
    conf.max_parts = 3
    conf.arena_size = (3, 3)
    conf.max_lifetime = 99999
    conf.initial_age_mu = 99999
    conf.initial_age_sigma = 1
    conf.age_cutoff = 99999

    conf.pose_update_frequency = 20


    # initialize world:
    world = yield From(World.create(conf))
    yield From(world.pause(False))

    bot_yaml = spider_yaml

    print "WORLD CREATED"

    body_spec = get_body_spec(conf)
    brain_spec = get_brain_spec(conf)

    mutator = Mutator()
    pose = Pose(position=Vector3(0, 0, 0))

    bot = yaml_to_robot(body_spec, brain_spec, bot_yaml)
    tree = Tree.from_body_brain(bot.body, bot.brain, body_spec)

    robot = yield From(wait_for(world.insert_robot(tree, pose)))

    print("new robot id = %d" %robot.robot.id)

    learner = RobotLearner(world=world,
                           robot=robot,
                           body_spec=body_spec,
                           brain_spec=brain_spec,
                           mutator=mutator,
                           population_size=pop_size,
                           evaluation_time=10, # simulation seconds
                           max_num_generations=1000)

    # Request callback for the subscriber
    def callback(data):
        req = Request()
        req.ParseFromString(data)


    subscriber = world.manager.subscribe(
        '/gazebo/default/request', 'gazebo.msgs.Request', callback)
    yield From(subscriber.wait_for_connection())




    deltaT = 0.01

    # run loop:
    while not learner.update():

        yield From(trollius.sleep(deltaT))



def main():

    print "START"

    args = parser.parse_args()
    seed = random.randint(1, 1000000) if args.seed < 0 else args.seed
    random.seed(seed)
    print("Seed: %d" % seed)

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
        loop.run_until_complete(run_server(args))

        # run = run_server(args)
        # run.next()
        # while True:
        #     run.next()

        print "FINISH"

    except KeyboardInterrupt:
        print("Got Ctrl+C, shutting down.")
    except ConnectionRefusedError:
        print("Connection refused, are the world and the analyzer loaded?")

if __name__ == '__main__':
    main()
