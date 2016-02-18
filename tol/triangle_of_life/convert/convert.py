import math
import random
import trollius
from trollius import From, Return, Future

# sdfbuilder
from sdfbuilder.math import Vector3
from sdfbuilder import Pose, Model, Link, SDF

# Revolve
from revolve.spec import BodyImplementation, NeuralNetImplementation
from revolve.spec.msgs import Body, BodyPart, NeuralNetwork

# ToL
from ...config import parser
from ...manage import World
from ...logging import logger, output_console
from ..encoding import GeneticEncoding, Neuron

class NeuralNetworkParser:

    def __init__(self, spec):
        self.spec = spec


    def brain_to_genotype(self, pb_brain, mutator):

        pb_neurons = pb_brain.neuron
        pb_connections = pb_brain.connection

        neuron_map = self._parse_neurons(pb_neurons)
        connection_descriptions = self._parse_connections(pb_connections)

        genotype = GeneticEncoding()

        for neuron_id, neuron in neuron_map.items():
            mutator.add_neuron(neuron, genotype)

        for connection in connection_descriptions:
            mutator.add_connection(
                neuron_from=neuron_map[connection["src"]],
                neuron_to=neuron_map[connection["dst"]] ,
                weight=connection["weight"],
                genotype=genotype
            )
        return genotype


    def genotype_to_brain(self, genotype):
        neuron_genes = genotype.neuron_genes
        connection_genes = genotype.connection_genes

        brain = NeuralNetwork()

        neuron_map = self._parse_neuron_genes(genotype, brain)
        self._parse_connection_genes(genotype, brain, neuron_map)
        return brain


    def _parse_neuron_genes(self, genotype, brain):
        neuron_map = {}
        for neuron_gene in genotype.neuron_genes:
            if neuron_gene.enabled:
                neuron_info = neuron_gene.neuron
                neuron_map[neuron_info] = neuron_info.neuron_id
                pb_neuron = brain.neuron.add()

                pb_neuron.id = neuron_info.neuron_id
                pb_neuron.layer = neuron_info.layer
                pb_neuron.type = neuron_info.neuron_type
                pb_neuron.partId = neuron_info.body_part_id
				
                serialized_params = self.spec.serialize_params(neuron_info.neuron_params)
                for param_value in serialized_params:
                    param = pb_neuron.param.add()
                    param.value = param_value
					
   #             for key, value in neuron_info.neuron_params.items():
   #                 param = pb_neuron.param.add()
   #                 param.value = value


    def _parse_connection_genes(self, genotype, brain, neuron_map):
        for conn_gene in genotype.connection_genes:
            if conn_gene.enabled:
                from_id = neuron_map[conn_gene.neuron_from]
                to_id = neuron_map[conn_gene.neuron_to]
                weight = conn_gene.weight
                pb_conn = brain.connection.add()
                pb_conn.src = from_id
                pb_conn.dst = to_id
                pb_conn.weight = weight


    def _parse_neurons(self, pb_neurons):
        neuron_map = {}
        for neuron in pb_neurons:
            neuron_id = neuron.id
            neuron_layer = neuron.layer
            neuron_type = neuron.type
            neuron_part_id = neuron.partId


            if neuron_id in neuron_map:
                err("Duplicate neuron ID '%s'" % neuron_id)

            spec = self.spec.get(neuron_type)
            if spec is None:
                err("Unknown neuron type '%s'" % neuron_type)
            neuron_params = spec.unserialize_params(neuron.param)


            neuron_map[neuron_id] = Neuron(
                neuron_id=neuron_id,
                layer=neuron_layer,
                neuron_type=neuron_type,
                body_part_id=neuron_part_id,
                neuron_params=neuron_params)
        return neuron_map


    def _parse_connections(self, pb_connections):
        conn_descriptions = []
        for connection in pb_connections:
            conn_descriptions.append({
                "src": connection.src,
                "dst": connection.dst,
                "weight": connection.weight
            })

        return conn_descriptions


