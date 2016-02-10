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




class Timers:
    def __init__(self, names, current_time):
        self.timers = {name: current_time for name in names}

    def is_it_time(self, name, time_period, current_time):
        last_time = self.timers[name]

#        print self.timers
#        print 'NAME = ', name
#        print 'last = ', last_time
#        print 'current = ', current_time
#        print ''
        if last_time is not None:
            elapsed = current_time - last_time
            if elapsed >= time_period:
                return True

        return False


    def reset(self, name, current_time):
        self.timers[name] = current_time




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
        self.life_time = life_time


        self.num_mates = 0

        self.timers = Timers(['reproduce', 'death'], self.world.last_time)
        print 'WORLD TIME = ', self.world.last_time

    def add_food(self, add_food_amount):
        self.food_found = self.food_found + add_food_amount
        self.life_time += self.time_bonus_per_food * add_food_amount


    # detect when robot finds food:
    @trollius.coroutine
    def update(self):

        cur_pos = self.my_position()

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



    def my_position(self):
        return (self.robot.last_position.x, self.robot.last_position.y)



    # this method decides whether I want to mate with other_robot
    # for now it just returns True if enough time passed since last mating
    def want_to_mate(self, other_robot):
        """
        This method decides whether this robot wants to mate with other_robot

        :param other_robot:
        :return:
        """
        return True



    def ready_to_mate(self):
        """
        Returns True if this robot is ready to mate
        :return:
        """
        return self.timers.is_it_time('reproduce', self.mating_cooldown, self.world.last_time)



    def notify_mating(self):
            """
            Call this method whenever this robot successfully mates
            It resets the cooldown time and increments personal number of mates
            :return:
            """
            self.timers.reset('reproduce', self.world.last_time)
            self.num_mates += 1



    def am_i_dead(self):
        """
        Returns True if this robot must die of old age
        :return:
        """
        cur_time = self.world.last_time
        return self.timers.is_it_time('death', self.life_time, cur_time)




# list of robot accounts:
class Population:

    def __init__(self, init_life_time, time_per_food, mating_distance, food_field, world):
        self.account_list = []
        self.food_field = food_field
        self.init_life_time = init_life_time
        self.time_per_food = time_per_food
        self.mating_distance = mating_distance
        self.world = world

    def __iter__(self):
        return iter(self.account_list)



    @trollius.coroutine
    def spawn_robot(self, tree, pose, parents=None):
        if parents is None:
            fut = yield From(self.world.insert_robot(tree, pose))
        else:
            fut = yield From(self.world.insert_robot(tree, pose, parents=parents))


        robot = yield From(fut)
        print("new robot id = %d" %robot.robot.id)
        self.append(RobotAccount(world = self.world, population = self,
                                     robot = robot, life_time = self.init_life_time,
                                     time_per_food = self.time_per_food))




    @trollius.coroutine
    def spawn_initial_robots(self, conf, number):
        poses = [Pose(position=pick_position()) for _ in range(number)]
        trees, bboxes = yield From(self.world.generate_population(len(poses)))
        for index in range(number):
            yield From(self.spawn_robot(trees[index], poses[index]))




    def append(self, account):
        self.account_list.append(account)



    def remove(self, remove_these_accounts):
        acc_upd = [acc for acc in self.account_list if acc not in remove_these_accounts]
        self.account_list = acc_upd



    def find_mate_pairs(self):

        bots_ready = [r for r in self.account_list if r.ready_to_mate()]
        num_bots = len(bots_ready)

        pairs = []
        for i in range(num_bots):
            robot_a = bots_ready[i]
            a_pos = robot_a.my_position()
            for j in range(i+1, num_bots):
                robot_b = bots_ready[j]
                b_pos = robot_b.my_position()
                dist = dist2d(a_pos, b_pos)
                if dist < self.mating_distance:
                    pairs.append((robot_a, robot_b))

        return pairs



    @trollius.coroutine
    def cleanup(self):

        dead_accounts = []
        dead_bots = []
        for account in self.account_list:
            if account.am_i_dead():
                dead_accounts.append(account)
                dead_bots.append(account.robot)

        # delete dead robots from the world:
        for dead_bot in dead_bots:
            yield From(self.world.delete_robot(dead_bot))

        # delete accounts of dead robots:
        self.remove(dead_accounts)


    @trollius.coroutine
    def reproduce(self, parent_pairs):
        for pair in parent_pairs:
            parent_a = pair[0]
            parent_b = pair[1]

            if parent_a.want_to_mate(parent_b) and parent_b.want_to_mate(parent_b):

                mate = None
                num_attempts = 0
                while num_attempts < 10:
                    # Attempt reproduction
                    mate = yield From(self.world.attempt_mate(parent_a.robot, parent_b.robot))

                    if mate:
                        break
                    num_attempts += 1


                new_pos = pick_position()
                new_pos.z = insert_z

                if mate:
                    logger.debug("Inserting child...")
                    child, bbox = mate
                    pose = Pose(position=new_pos)

                    parent_a.notify_mating()
                    parent_b.notify_mating()

                    yield From(self.spawn_robot(tree=child, pose=pose, parents=[parent_a.robot, parent_b.robot]))
                else:
                    logger.debug("Could not mate")
