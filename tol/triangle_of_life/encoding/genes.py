from copy import copy, deepcopy

class Neuron:
    """
    This is all the info about a neuron
    """

    def __init__(self, neuron_id, layer, neuron_type, body_part_id, neuron_params):
        self.neuron_id = neuron_id
        self.layer = layer
        self.neuron_type = neuron_type
        self.body_part_id = body_part_id
        self.neuron_params = neuron_params

    def copy(self):
        copy_neuron = Neuron(neuron_id=copy(self.neuron_id),
                             layer=copy(self.layer),
                             neuron_type=copy(self.neuron_type),
                             body_part_id=copy(self.body_part_id),
                             neuron_params=deepcopy(self.neuron_params))
        return copy_neuron



class Gene:
    def __init__(self, innovation_number=0, enabled=True):
        self.historical_mark = innovation_number
        self.enabled = enabled


class NeuronGene(Gene):
    def __init__(self, neuron, innovation_number=0, enabled=True):
        Gene.__init__(self, innovation_number = innovation_number,
                                       enabled = enabled)
        self.neuron = neuron


class ConnectionGene(Gene):
    def __init__(self, neuron_from, neuron_to, weight, innovation_number=0, enabled=True):
        Gene.__init__(self, innovation_number = innovation_number,
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


    def to_lists(self):
        neuron_list = []
        for neuron_gene in self.neuron_genes:
            neuron = neuron_gene.neuron
            neuron_list.append({
                "hist_mark": neuron_gene.historical_mark,
                "enabled": neuron_gene.enabled,
                "id": neuron.neuron_id,
                "layer": neuron.layer,
                "type": neuron.neuron_type,
                "params": neuron.neuron_params
            })

        conn_list = []
        for conn_gene in self.connection_genes:
            conn_list.append({
                "hist_mark": conn_gene.historical_mark,
                "enabled": conn_gene.enabled,
                "from": conn_gene.neuron_from.neuron_id,
                "to": conn_gene.neuron_to.neuron_id
            })

        return neuron_list, conn_list


    def debug_string(self):
        deb_str = ""
        n_gs, c_gs = self.to_lists()
        deb_str += "neurons:\n"
        for n_g in n_gs:
            deb_str += str(n_g)
            deb_str += "\n"
        deb_str += "connections:\n"
        for c_g in c_gs:
            deb_str += str(c_g)
            deb_str += "\n"

        return deb_str


    def copy(self):
        copy_gen = GeneticEncoding()
        old_to_new = {}

        for n_gene in self.neuron_genes:

            new_n_gene = NeuronGene(
                    neuron=n_gene.neuron.copy(),
                    innovation_number=n_gene.historical_mark,
                    enabled=n_gene.enabled)

            old_to_new[n_gene] = new_n_gene
            copy_gen.add_neuron_gene(new_n_gene)

        for c_gene in self.connection_genes:
            new_c_gene = ConnectionGene(
                    neuron_from=old_to_new[c_gene.neuron_from],
                    neuron_to= old_to_new[c_gene.neuron_to],
                    weight=c_gene.weight,
                    innovation_number=c_gene.historical_mark,
                    enabled=c_gene.enabled)
            copy_gen.add_connection_gene(new_c_gene)

        return copy_gen

