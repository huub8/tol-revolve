import math
import random
import trollius
from trollius import From, Return, Future

# Revolve / sdfbuilder
from sdfbuilder.math import Vector3
from sdfbuilder import Pose, Model, Link, SDF

# ToL
from ..config import parser
from ..manage import World
from ..logging import logger, output_console
from revolve.util import multi_future


#insertion height in meters:
insert_z = 3.0



def dist2d(point1, point2):
    return math.sqrt(pow(point1[0] - point2[0], 2) + pow(point1[1] - point2[1], 2))




def pick_position():

    margin = 1
    x_min, x_max = -margin/2, margin/2
    y_min, y_max = -margin/2, margin/2

    x = random.uniform(x_min, x_max)
    y = random.uniform(y_min, y_max)
    return Vector3(x, y, insert_z)



# account that keeps track of robot's achievements:
class RobotAccount:
    def __init__(self, world, population, robot, life_time, time_per_food,
                 max_mates = 9999, mating_cooldown = 15, mating_distance = 2):

        self.robot = robot
        self.world = world
        self.population = population

        self.food_found = 0
        self.time_bonus_per_food = time_per_food

        self.mating_distance = mating_distance
        self.max_mates = max_mates
        self.mating_cooldown = mating_cooldown

        self.last_food_pos = (robot.last_position.x, robot.last_position.y)
        self.time_left = life_time


        self.num_mates = 0
        self.time_since_mating = 0


    def add_food(self, add_food_amount):
        self.food_found = self.food_found + add_food_amount
        self.time_left += self.time_bonus_per_food * add_food_amount


    # detect when robot finds food:

    @trollius.coroutine
    def update(self, deltaT):
        self.time_left -= deltaT
        self.time_since_mating += deltaT

        cur_pos = (self.robot.last_position.x, self.robot.last_position.y)

        # distance from robot to position of the last piece of food:
        dist_sq = pow(cur_pos[0] - self.last_food_pos[0], 2) + pow(cur_pos[1] - self.last_food_pos[1], 2)

        local_food_density = self.population.food_field.get_density(cur_pos[0], cur_pos[1])
        cell_i, cell_j = self.population.food_field.find_cell(cur_pos[0], cur_pos[1])

        # distance that robot must travel to find another piece of food:
        max_dist_sq = 1.0 / (local_food_density + 0.0001)

        # if that distance was traveled, add food to counter and remember current position
        if dist_sq >= max_dist_sq:
            self.last_food_pos = cur_pos
            self.add_food(1)
            # decrease local food density:
            self.population.food_field.change_density(cur_pos[0], cur_pos[1], -1)
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
                if dist < self.mating_distance:
                    yield From(self.do_mate(self.world, self.robot, other_robot.robot))
                    self.num_mates += 1
                    other_robot.num_mates += 1

                    self.time_since_mating = 0
                    other_robot.time_since_mating = 0



    @trollius.coroutine
    def do_mate(self, world, ra, rb):
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
            yield From(self.population.spawn_robot(world, tree=child, pose=pose, parents=[ra, rb]))
        else:
            logger.debug("Could not mate")
    #    yield From(sleep_sim_time(world, 1.8))

    #    logger.debug("Removing highlights...")
     #   yield From(remove_highlights(world, hls))







# list of robot accounts:
class Population:

    def __init__(self, init_life_time, time_per_food, mating_distance, food_field):
        self.account_list = []
        self.food_field = food_field
        self.init_life_time = init_life_time
        self.time_per_food = time_per_food
        self.mating_distance = mating_distance

    def __iter__(self):
        return iter(self.account_list)



    @trollius.coroutine
    def spawn_robot(self, world, tree, pose, parents=None):
        if parents is None:
            fut = yield From(world.insert_robot(tree, pose))
        else:
            fut = yield From(world.insert_robot(tree, pose, parents=parents))


        robot = yield From(fut)
        print("new robot id = %d" %robot.robot.id)
        self.append(RobotAccount(world = world, population = self,
                                     robot = robot, life_time = self.init_life_time,
                                     time_per_food = self.time_per_food))




    @trollius.coroutine
    def spawn_initial_robots(self, world, conf, number):
        """
        :param world:
        :type world: World
        :return:
        """
        poses = [Pose(position=pick_position()) for _ in range(number)]
        trees, bboxes = yield From(world.generate_population(len(poses)))
        for index in range(number):
            yield From(self.spawn_robot(world, trees[index], poses[index]))




    def append(self, account):
        self.account_list.append(account)


    def remove(self, remove_these_accounts):
        acc_upd = [acc for acc in self.account_list if acc not in remove_these_accounts]
        self.account_list = acc_upd
