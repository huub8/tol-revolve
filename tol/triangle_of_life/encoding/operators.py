import random
import numpy

from . import NeuronGene, ConnectionGene, GeneticEncoding, Neuron


class Mutator:

    def __init__(self, new_connection_sigma = 1, innovation_number = 0, max_attempts = 100):
        self.innovation_number = innovation_number
        self.new_connection_sigma = new_connection_sigma
        self.max_attempts = max_attempts

    def mutate_weights(self, genotype, probability, sigma):

        """
        For every connection gene change weight with probability.
        The change value is drawn from normal distribution with mean=0 and sigma

        :type genotype: GeneticEncoding
        """
        for connection_gene in genotype.connection_genes:
            if random.random() < probability:
                weight_change = random.gauss(0, sigma)
                connection_gene.weight += weight_change


    def mutate_structure(self, genotype, probability):
        """
        Mutates structure of the neural network. Adds new neurons and connections.
        Chooses whether to apply a mutation with specified probability
        Chooses what kind of mutation to apply (new connection of new neuron)
        with probability=0.5

        :type genotype: GeneticEncoding
        """

        if random.random() < probability:
            if random.random() < 0.5:
                self.add_connection_mutation(genotype, self.new_connection_sigma)
            else:
                self.add_neuron_mutation(genotype)


    def add_connection_mutation(self, genotype, sigma):
        neuron_from = random.choice(genotype.neuron_genes).neuron
        neuron_to = random.choice(genotype.neuron_genes).neuron

        num_attempts = 1
        while genotype.connection_exists(neuron_from, neuron_to):
            neuron_from = random.choice(genotype.neuron_genes).neuron
            neuron_to = random.choice(genotype.neuron_genes).neuron

            num_attempts += 1
            if num_attempts >= self.max_attempts:
                return False

        new_gene = ConnectionGene(neuron_from, neuron_to,
                                  weight = random.gauss(0, sigma),
                                  innovation_number = self.innovation_number,
                                  enabled = True)
        self.innovation_number += 1

        genotype.add_connection_gene(new_gene)

        return True


    def add_neuron_mutation(self, genotype):
        connection_to_split = random.choice(genotype)
        old_weight = connection_to_split.weight
        connection_to_split.enabled = False


        neuron_from = connection_to_split.neuron_from
        neuron_to = connection_to_split.neuron_to

        # TODO make so that new neuron can be added anywhere along the path
        body_part_id = random.choice([neuron_from.body_part_id, neuron_to.body_part_id])

        neuron_middle = Neuron("hidden", body_part_id)

        new_conn1 = ConnectionGene(neuron_from, neuron_middle,
                                  weight = old_weight,
                                  innovation_number = self.innovation_number,
                                  enabled = True)
        self.innovation_number += 1

        new_conn2 = ConnectionGene(neuron_middle, neuron_to,
                                  weight = 1.0,
                                  innovation_number = self.innovation_number,
                                  enabled = True)
        self.innovation_number += 1

        new_neuron = NeuronGene(neuron_middle,
                                innovation_number = self.innovation_number,
                                enabled = True)
        self.innovation_number += 1

        genotype.add_connection_gene(new_conn1)
        genotype.add_connection_gene(new_conn2)
        genotype.add_connection_gene(new_neuron)

