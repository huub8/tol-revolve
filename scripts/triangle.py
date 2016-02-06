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

# Revolve / sdfbuilder
from sdfbuilder.math import Vector3
from sdfbuilder import Pose, Model, Link, SDF

# ToL
from tol.config import parser
from tol.manage import World
from tol.logging import logger, output_console
from revolve.util import multi_future
from tol.online_evolution import Food_Grid

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

#insertion height in meters:
insert_z = 3.0

# initial food density
init_food_density = 5


#time before robots die
init_life_time = 10

# food density grid:
food_field = Food_Grid(xmin=-10, ymin=-10, xmax=10, ymax=10, xresol=100, yresol=100, value=init_food_density)

# initial population size:
init_pop_size = 5

# maximum mating distance:
mating_distance = 2


# maximum matings per robot:
max_mates_per_robot = 2


def dist2d(point1, point2):
    return math.sqrt(pow(point1[0] - point2[0], 2) + pow(point1[1] - point2[1], 2))


# account that keeps track of robot's achievements:
class RobotAccount:
    def __init__(self, world, population, robot, food, life_time, max_mates = 1, mating_cooldown = 5):
        self.robot = robot
        self.food_found = food
        self.last_food_pos = (robot.last_position.x, robot.last_position.y)
        self.time_left = life_time
        self.population = population

        self.world = world
        self.max_mates = max_mates
        self.num_mates = 0
        self.mating_cooldown = mating_cooldown
        self.time_since_mating = 0


    def add_food(self, add_food_amount):
        self.food_found = self.food_found + add_food_amount


    # detect when robot finds food:

    @trollius.coroutine
    def update(self, deltaT):
        self.time_left -= deltaT
        self.time_since_mating += deltaT

        cur_pos = (self.robot.last_position.x, self.robot.last_position.y)

        # distance from robot to position of the last piece of food:
        dist_sq = pow(cur_pos[0] - self.last_food_pos[0], 2) + pow(cur_pos[1] - self.last_food_pos[1], 2)

        local_food_density = food_field.get_density(cur_pos[0], cur_pos[1])
        cell_i, cell_j = food_field.find_cell(cur_pos[0], cur_pos[1])

        # distance that robot must travel to find another piece of food:
        max_dist_sq = 1.0 / (local_food_density + 0.0001)

        # if that distance was traveled, add food to counter and remember current position
        if dist_sq >= max_dist_sq:
            self.last_food_pos = cur_pos
            self.add_food(1)
            # decrease local food density:
            food_field.change_density(cur_pos[0], cur_pos[1], -1)
            print "robot %d found food, now %d pieces found, [%d, %d]-local density = %f" \
                  % (self.robot.robot.id, self.food_found, cell_i, cell_j, local_food_density)

        if self.time_since_mating >= self.mating_cooldown:
            yield From(self.try_to_mate())



    @trollius.coroutine
    def try_to_mate(self):
        # copy current list of accounts so that it does not grow infinitely:
        parents = [p for p in self.population]

        my_pos = (self.robot.last_position.x, self.robot.last_position.y)
        for other_robot in parents:
            if not other_robot == self and \
                self.num_mates < self.max_mates and \
                other_robot.num_mates < other_robot.max_mates:

                other_pos = (other_robot.robot.last_position.x, other_robot.robot.last_position.y)
                dist = dist2d(my_pos, other_pos)
                if dist < mating_distance:
                    yield From(do_mate(self.world, self.robot, other_robot.robot))
                    self.num_mates += 1
                    other_robot.num_mates += 1

                    self.time_since_mating = 0
                    other_robot.time_since_mating = 0







# list of robot accounts:
class Population:

    def __init__(self):
        self.account_list = []


    def __iter__(self):
        return iter(self.account_list)


    def append(self, account):
        self.account_list.append(account)


    def remove(self, remove_these_accounts):
        acc_upd = [acc for acc in self.account_list if acc not in remove_these_accounts]
        self.account_list = acc_upd


# robot accounts:
accounts = Population()


@trollius.coroutine
def sleep_sim_time(world, seconds, state_break=[False]):
    """
    Sleeps for a certain number of simulation seconds,
    note that this is always approximate as it relies
    on real world sleeping.
    :param world:
    :param seconds:
    :param state_break: List containing one boolean, the
                        wait will be terminated if this
                        is set to True (basically a hack
                        to break out of automatic mode early).
    :return:
    """
    start = world.last_time if world.last_time else Time()
    remain = seconds

    while remain > 0 and not state_break[0]:
        yield From(trollius.sleep(0.1))
        now = world.last_time if world.last_time else Time()
        remain = seconds - float(now - start)



@trollius.coroutine
def cleanup(world):
    dead_accounts = []
    dead_bots = []
    for account in accounts:
        if account.time_left <= 0:
            dead_accounts.append(account)
            dead_bots.append(account.robot)

    # delete dead robots from the world:
    for dead_bot in dead_bots:
        yield From(world.delete_robot(dead_bot))

    # delete accounts of dead robots:
    accounts.remove(dead_accounts)


def pick_position():

    margin = 1
    x_min, x_max = -margin/2, margin/2
    y_min, y_max = -margin/2, margin/2

    x = random.uniform(x_min, x_max)
    y = random.uniform(y_min, y_max)
    return Vector3(x, y, insert_z)







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
        yield From(spawn_robot(world, tree=child, pose=pose, parents=[ra, rb]))
    else:
        logger.debug("Could not mate")
#    yield From(sleep_sim_time(world, 1.8))

#    logger.debug("Removing highlights...")
 #   yield From(remove_highlights(world, hls))




@trollius.coroutine
def spawn_robot(world, tree, pose, parents=None):
    if parents is None:
        fut = yield From(world.insert_robot(tree, pose))
    else:
        fut = yield From(world.insert_robot(tree, pose, parents=parents))

    robot = yield From(fut)
    print("new robot id = %d" %robot.robot.id)
    accounts.append(RobotAccount(world = world, population = accounts, robot = robot, food = 0, life_time = init_life_time))



@trollius.coroutine
def spawn_initial_robots(world, conf, number):
    """
    :param world:
    :type world: World
    :return:
    """
    poses = [Pose(position=pick_position()) for _ in range(number)]
    trees, bboxes = yield From(world.generate_population(len(poses)))
    for index in range(number):
        yield From(spawn_robot(world, trees[index], poses[index]))






@trollius.coroutine
def update_states(world, deltaT):
    for account in accounts:
        yield From(account.update(deltaT))




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

 #   interactive = [True]

    world = yield From(World.create(conf))
    yield From(world.pause(True))

#    start_bots = conf.num_initial_bots
#    poses = [Pose(position=pick_position(conf)) for _ in range(start_bots)]

#    trees, bboxes = yield From(world.generate_population(len(poses)))

#    fut = yield From(world.insert_population(trees, poses))
#    yield From(fut)

    # List of reproduction requests
    reproduce = []

    # Request callback for the subscriber
    def callback(data):
        req = Request()
        req.ParseFromString(data)
       

        if req.request == "produce_offspring":
            reproduce.append(req.data.split("+++"))


    subscriber = world.manager.subscribe(
        '/gazebo/default/request', 'gazebo.msgs.Request', callback)
    yield From(subscriber.wait_for_connection())

    yield From(spawn_initial_robots(world, conf, init_pop_size))

    yield From(world.pause(False))


    deltaT = 0.1
    while True:

        yield From(update_states(world, deltaT))
        yield From(cleanup(world))
        yield From(trollius.sleep(deltaT))



def main():
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
  #      logging.basicConfig(level=logging.DEBUG)

        loop.set_exception_handler(handler)
        loop.run_until_complete(run_server(args))
    except KeyboardInterrupt:
        print("Got Ctrl+C, shutting down.")
    except ConnectionRefusedError:
        print("Connection refused, are the world and the analyzer loaded?")

if __name__ == '__main__':
    main()
