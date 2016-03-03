# External / system
from __future__ import print_function, absolute_import
import random
import sys
import math
import trollius
from trollius import From, Return, Future
import time
import itertools
import csv
import os
from datetime import datetime

# Pygazebo
from pygazebo.msg import world_control_pb2, poses_stamped_pb2, world_stats_pb2, model_pb2

# Revolve / sdfbuilder
from revolve.angle import Tree, Crossover, Mutator, WorldManager
from sdfbuilder.math import Vector3, Quaternion
from sdfbuilder import SDF, Model, Pose, Link

# Local
from ..config import constants, parser, str_to_address
from ..build import get_builder, get_simulation_robot
from ..spec import get_tree_generator, make_planar
from revolve.util import multi_future, wait_for
from .robot import Robot
from ..scenery import Wall, BirthClinic
from ..logging import logger

# Construct a message base from the time. This should make
# it unique enough for consecutive use when the script
# is restarted.
_a = time.time()
MSG_BASE = int(_a - 14e8 + (_a - int(_a)) * 1e5)


class World(WorldManager):
    """
    A class that is used to manage the world, meaning it provides
    methods to insert / remove robots and request information
    about where they are.

    The world class contains a number of coroutines, usually from
    a request / response perspective. These methods thus work with
    two futures - one for the request to complete, one for the
    response to arrive. The convention for these methods is to
    always yield the first future, because it has proven problematic
    to send multiple messages over the same channel, so a request
    is always sent until completion. The methods then return the
    future that resolves when the response is delivered.
    """

    def __init__(self, conf, _private):
        """

        :param conf:
        :return:
        """
        super(World, self).__init__(_private=_private,
                                    world_address=str_to_address(conf.world_address),
                                    analyzer_address=str_to_address(conf.analyzer_address),
                                    output_directory=conf.output_directory,
                                    builder=get_builder(conf),
                                    state_update_frequency=conf.pose_update_frequency,
                                    generator=get_tree_generator(conf),
                                    restore=conf.restore_directory)

        self.conf = conf
        self.crossover = Crossover(self.generator.body_gen, self.generator.brain_gen)
        self.mutator = Mutator(self.generator.body_gen, self.generator.brain_gen,
                               p_duplicate_subtree=conf.p_duplicate_subtree,
                               p_swap_subtree=conf.p_swap_subtree,
                               p_delete_subtree=conf.p_delete_subtree,
                               p_remove_brain_connection=conf.p_remove_brain_connection,
                               p_delete_hidden_neuron=conf.p_delete_hidden_neuron)

        # Set to true whenever a reproduction sequence is going on
        # to prevent another one from starting (which cannot happen now
        # but might in a more complicated yielding structure).
        self._reproducing = False

        self.model_control = None
        self.birth_clinic_model = None

        # Write settings to config file
        if self.output_directory:
            parser.write_to_file(conf, os.path.join(self.output_directory, "settings.conf"))

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

    def _init(self):
        """
        :return:
        """
        yield From(super(World, self)._init())
        self.model_control = yield From(self.manager.advertise(
            '/gazebo/default/model/modify', 'gazebo.msgs.Model'
        ))

    def robots_header(self):
        """
        Extends the robots header with a max age
        :return:
        """
        return Robot.header()

    def create_robot_manager(self, robot_name, tree, robot, position, time, battery_level, parents):
        """
        Overriding with robot manager with more capabilities.
        :param robot_name:
        :param tree:
        :param robot:
        :param position:
        :param time:
        :param battery_level:
        :param parents:
        :return:
        """
        return Robot(self.conf, robot_name, tree, robot, position, time,
                     battery_level=battery_level, parents=parents)

    @trollius.coroutine
    def add_highlight(self, position, color):
        """
        Adds a circular highlight at the given position.
        :param position:
        :param color:
        :return:
        """
        hl = Highlight("highlight_"+str(self.get_robot_id()), color)
        position = position.copy()
        position.z = 0
        hl.set_position(position)
        sdf = SDF(elements=[hl])
        fut = yield From(self.insert_model(sdf))
        raise Return(fut, hl)

    @trollius.coroutine
    def generate_population(self, n):
        """
        Generates population of `n` valid robots robots.

        :param n: Number of robots
        :return: Future with a list of valid robot trees and corresponding
                 bounding boxes.
        """
        logger.debug("Generating population...")
        trees = []
        bboxes = []

        for _ in xrange(n):
            gen = yield From(self.generate_valid_robot())
            if not gen:
                raise Return(None)

            tree, robot, bbox = gen
            trees.append(tree)
            bboxes.append(bbox)

        raise Return(trees, bboxes)

    @trollius.coroutine
    def insert_population(self, trees, poses):
        """
        :param trees:
        :type trees: list[Tree]
        :param poses: Iterable of (x, y, z) positions to insert.
        :type poses: list[Pose]
        :return:
        """
        futures = []
        for tree, pose in itertools.izip(trees, poses):
            future = yield From(self.insert_robot(tree, pose))
            futures.append(future)

        future = multi_future(futures)
        future.add_done_callback(lambda _: logger.debug("Done inserting population."))
        raise Return(future)

    def get_simulation_sdf(self, robot, robot_name):
        """
        :param robot:
        :param robot_name:
        :return:
        """
        return get_simulation_robot(robot, robot_name, self.builder, self.conf)

    @trollius.coroutine
    def build_walls(self, points):
        """
        Builds a wall defined by the given points, used to shield the
        arena.
        :param points:
        :return: Future that resolves when all walls have been inserted.
        """
        futures = []
        l = len(points)
        for i in range(l):
            start = points[i]
            end = points[(i + 1) % l]
            wall = Wall("wall_%d" % i, start, end, constants.WALL_THICKNESS, constants.WALL_HEIGHT)
            future = yield From(self.insert_model(SDF(elements=[wall])))
            futures.append(future)

        raise Return(multi_future(futures))

    @trollius.coroutine
    def place_birth_clinic(self, diameter, height, angle=None):
        """
        CURRENTLY NOT USED.

        Places the birth clinic. Since we're lazy and rotating appears to cause errors,
        we're just deleting the old birth clinic and inserting a new one every time.
        Inserts the birth clinic
        :param height:
        :param diameter:
        :param angle:
        :return:
        """
        if self.birth_clinic_model:
            # Delete active birth clinic and place new
            yield From(wait_for(self.delete_model(self.birth_clinic_model.name)))
            self.birth_clinic_model = None

        if angle is None:
            angle = random.random() * 2 * math.pi

        name = "birth_clinic_"+str(self.get_robot_id())
        self.birth_clinic_model = bc = BirthClinic(name=name, diameter=diameter, height=height)
        bc.rotate_around(Vector3(0, 0, 1), angle)
        future = yield From(self.insert_model(SDF(elements=[bc])))
        raise Return(future)

    @trollius.coroutine
    def set_birth_clinic_rotation(self, angle=None):
        """
        Sets rotation of the birth clinic.
        :param angle: Desired rotation, a random angle is chosen if none is given.
        :return:
        """
        if angle is None:
            angle = random.random() * 2 * math.pi

        msg = model_pb2.Model()
        msg.name = self.birth_clinic_model.name
        quat = Quaternion.from_angle_axis(angle, Vector3(0, 0, 1))

        pose = msg.pose
        pos, rot = pose.position, pose.orientation
        pos.x, pos.y, pos.z = 0, 0, 0
        rot.w, rot.x, rot.y, rot.z = quat

        fut = yield From(self.model_control.publish(msg))
        raise Return(fut)

    @trollius.coroutine
    def attempt_mate(self, ra, rb):
        """
        Attempts mating between two robots.
        :param ra:
        :param rb:
        :return:
        """
        logger.debug("Attempting mating between `%s` and `%s`..." % (ra.name, rb.name))

        # Attempt to create a child through crossover
        success, child = self.crossover.crossover(ra.tree, rb.tree)
        if not success:
            logger.debug("Crossover failed.")
            raise Return(False)

        # Apply mutation
        logger.debug("Crossover succeeded, applying mutation...")
        self.mutator.mutate(child, in_place=True)

        if self.conf.enforce_planarity:
            make_planar(child.root)

        _, outputs, _ = child.root.io_count(recursive=True)
        if not outputs:
            logger.debug("Evolution resulted in child without motors.")
            raise Return(False)

        # Check if the robot body is valid
        ret = yield From(self.analyze_tree(child))
        if ret is None or ret[0]:
            logger.debug("Intersecting body parts: Miscarriage.")
            raise Return(False)

        logger.debug("Viable child created.")
        raise Return(child, ret[1])


class Highlight(Model):
    """
    Model to highlight newly inserted robots / selected parents
    """

    def __init__(self, name, color, **kwargs):
        super(Highlight, self).__init__(name, static=True, **kwargs)
        self.highlight = Link("hl_link")
        self.highlight.make_cylinder(10e10, 0.4, 0.001, collision=False)
        r, g, b, a = color
        self.highlight.make_color(r, g, b, a)
        self.add_element(self.highlight)
