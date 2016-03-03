from revolve.convert import yaml_to_robot, robot_to_yaml

from tol.spec import get_body_spec, get_brain_spec
from tol.config import parser


def main():
    conf = parser.parse_args()
    with open("scripts/testBots/gecko",'r') as yamlfile:
        yaml_bot = yamlfile.read()

    body_spec = get_body_spec(conf)
    brain_spec = get_brain_spec(conf)

    print "converting to protobuf..."
    pb_bot = yaml_to_robot(body_spec, brain_spec, yaml_bot)

    print "converting to yaml..."
    yaml_bot = robot_to_yaml(body_spec, brain_spec, pb_bot)

    with open("scripts/testBots/gecko.yaml",'w') as out_file:
        out_file.write(yaml_bot)

    print "done"



if __name__ == '__main__':
    main()
