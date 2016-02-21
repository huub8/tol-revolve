from copy import copy, deepcopy


def validate_genotype(genotype, err_message):
    if not genotype.check_validity():
        ex = GenotypeInvalidError(message=err_message, genotype=genotype)
        print ex.debug_string()
        raise RuntimeError
    return True



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

    def __str__(self):
        return "Neuron info at " + hex(id(self))



class Gene:
    def __init__(self, innovation_number=0, enabled=True):
        self.historical_mark = innovation_number
        self.enabled = enabled


class NeuronGene(Gene):
    def __init__(self, neuron, innovation_number=0, enabled=True):
        Gene.__init__(self, innovation_number = innovation_number,
                                       enabled = enabled)
        """
        :param neuron:
        :type neuron: Neuron

        :param innovation_number:
        :type innovation_number: int

        :param enabled:
        :type enabled: bool
        """

        self.neuron = neuron


    def __str__(self):
        return "NEAT Neuron gene at " + hex(id(self)) + ",mark " + str(self.historical_mark)


class ConnectionGene(Gene):
    def __init__(self, mark_from, mark_to, weight, innovation_number=0, enabled=True):
        Gene.__init__(self, innovation_number = innovation_number,
                                             enabled = enabled)

        """
        :param mark_from:
        :type mark_from: int

        :param mark_to:
        :type mark_to: int

        :param weight:
        :type weight: float

        :param innovation_number:
        :type innovation_number: int

        :param enabled:
        :type enabled: bool
        """
        self.mark_from = mark_from
        self.mark_to = mark_to
        self.weight = weight


    def __str__(self):
            return "NEAT Connection gene at " + hex(id(self)) + ",mark " + str(self.historical_mark) + \
                " (from " + str(self.mark_from) + " to " + str(self.mark_to) + ")"




class GeneticEncoding:
    def __init__(self):
        self.neuron_genes = []
        self.connection_genes = []


    def connection_exists(self, mark_from, mark_to):
        exists = False
        for c_g in self.connection_genes:
            if c_g.mark_from == mark_from and c_g.mark_to == mark_to and c_g.enabled:
                exists = True
                break

        return exists


    def find_gene_by_mark(self, mark):
        for gene in self.neuron_genes + self.connection_genes:
            if gene.historical_mark == mark:
                return gene
        return None


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
                "from": conn_gene.mark_from,
                "to": conn_gene.mark_to
            })

        return neuron_list, conn_list


    def debug_string(self, verbose=False):
        deb_str = ""
        if verbose:
            n_gs, c_gs = self.to_lists()
            deb_str += "neurons:\n"
            for n_g in n_gs:
                deb_str += str(n_g)
                deb_str += "\n"
            deb_str += "connections:\n"
            for c_g in c_gs:
                deb_str += str(c_g)
                deb_str += "\n"

        else:
            n_gs, c_gs = self.to_lists()
            deb_str += "neurons:\n"
            for n_g in n_gs:
                deb_str += "("
                deb_str += str(n_g["id"])
                deb_str += ")"
            deb_str += "\nconnections:\n"
            for c_g in c_gs:
                deb_str += "["
                deb_str += str(c_g["from"])
                deb_str += ", "
                deb_str += str(c_g["to"])
                deb_str += "]"

        return deb_str


    def copy(self):
        copy_gen = GeneticEncoding()
        old_to_new = {}

        for n_gene in self.neuron_genes:

            new_n_gene = NeuronGene(
                    neuron=n_gene.neuron.copy(),
                    innovation_number=n_gene.historical_mark,
                    enabled=n_gene.enabled)

            old_to_new[n_gene.neuron] = new_n_gene.neuron
            copy_gen.add_neuron_gene(new_n_gene)


        for c_gene in self.connection_genes:

            new_c_gene = ConnectionGene(
                    mark_from=c_gene.mark_from,
                    mark_to= c_gene.mark_to,
                    weight=c_gene.weight,
                    innovation_number=c_gene.historical_mark,
                    enabled=c_gene.enabled)
            copy_gen.add_connection_gene(new_c_gene)

        return copy_gen


    def check_validity(self):
        for conn_gene in self.connection_genes:
            mark_from = conn_gene.mark_from
            mark_to = conn_gene.mark_to
            if not self.check_neuron_exists(mark_from):
                return False
            if not self.check_neuron_exists(mark_to):
                return False
        return True


    def check_neuron_exists(self, mark):
        result = False
        for neuron_gene in self.neuron_genes:
            if mark == neuron_gene.historical_mark:
                result = True
        return result


    def __str__(self):
        return "NEAT Genotype at " + hex(id(self))



class GenotypeCopyError(Exception):
    def __init__(self, message, genotype):
        self.message = message
        self.genotype = genotype
    def debug_string(self):
        print "--------------------------"
        print self.message
        print "Tried to copy this genotype:"
        print "neurons:"
        for n_g in self.genotype.neuron_genes:
            print str(n_g) + ": " + str(n_g.neuron)
        print "connections:"
        for c_g in self.genotype.connection_genes:
            print c_g
        print "--------------------------"


class GenotypeInvalidError(Exception):
    def __init__(self, message, genotype):
        self.message = message
        self.genotype = genotype

    def debug_string(self):
        print "--------------------------"
        print self.message
        print "Invalid genotype:"
        print "neurons:"
        for n_g in self.genotype.neuron_genes:
            print n_g
        print "connections:"
        for c_g in self.genotype.connection_genes:
            print c_g
        print "--------------------------"