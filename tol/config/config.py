import argparse


class CustomParser(argparse.ArgumentParser):
    """
    Extends argument parser to add some simple file reading / writing
    functionality.
    """
    def convert_arg_line_to_args(self, arg_line):
        """
        Simple arg line converter that returns `--my-argument value` from
        lines like "my_argument=value"
        :param arg_line:
        :return:
        """
        # Empty or comment line
        if not arg_line or arg_line[0] == "#":
            return []

        split = arg_line.find("=")
        if split < 0:
            return [arg_line]

        k, v = "--"+arg_line[:split].replace("_", "-"), arg_line[1+split:]

        # Try to determine if this key is a store constant action, if so
        # return only the key.
        const = False
        for a in self._actions:
            if k in a.option_strings and a.const is not None:
                const = True
                break

        return [k] if const else [k, v]

    def write_to_file(self, args, file):
        """
        Takes the result of `parse_args` and writes it back
        to a file.
        """
        lines = ["%s=%s\n" % (k, args.__dict__[k]) for k in sorted(args.__dict__.keys())]
        with open(file, 'w') as o:
            o.writelines(lines)


def str_to_bool(v):
    """
    :type v: str
    """
    return v.lower() in ("true", "1")


def str_to_address(v):
    """
    :type v: str
    """
    if not v:
        return None

    host, port = v.split(":", 1)
    return host, int(port)


parser = CustomParser(fromfile_prefix_chars='@')
parser.add_argument(
    '--sensor-update-rate',
    default=10, type=int,
    help='The rate at which Gazebo sensors are set to update their values.'
)

parser.add_argument(
    '--controller-update-rate',
    default=10, type=int,
    help='The rate at which the `RobotController` is requested to update.'
)

parser.add_argument(
    '--visualize-sensors',
    default=False, type=bool,
    help='Visualize sensors (helpful for debugging purposes)'
)

parser.add_argument(
    '--pose-update-frequency',
    default=8, type=int,
    help="The frequency at which the world is requested to send robot pose"
         " updates (in number of times per *simulation* second)."
)

parser.add_argument(
    '--evaluation-time',
    default=12, type=float,
    help="The size of the `speed window` for each robot, i.e. the number of past (simulation) seconds "
         "over which its speed is evaluated. In offline evolution, this determines the length"
         "of the experiment run."
)

parser.add_argument(
    '--min-parts',
    default=3, type=int,
    help="Minimum number of parts in a robot."
)

parser.add_argument(
    '--max-parts',
    default=12, type=int,
    help="Maximum number of parts in a robot."
)

parser.add_argument(
    '--max-inputs',
    default=10, type=int,
    help="Maximum number of inputs (i.e. sensors) in a robot."
)

parser.add_argument(
    '--max-outputs',
    default=10, type=int,
    help="Maximum number of outputs (i.e. sensors) in a robot."
)

parser.add_argument(
    '--enforce-planarity',
    default=True, type=str_to_bool,
    help="Force bricks to be in default orientation and disable parametric bar joint rotation."
)

parser.add_argument(
    '--body-mutation-epsilon',
    default=0.1, type=float,
    help="Mutation epsilon for robot body parameters."
)

parser.add_argument(
    '--brain-mutation-epsilon',
    default=0.2, type=float,
    help="Mutation epsilon for robot neural net parameters."
)

parser.add_argument(
    '--p-duplicate-subtree',
    default=0.1, type=float,
    help="Probability of duplicating a subtree."
)

parser.add_argument(
    '--p-connect-neurons',
    default=0.1, type=float,
    help="Initial connection probability."
)

parser.add_argument(
    '--p-swap-subtree',
    default=0.1, type=float,
    help="Probability of swapping two subtrees."
)

parser.add_argument(
    '--p-delete-subtree',
    default=0.1, type=float,
    help="Probability of deleting a subtree."
)

parser.add_argument(
    '--p-remove-brain-connection',
    default=0.1, type=float,
    help="Probability of removing a neural network connection."
)

parser.add_argument(
    '--p-delete-hidden-neuron',
    default=0.1, type=float,
    help="Probability of deleting a random hidden neuron."
)

parser.add_argument(
    '--world-address',
    default="127.0.0.1:11345", type=str,
    help="Host:port of the simulator."
)

parser.add_argument(
    '--analyzer-address',
    default="127.0.0.1:11346", type=str,
    help="Host:port of the body analyzer (set to empty string to ignore)."
)

# Directory where robot information will be written. The system writes
# two main CSV files:
# - The `robots.csv` file containing all the basic robot information, one line
#   per robot, in the format
#   id,parent1,parent2
# - The `poses.csv` file containing each robot pose through time, in the format
#   id,sim_time_sec,sim_time_nsec,x,y,z
#
# Additionally, the `Robot` protobuf message for each bot is written to
# a file called `robot_[ID].pb` when the robot is first registered.
#
# The files are written to a new YYYYMMDDHHIISS directory within the
# specified output directory, unless a subdirectory is explicitly
# provided with `--restore-directory`
parser.add_argument(
    '--output-directory',
    default=None, type=str,
    help="Directory where robot statistics are written."
)

parser.add_argument(
    '--restore-directory',
    default=None, type=str,
    help="Explicit subdirectory of the output directory, if a world "
         "state is present in this directory it will be restored."
)

parser.add_argument(
    '--disable-sensors',
    default=False, type=str_to_bool,
    help="Disables all sensors - overriding specific sensor settings. In practice "
         "this means that the core component is created without an IMU sensor, whereas "
         "the other sensor parts are not enabled at all."
)

parser.add_argument(
    '--enable-touch-sensor',
    default=True, type=str_to_bool,
    help="Enable / disable the touch sensor in robots."
)

parser.add_argument(
    '--enable-light-sensor',
    default=True, type=str_to_bool,
    help="Enable / disable the light sensor in robots."
)

parser.add_argument(
    '--warmup-time',
    default=1, type=float,
    help="The number of seconds the robot is initially ignored, allows it to e.g. topple over"
         " when put down without that being counted as movement. Especially helps when dropping"
         " robots from the sky at the start."
)