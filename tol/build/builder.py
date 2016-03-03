from revolve.build.sdf import RobotBuilder, BodyBuilder, NeuralNetBuilder, BasicBattery
from sdfbuilder import SDF, Element
from sdfbuilder.physics import Friction
from sdfbuilder.structure import Collision
from sdfbuilder.util import number_format as nf
from ..spec import get_body_spec, get_brain_spec
from ..config import constants


def get_builder(conf):
    """
    :param conf:
    :return:
    """
    body_spec = get_body_spec(conf)
    brain_spec = get_brain_spec(conf)
    return RobotBuilder(BodyBuilder(body_spec, conf), NeuralNetBuilder(brain_spec))


def get_simulation_robot(robot, name, builder, conf):
    """
    :param robot:
    :param name:
    :param builder:
    :param conf: Config
    :return:
    """
    model = builder.get_sdf_model(robot, controller_plugin="libtolrobotcontrol.so",
                                  update_rate=conf.controller_update_rate, name=name)

    apply_surface_parameters(model)

    sdf = SDF()
    sdf.add_element(model)
    return sdf


def apply_surface_parameters(model):
    """
    Applies surface parameters to all collisions in the given model.
    :param model:
    :type model: Model
    :return:
    """
    # Add friction surfaces to all body parts
    surf = Element(tag_name="surface")
    friction = Friction(
        friction=constants.SURFACE_FRICTION1,
        friction2=constants.SURFACE_FRICTION2,
        slip1=constants.SURFACE_SLIP1,
        slip2=constants.SURFACE_SLIP2
    )
    contact = "<contact>" \
              "<ode>" \
              "<kd>%s</kd>" \
              "<kp>%s</kp>" \
              "</ode>" \
              "</contact>" % (
                  nf(constants.SURFACE_KD), nf(constants.SURFACE_KP)
              )

    surf.add_element(contact)
    surf.add_element(friction)

    collisions = model.get_elements_of_type(Collision, recursive=True)
    for collision in collisions:
        collision.add_element(surf)
