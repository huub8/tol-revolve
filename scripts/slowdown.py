from __future__ import print_function
import time
import collections
from sdfbuilder import Pose
from sdfbuilder.math import Vector3
from revolve.convert.yaml import yaml_to_robot
from revolve.util import Time
from revolve.angle import Tree
import os
import sys
from pygazebo.pygazebo import DisconnectError
import trollius
from trollius import ConnectionRefusedError, ConnectionResetError, From, Return
import random
import math

# Add root directory to import search path
sys.path.append(os.path.dirname(os.path.abspath(__file__))+'/../')

from tol.spec import get_body_spec, get_brain_spec
from tol.config import parser
from tol.manage import World


random.seed(12345)


@trollius.coroutine
def sleep_sim_time(world, seconds):
    start = world.last_time if world.last_time else Time()
    remain = seconds

    while remain > 0:
        yield From(trollius.sleep(0.05))
        now = world.last_time if world.last_time else Time()
        remain = seconds - float(now - start)


@trollius.coroutine
def birth(world, tree, bbox, parents):
    """
    Birth process, picks a robot position and inserts
    the robot into the world.
    :param world:
    :param tree:
    :param bbox:
    :param parents:
    :return:
    """
    angle = random.random() * 2 * math.pi
    r = 2.0

    # Drop height is 20cm here
    # TODO Should we check whether other robots are not too close?
    pos = Vector3(r * math.cos(angle), r * math.sin(angle), -bbox.min.z + 0.2)
    fut = yield From(world.insert_robot(tree, Pose(position=pos), parents))
    raise Return(fut)


@trollius.coroutine
def run_server():
    conf = parser.parse_args()
    conf.enable_light_sensor = False
    conf.output_directory = None
    conf.max_lifetime = 999999
    conf.initial_age_mu = 500
    conf.initial_age_sigma = 500

    world = yield From(World.create(conf))
    yield From(world.pause(True))
    trees, bboxes = yield From(world.generate_population(40))
    insert_queue = zip(trees, bboxes)

    yield From(world.pause(False))
    for tree, bbox in insert_queue[:40]:
        fut = yield From(birth(world, tree, bbox, None))
        yield From(fut)
        yield From(sleep_sim_time(world, 1.0))

    print("Inserted all robots")
    sim_time_sec = 1.0

    while True:
        before = time.time()
        yield From(sleep_sim_time(world, sim_time_sec))
        after = time.time()

        diff = after - before
        print(sim_time_sec / diff)


def main():
    def handler(loop, context):
        exc = context['exception']
        if isinstance(exc, DisconnectError) or isinstance(exc, ConnectionResetError):
            print("Got disconnect / connection reset - shutting down.")
            sys.exit(0)

        raise context['exception']

    try:
        loop = trollius.get_event_loop()
        loop.set_exception_handler(handler)
        loop.run_until_complete(run_server())
    except KeyboardInterrupt:
        print("Got Ctrl+C, shutting down.")
    except ConnectionRefusedError:
        print("Connection refused, are the world and the analyzer loaded?")

if __name__ == '__main__':
    main()
