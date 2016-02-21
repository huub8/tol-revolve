import random

from . import NeuronGene, ConnectionGene, GeneticEncoding, Neuron, GenotypeCopyError



class Mutator:

    def __init__(self, brain_spec, new_connection_sigma = 1, innovation_number = 0, max_attempts = 100):
        self.innovation_number = innovation_number
        self.new_connection_sigma = new_connection_sigma
        self.max_attempts = max_attempts
        self.brain_spec = brain_spec


    def mutate_neuron_params(self, genotype, probability):
        """
        Each neuron gene is chosen to be mutated with probability.
        The parameter to be mutated is chosen from the set of parameters with equal probability.
        """

        # # FOR DEBUG
        # #########################################
        # print "before mutation:"
        # print genotype.debug_string()
        # ##########################################



        for neuron_gene in genotype.neuron_genes:
            if random.random() < probability:

                # # FOR DEBUG
                # ##################################
                # print 'mutating gene :{0}'.format(neuron_gene.neuron.neuron_id)
                # ##################################

                random_param_values = self.brain_spec.get(neuron_gene.neuron.neuron_type).\
                    get_random_parameters(serialize=False) # returns dictionary {param_name:param_value}
                if random_param_values:
                    param_name, param_value = random.choice(random_param_values.items()) # choose one param to mutate

                    # # FOR DEBUG
                    # ##################################
                    # print 'mutating param :{0} -- new value = {1}'.format(param_name, param_value)
                    # ##################################


                    neuron_gene.neuron.neuron_params[param_name] = param_value

                # else:
                #    # # FOR DEBUG
                #    #  ##################################
                #    #  print 'no params'
                #    #  ##################################


        # # FOR DEBUG
        # #########################################
        # print "after mutation:"
        # print genotype.debug_string()
        # ##########################################





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
            if len(genotype.connection_genes) == 0:
                self.add_connection_mutation(genotype, self.new_connection_sigma)
            else:
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

        self.add_connection(neuron_from, neuron_to, weight = random.gauss(0, sigma), genotype = genotype)


        return True


    def add_neuron_mutation(self, genotype):
        connection_to_split = random.choice(genotype.connection_genes)
        old_weight = connection_to_split.weight
        connection_to_split.enabled = False

        neuron_from = connection_to_split.neuron_from
        neuron_to = connection_to_split.neuron_to

        # TODO make so that new neuron can be added anywhere along the path
        body_part_id = random.choice([neuron_from.body_part_id, neuron_to.body_part_id])


        new_neuron_type = "simple"
        # TODO Add option to generate neurons of other types

        new_neuron_params = self.brain_spec.get(new_neuron_type).\
                    get_random_parameters(serialize=False) # returns dictionary {param_name:param_value}

 #       neuron_middle = Neuron("hidden", body_part_id)
        neuron_middle = Neuron(
            neuron_id="innov" + str(self.innovation_number),
            neuron_type=new_neuron_type,
            layer="hidden",
            body_part_id=body_part_id,
            neuron_params=new_neuron_params
        )

        self.add_neuron(neuron_middle, genotype)
        self.add_connection(neuron_from, neuron_middle, old_weight, genotype)
        self.add_connection(neuron_middle, neuron_to, 1.0, genotype)




    def add_neuron(self, neuron, genotype):
        new_neuron_gene = NeuronGene(neuron,
                                innovation_number = self.innovation_number,
                                enabled = True)
        self.innovation_number += 1
        genotype.add_neuron_gene(new_neuron_gene)


    def add_connection(self, neuron_from, neuron_to, weight, genotype):
        new_conn_gene = ConnectionGene(neuron_from, neuron_to,
                                  weight = weight,
                                  innovation_number = self.innovation_number,
                                  enabled = True)
        self.innovation_number += 1
        genotype.add_connection_gene(new_conn_gene)


class Crossover:

    @staticmethod
    def crossover(genotype_more_fit, genotype_less_fit):
        # copy original genotypes to keep them intact:
        try:
            genotype_more_fit = genotype_more_fit.copy()
            genotype_less_fit = genotype_less_fit.copy()
        except GenotypeCopyError as ex:
            print "--------------------------"
            print "Crossover: Error when copying genotype"
            print ex.message
            print "neurons:"
            for n_g in ex.genotype.neuron_genes:
                print n_g.neuron
            print "connections:"
            for c_g in ex.genotype.connection_genes:
                print "[" + str(c_g.neuron_from) + "," + str(c_g.neuron_to) + "]"
            print "--------------------------"


        # sort genes by historical marks:
        genes_better = sorted(genotype_more_fit.neuron_genes + genotype_more_fit.connection_genes,
                        key = lambda gene: gene.historical_mark)

        genes_worse = sorted(genotype_less_fit.neuron_genes + genotype_less_fit.connection_genes,
                        key = lambda gene: gene.historical_mark)

        # assume that each genotype has at most 1 gene per historical_mark

        min_hist_mark = min(genes_better[0].historical_mark, genes_worse[0].historical_mark)

        max_hist_mark = max(genes_better[-1].historical_mark,
                            genes_worse[-1].historical_mark)

        gene_pairs = []

        # search for pairs of genes with equal marks:
        for mark in range(min_hist_mark, max_hist_mark+1):
            better_gene = None
            for i in range(len(genes_better)):
                if genes_better[i].historical_mark == mark:
                    better_gene = genes_better[i]
                    break

            worse_gene = None
            for i in range(len(genes_worse)):
                if genes_worse[i].historical_mark == mark:
                    worse_gene = genes_worse[i]
                    break

            gene_pairs.append((better_gene, worse_gene))


        child_genes = []

        for pair in gene_pairs:

            # if gene is paired, inherit one of the pair with 50/50 chance:
            if pair[0] is not None and pair[1] is not None:
                if random.random() < 0.5:
                    child_genes.append(pair[0])
                else:
                    child_genes.append(pair[1])

            # inherit unpaired gene from the more fit parent:
            elif pair[0] is not None:
                child_genes.append(pair[0])

        child_genotype = GeneticEncoding()
        for gene in child_genes:
            if isinstance(gene, NeuronGene):
                child_genotype.add_neuron_gene(gene)
            elif isinstance(gene, ConnectionGene):
                child_genotype.add_connection_gene(gene)

        return child_genotype