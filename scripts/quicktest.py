from __future__ import print_function

from revolve.build.util import in_grams, in_mm
from sdfbuilder import Link, SDF, Model
from sdfbuilder.structure import Collision, Visual, Box, StructureCombination
from sdfbuilder.math import Vector3
import math

from tol.build.builder import apply_surface_parameters

MASS = in_grams(3)
SENSOR_BASE_WIDTH = in_mm(34)
SENSOR_BASE_THICKNESS = in_mm(1.5)
SENSOR_THICKNESS = in_mm(9)
SENSOR_WIDTH = in_mm(18.5)
SENSOR_HEIGHT = in_mm(16)
SEPARATION = in_mm(1)

m = Model(name="mybot")
sdf = SDF(elements=[m])

geom = Box(SENSOR_BASE_THICKNESS, SENSOR_BASE_WIDTH, SENSOR_BASE_WIDTH, MASS)
base = StructureCombination("base", geom)

x_sensors = 0.5 * (SENSOR_BASE_THICKNESS + SENSOR_THICKNESS)
y_left_sensor = -0.5 * SENSOR_WIDTH - SEPARATION
y_right_sensor = 0.5 * SENSOR_WIDTH + SEPARATION

left = StructureCombination("left", Box(SENSOR_THICKNESS, SENSOR_WIDTH, SENSOR_HEIGHT, MASS))
left.set_position(Vector3(x_sensors, y_left_sensor, 0))

right = StructureCombination("right", Box(SENSOR_THICKNESS, SENSOR_WIDTH, SENSOR_HEIGHT, MASS))
right.set_position(Vector3(x_sensors, y_right_sensor, 0))

link = Link("my_link")
link.add_elements([base, left, right])


link.align_center_of_mass()
link.calculate_inertial()

m.add_element(link)

apply_surface_parameters(m)
m.translate(Vector3(0, 0, in_mm(30)))

with open("/home/elte/.gazebo/models/test_bot/model.sdf", "w") as f:
    f.write(str(sdf))
