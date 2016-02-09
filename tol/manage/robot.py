import random

from sdfbuilder.math import Vector3
from revolve.util import Time
from revolve.angle import Robot as RvRobot


class Robot(RvRobot):
    """
    Class to manage a single robot
    """

    def __init__(self, conf, name, tree, robot, position, time, parents=None):
        """
        :param conf:
        :param name:
        :param tree:
        :param robot: Protobuf robot
        :param position:
        :type position: Vector3
        :param time:
        :type time: Time
        :param parents:
        :type parents: tuple(Robot, Robot)
        :return:
        """
        speed_window = int(conf.evaluation_time * conf.pose_update_frequency)
        super(Robot, self).__init__(name=name, tree=tree, robot=robot, position=position, time=time,
                                    speed_window=speed_window, warmup_time=conf.warmup_time, parents=parents)

        # Set of robots this bot has mated with
        self.mated_with = {}
        self.last_mate = None
        self.conf = conf

        # Set the age of death
        max_l = conf.max_lifetime
        if parents:
            pa, pb = parents
            f = 0.5 * (pa.fitness() + pb.fitness())
            c = conf.age_cutoff
            self.age_of_death = max_l * min(f, c) / c
        else:
            mu = self.conf.initial_age_mu
            sigma = self.conf.initial_age_sigma
            self.age_of_death = max(0, random.gauss(mu, sigma))

    def will_mate_with(self, other):
        """
        Decides whether or not to mate with the other given robot
        based on its position and speed.
        :param other:
        :type other: Robot
        :return:
        """
        if self.age() < self.conf.warmup_time:
            # Don't mate within the warmup time
            return False

        mate_count = self.mated_with.get(other.name, 0)
        if mate_count > self.conf.max_pair_children:
            # Maximum number of children with this other parent
            # has been reached
            return False

        if self.last_mate is not None and \
           float(self.last_update - self.last_mate) < self.conf.gestation_period:
            # Don't mate within the cooldown window
            return False

        dist = other.last_position - self.last_position
        dist.z = 0
        if dist.norm() > self.conf.mating_distance_threshold:
            return False

        my_fitness = self.fitness()
        other_fitness = other.fitness()

        return my_fitness == 0 or (other_fitness / my_fitness) >= self.conf.mating_fitness_threshold

    def write_robot(self, details_file, csv_writer):
        """

        :param details_file:
        :param csv_writer:
        :return:
        """
        with open(details_file, 'w') as f:
            f.write(self.robot.SerializeToString())

        row = [self.robot.id]
        row += [parent.robot.id for parent in self.parents] if self.parents else ['', '']
        row += [self.age_of_death]
        csv_writer.writerow(row)

    def fitness(self):
        """
        Fitness is proportional to both the displacement and absolute
        velocity of the center of mass of the robot, in the formula:

        5 dS + S

        Where dS is the displacement over a direct line between the
        start and end points of the robot, and S is the distance that
        the robot has moved.

        Since we use an active speed window, we use this formula
        in context of velocities instead.
        :return:
        """
        if self.age() < (1.5 * self.conf.warmup_time):
            # We want at least some data
            return 0.0

        return 5.0 * self.displacement_velocity() + self.velocity()

    def did_mate_with(self, other):
        """
        Called when this robot mated with another robot successfully.
        :param other:
        :type other: Robot
        :return:
        """
        self.last_mate = self.last_update

        if other.name in self.mated_with:
            self.mated_with[other.name] += 1
        else:
            self.mated_with[other.name] = 1
