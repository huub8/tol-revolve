
class Neuron:
    def __init__(self, type, body_part_id):
        self.type = type
        self.body_part_id = body_part_id



class Gene:
    def __init__(self, innovation_number=0, enabled=True):
        self.historical_mark = innovation_number
        self.enabled = enabled


class NeuronGene(Gene):
    def __init__(self, neuron, innovation_number=0, enabled=True):
        super(NodeGene, self).__init__(innovation_number = innovation_number,
                                       enabled = enabled)
        self.neuron = neuron


class ConnectionGene(Gene):
    def __init__(self, neuron_from, neuron_to, weight, innovation_number=0, enabled=True):
        super(ConnectionGene, self).__init__(innovation_number = innovation_number,
                                             enabled = enabled)
        self.neuron_from = neuron_from
        self.neuron_to = neuron_to
        self.weight = weight




class GeneticEncoding:
    def __init__(self):
        self.neuron_genes = []
        self.connection_genes = []


    def connection_exists(self, neuron_from, neuron_to):
        exists = False
        for c_g in self.connection_genes:
            if c_g.neuron_from == neuron_from and c_g.neuron_to == neuron_to and c_g.enabled:
                exists = True
                break

        return exists


    def are_two_genes_same(self, gene1, gene2):
        """
        Returns True if two genes represent the same structure

        :type gene1: Gene
        :type gene2: Gene
        """

        if isinstance(gene1, NeuronGene) and isinstance(gene2, NeuronGene):
            return gene1.neuron == gene2.neuron
        elif isinstance(gene1, ConnectionGene) and isinstance(gene2, ConnectionGene):
            return gene1.neuron_from == gene2.neuron_to and gene1.neuron_to == gene2.neuron_to
        else:
            return False


    def add_neuron_gene(self, neuron_gene):
        self.neuron_genes.append(neuron_gene)


    def add_connection_gene(self, connection_gene):
        self.connection_genes.append(connection_gene)