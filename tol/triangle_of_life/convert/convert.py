import math
import random
import trollius
from trollius import From, Return, Future

# Revolve / sdfbuilder
from sdfbuilder.math import Vector3
from sdfbuilder import Pose, Model, Link, SDF

# ToL
from ...config import parser
from ...manage import World
from ...logging import logger, output_console

from ..encoding import GeneticEncoding, Neuron

class NeuralNetworkParser:

    def __init__(self, spec):
        self.spec = spec
        self.neurons = {}


    def robot_to_genotype(self, robot, mutator):
        """
        :type robot: revolve.angle.Robot
        """

  #      pb_brain = robot.tree.to_robot().brain
        pb_brain = robot.brain
        pb_neurons = pb_brain.neuron
        pb_connections = pb_brain.connection

        self._parse_neurons(pb_neurons)
        connection_descriptions = self._parse_connections(pb_connections)

        genotype = GeneticEncoding()

        for neuron_id, neuron in self.neurons.items():
            mutator.add_neuron(neuron, genotype)

        for connection in connection_descriptions:
            mutator.add_connection(
                neuron_from=self.neurons[connection["src"]],
                neuron_to=self.neurons[connection["dst"]] ,
                weight=connection["weight"],
                genotype=genotype
            )
        return genotype



    def _parse_neurons(self, pb_neurons):
        for neuron in pb_neurons:
            neuron_id = neuron.id
            neuron_layer = neuron.layer
            neuron_type = neuron.type
            neuron_part_id = neuron.partId

            if neuron_id in self.neurons:
                err("Duplicate neuron ID '%s'" % neuron_id)

            spec = self.spec.get(neuron_type)
            if spec is None:
                err("Unknown neuron type '%s'" % neuron_type)
            neuron_params = spec.unserialize_params(neuron.param)


            self.neurons[neuron_id] = Neuron(
                neuron_id=neuron_id,
                layer=neuron_layer,
                neuron_type=neuron_type,
                body_part_id=neuron_part_id,
                neuron_params=neuron_params)


    def _parse_connections(self, pb_connections):
        conn_descriptions = []
        for connection in pb_connections:
            conn_descriptions.append({
                "src": connection.src,
                "dst": connection.dst,
                "weight": connection.weight
            })

        return conn_descriptions
