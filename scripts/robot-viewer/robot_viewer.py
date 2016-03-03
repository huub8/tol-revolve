import os
import sys
import csv
import logging
import shutil

from pygazebo.pygazebo import DisconnectError
from trollius.py33_exceptions import ConnectionResetError, ConnectionRefusedError

# Add "tol" directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__))+'/../../')

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
from tol.triangle_of_life.convert import NeuralNetworkParser, yaml_to_genotype


# Log output to console
output_console()
logger.setLevel(logging.DEBUG)


parser.add_argument(
    '--robot-file',
    type=str,
    help="path to YAML file containing robot morphology"
)

parser.add_argument(
    '--genotype-file',
    type=str,
    default=None,
    help="path to YAML file containing brain genotype"
)



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

    body_spec = get_body_spec(conf)
    brain_spec = get_brain_spec(conf)


    print "OPENING FILES!!!!!!!!!!!!!!!!!!!"
    with open(conf.robot_file,'r') as robot_file:
        bot_yaml = robot_file.read()

    genotype_yaml = None

    # if brain genotype file exists:
    if conf.genotype_file != '':
        with open (conf.genotype_file, 'r') as gen_file:
            genotype_yaml = gen_file.read()

    print "CREATING WORLD!!!!!!!!!!!!!!!!!!!"
    world = yield From(World.create(conf))
    yield From(world.pause(True))

    pose = Pose(position=Vector3(0, 0, 0))

    # if brain genotype is given, combine body and brain:
    if genotype_yaml:
        # convert YAML stream to protobuf body:
        robot_body_pb = yaml_to_robot(body_spec, brain_spec, bot_yaml).body

        # convert YAML stream to genotype:
        robot_brain_genotype = yaml_to_genotype(genotype_yaml, brain_spec)

        # convert genotype to protobuf brain:
        nn_parser = NeuralNetworkParser(brain_spec)
        robot_brain_pb = nn_parser.genotype_to_brain(robot_brain_genotype)

        tree = Tree.from_body_brain(robot_body_pb, robot_brain_pb, body_spec)


    # if brain genotype is not given, just insert the body:
    else:
         # convert YAML stream to protobuf robot:
        robot_pb = yaml_to_robot(body_spec, brain_spec, bot_yaml)
        tree = Tree.from_body_brain(robot_pb.body, robot_pb.brain, body_spec)


    print "INSERTING ROBOT!!!!!!!!!!!!!!!!!!!!!!"
    robot = yield From(wait_for(world.insert_robot(tree, pose)))
    yield From(world.pause(False))

    while (True):
        continue



def main():
    print "START"

    def handler(loop, context):
        exc = context['exception']
        if isinstance(exc, DisconnectError) or isinstance(exc, ConnectionResetError):
            print("Got disconnect / connection reset - shutting down.")
            sys.exit(1)

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
