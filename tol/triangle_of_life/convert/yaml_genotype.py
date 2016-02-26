# Revolve
import yaml
from revolve.spec.msgs import Body, BodyPart, NeuralNetwork
from revolve.spec.exception import err

# ToL
from ..encoding import GeneticEncoding, Neuron



def parse_neurons(neurons, genotype, mutator):
    # map old marks to new marks:
    neuron_marks = {}
    for neuron_gene in neurons:
        id = neuron_gene['id']
        layer = neuron_gene['layer']
        neuron_type = neuron_gene['type']
        part_id = neuron_gene['part_id']
        params = neuron_gene['params']
        old_mark = neuron_gene['hist_mark']
        enabled = neuron_gene['enabled']

        if enabled:
            neuron = Neuron(neuron_id=id,
                            layer=layer,
                            neuron_type=neuron_type,
                            body_part_id=part_id,
                            neuron_params=params)

            new_mark = mutator.add_neuron(neuron, genotype)
            neuron_marks[old_mark] = new_mark

    return neuron_marks


def parse_connections(connections, genotype, mutator, neuron_marks):
    for conn in connections:
        enabled = conn['enabled']
        hist_mark = conn['hist_mark']
        from_mark = conn['from']
        to_mark = conn['to']
        weight = conn['weight']
        if enabled:
            mutator.add_connection(mark_from=neuron_marks[from_mark],
                                   mark_to=neuron_marks[to_mark],
                                   weight=weight,
                                   genotype=genotype)




def yaml_to_genotype(yaml_stream, mutator):
    obj = yaml.load(yaml_stream)
    neurons = obj['neurons']
    connections = obj['connections']

    genotype = GeneticEncoding()
    neuron_marks = parse_neurons(neurons, genotype, mutator)
    parse_connections(connections, genotype, mutator, neuron_marks)
    return genotype




