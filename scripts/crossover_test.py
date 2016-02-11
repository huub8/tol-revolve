import random
import os
import sys
import logging
import argparse
import math


# Add "tol" directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__))+'/../')

sys.path.append(os.path.dirname(os.path.abspath(__file__))+'/../../sdf-builder')

sys.path.append(os.path.dirname(os.path.abspath(__file__))+'/../../revolve')




# Trollius / Pygazebo
import trollius
from trollius import From, Return, Future
from pygazebo.msg.request_pb2 import Request

# Revolve / sdfbuilder
from sdfbuilder.math import Vector3
from sdfbuilder import Pose, Model, Link, SDF

# ToL
from tol.config import parser
from tol.manage import World
from tol.logging import logger, output_console
from revolve.util import multi_future

# Revolve / Angle
from revolve.angle.manage import Robot

# Log output to console
output_console()
logger.setLevel(logging.DEBUG)


init_pop_size = 10


@trollius.coroutine
def do_mate(world, ra, rb):
    """
    :param world:
    :param ra:
    :param rb:
    :return:
    """
    mate = None
    num_attempts = 0
    while num_attempts < 10:
        # Attempt reproduction
        mate = yield From(world.attempt_mate(ra, rb))

        if mate:
            break
        num_attempts += 1

#    logger.debug("Mates selected, highlighting points...")

    new_pos = pick_position()
    new_pos.z = insert_z
#    hls = yield From(create_highlights(
#        world, ra.last_position, rb.last_position, new_pos))
#    yield From(trollius.sleep(2))
    if mate:
        logger.debug("Inserting child...")
        child, bbox = mate
        pose = Pose(position=new_pos)
        spawn_robot(world, tree=child, pose=pose, parents=[ra, rb])
    else:
        logger.debug("Could not mate")



def spawn_robot(world, tree, pose, parents=None):
    robot_id = world.get_robot_id()
    position = pose.position
    robot = tree.to_robot(robot_id)
    if parents is not None:
        robot = Robot(0, 'no_name', tree, robot, position, 0, parents)
    else:
        robot = Robot(0, 'no_name', tree, robot, position, 0)
    print("new robot id = %d" %robot.robot.id)



@trollius.coroutine
def spawn_initial_robots(world, number):
    """
    :param world:
    :type world: World
    :return:
    """
    poses = [Pose(position=pick_position()) for _ in range(number)]
    trees, bboxes = yield From(world.generate_population(len(poses)))
    for index in range(number):
        spawn_robot(world, trees[index], poses[index])



@trollius.coroutine
def run_server(conf):

    conf.min_parts = 1
    conf.max_parts = 3
    conf.arena_size = (3, 3)


    world = yield From(World.create(conf))


    yield From(spawn_initial_robots(world, init_pop_size))

    robots = [r for r in world.robot_list()]

    parent_a = random.choice(robots)
    parent_b = random.choice(robots)
    print "parent_a id =", parent_a.id
    print "parent_b id =", parent_b.id

    yield From(do_mate(world, parent_a, parent_b))



def main():
    args = parser.parse_args()
    def handler(loop, context):
        exc = context['exception']
        if isinstance(exc, DisconnectError) or isinstance(exc, ConnectionResetError):
            print("Got disconnect / connection reset - shutting down.")
            sys.exit(0)

        raise context['exception']

    try:
        loop = trollius.get_event_loop()
        loop.set_debug(enabled=True)
        logging.basicConfig(level=logging.DEBUG)
        loop.set_exception_handler(handler)
        loop.run_until_complete(run_server(args))

    except KeyboardInterrupt:
        print("Got Ctrl+C, shutting down.")


if __name__ == '__main__':
    main()