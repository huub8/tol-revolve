import trollius
from tol.manage import World
from trollius import From, Return
from revolve.util import wait_for
from sdfbuilder import Pose
from sdfbuilder.math import Vector3
from tol.config import parser


@trollius.coroutine
def run(conf):
    """

    :param conf:
    :return:
    """
    conf.evaluation_time = 5.0
    conf.output_directory = 'output'
    world = yield From(World.create(conf))
    yield From(world.pause(True))

    for i in range(3):
        ta, _, _ = yield From(world.generate_valid_robot())
        tb, _, _ = yield From(world.generate_valid_robot())
        ra = yield From(wait_for(world.insert_robot(ta, pose=Pose(position=Vector3(0, 3*i, 0.5)))))
        rb = yield From(wait_for(world.insert_robot(tb, pose=Pose(position=Vector3(0, 3*i + 1, 0.5)))))

        while True:
            # Attempt reproduction
            mate = yield From(world.attempt_mate(ra, rb))

            if mate:
                break

        tree, bbox = mate
        yield From(wait_for(world.insert_robot(tree, pose=Pose(position=Vector3(0, 3*i + 2, 0.5)))))


def main():
    try:
        loop = trollius.get_event_loop()
        loop.run_until_complete(run(parser.parse_args()))
    except KeyboardInterrupt:
        print("Got Ctrl+C, shutting down.")


if __name__ == '__main__':
    main()
