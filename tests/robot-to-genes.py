import sys
import os
import yaml

# Add "tol" directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__))+'/../')

from revolve.convert import yaml_to_robot, robot_to_yaml

from tol.config import parser
from tol.spec import get_brain_spec
from tol.triangle_of_life.convert import NeuralNetworkParser
from tol.triangle_of_life.encoding import Mutator

yaml_robot = '''\
---
body:
  id: Core
  type: CoreComponent
  children:
    0:
      id: Sub1
      type: 2Params
      orientation: 180
      slot: 1
      children:
        0:
          id          : UpperLeg2
          type        : 2Params
          orientation : 90
    1:
      id: Sub2
      type: 2Params
      params:
        param_a: 10
        param_b: 20
brain:
  neurons:
    Hidden1:
      type: Oscillator
      period: 0.1
      phaseOffset: 0.2
      amplitude: 0.3
    Hidden2:
      type: Oscillator
    Hidden3: {}
  params:
    Sub1-out-1:
      type: Oscillator
      phaseOffset: 10
    Sub2-out-0:
      type: Oscillator
  connections:
    - src: Sub1-out-1
      dst: Sub1-out-1
      weight: 2
    - src: Sub2-in-1
      dst: Sub1-out-1
'''



def main():

    args = parser.parse_args()
    brain_spec = get_brain_spec(args)
    brain_parser = NeuralNetworkParser(brain_spec)

    pb_robot = yaml_to_robot(yaml_robot)
    print "yaml converted to pb"

    mutator = Mutator()

    genotype = brain_parser.robot_to_genotype(pb_robot, mutator)

    print "pb converted to genotype"
    print ""
    print genotype.neuron_genes
    print ""
    print genotype.connection_genes


if __name__ == '__main__':
    main()