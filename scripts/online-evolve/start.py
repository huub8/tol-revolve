import os
import sys

here = os.path.dirname(os.path.abspath(__file__))
tol_path = os.path.abspath(os.path.join(here, '..', '..'))
rv_path = os.path.abspath(os.path.join(tol_path, '..', 'revolve'))
sys.path.append(tol_path)

from revolve.util import Supervisor
from online_evolve import parser

os.environ['GAZEBO_PLUGIN_PATH'] = os.path.join(tol_path, 'build')
os.environ['GAZEBO_MODEL_PATH'] = os.path.join(tol_path, 'tools', 'models')


class OnlineEvolutionSupervisor(Supervisor):
    """
    Supervisor class that adds some output filtering for ODE errors
    """

    def __init__(self, *args, **kwargs):
        super(OnlineEvolutionSupervisor, self).__init__(*args, **kwargs)
        self.ode_errors = 0

    def write_stderr(self, data):
        """
        :param data:
        :return:
        """
        if 'ODE Message 3' in data:
            self.ode_errors += 1
        elif data.strip():
            sys.stderr.write(data)

        if self.ode_errors >= 100:
            self.ode_errors = 0
            sys.stderr.write('ODE Message 3 (100)\n')

manager_cmd = [sys.executable, "online_evolve.py"]
analyzer_cmd = os.path.join(rv_path, 'tools', 'analyzer', 'run-analyzer')
world_file = os.path.join(here, 'online-evolve.world')

if __name__ == '__main__':
    args = parser.parse_args()
    supervisor = OnlineEvolutionSupervisor(
        manager_cmd=manager_cmd,
        analyzer_cmd=analyzer_cmd,
        world_file=world_file,
        output_directory=args.output_directory,
        manager_args=sys.argv[1:],
        restore_directory=args.restore_directory
    )
    supervisor.launch()
