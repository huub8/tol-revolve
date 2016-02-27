import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../")


from tol.config import parser
from tol.spec import get_brain_spec
from tol.triangle_of_life.encoding import GeneticEncoding
from tol.triangle_of_life.convert import NeuralNetworkParser, yaml_to_genotype


parser.add_argument(
    '--genotype-file-1',
    type=str,
    help="path to YAML file containing brain genotype"
)

parser.add_argument(
    '--genotype-file-2',
    type=str,
    default=None,
    help="path to YAML file containing brain genotype"
)



def main():
    conf = parser.parse_args()

    brain_spec = get_brain_spec(conf)
    print "READING FILES!!!!!!!!!!!!!!!!!!!"
    with open(conf.genotype_file_1, 'r') as gen_file1:
        gen_yaml1 = gen_file1.read()

    with open(conf.genotype_file_2, 'r') as gen_file2:
        gen_yaml2 = gen_file2.read()

    print "CONVERTING!!!!!!!!!"

    genotype1 = yaml_to_genotype(gen_yaml1, brain_spec, keep_historical_marks=True)
    genotype2 = yaml_to_genotype(gen_yaml2, brain_spec, keep_historical_marks=True)

    print "genotype 1:"
    print genotype1.debug_string()

    print "genotype 2:"
    print genotype2.debug_string()

    print "CALCULATING SIMILARITY!!!!!!!!!!!!!!!!!!"

    similarity = GeneticEncoding.get_dissimilarity(genotype1, genotype2)
    print "SIMILARITY = {0}".format(similarity)


if __name__ == '__main__':
    main()