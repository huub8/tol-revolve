import os
import sys

here = os.path.dirname(os.path.abspath(__file__))
tol_path = os.path.abspath(os.path.join(here, '..', '..'))
rv_path = os.path.abspath(os.path.join(tol_path, '..', 'revolve'))
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from revolve.util import Supervisor
from offline_evolve import parser

args = parser.parse_args()

os.environ['GAZEBO_PLUGIN_PATH'] = os.path.join(tol_path, 'build')
os.environ['GAZEBO_MODEL_PATH'] = os.path.join(tol_path, 'tools', 'models')

supervisor = Supervisor(
    manager_cmd=[sys.executable, "offline_evolve.py"],
    analyzer_cmd=os.path.join(rv_path, 'tools', 'analyzer', 'run-analyzer'),
    world_file=os.path.join(here, 'offline-evolve.world'),
    output_directory=args.output_directory,
    manager_args=sys.argv[1:],
    restore_directory=args.restore_directory
)

supervisor.launch()
