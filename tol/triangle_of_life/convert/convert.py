# Revolve
from revolve.spec.msgs import Body, BodyPart, NeuralNetwork
from revolve.spec.exception import err

# ToL
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

        # map neuron ids to historical marks of their respective genes:
        id_mark_map = {}

        for neuron_id, neuron in neuron_map.items():
            mark = mutator.add_neuron(neuron, genotype)
            id_mark_map[neuron_id] = mark

        for connection in connection_descriptions:
            mutator.add_connection(
                mark_from=id_mark_map[connection["src"]],
                mark_to=id_mark_map[connection["dst"]],
                weight=connection["weight"],
                genotype=genotype
            )
        return genotype


    def genotype_to_brain(self, genotype):

        brain = NeuralNetwork()

#        neuron_map = self._parse_neuron_genes(genotype, brain)
#        self._parse_connection_genes(genotype, brain, neuron_map)

        self._parse_neuron_genes(genotype, brain)
        self._parse_connection_genes(genotype, brain)

        return brain


    # def _parse_neuron_genes(self, genotype, brain):
    #     neuron_map = {}
    #     for neuron_gene in genotype.neuron_genes:
    #         if neuron_gene.enabled:
    #             neuron_info = neuron_gene.neuron
    #             neuron_map[neuron_info] = neuron_info.neuron_id
    #
    #             pb_neuron = brain.neuron.add()
    #             pb_neuron.id = neuron_info.neuron_id
    #             pb_neuron.layer = neuron_info.layer
    #             pb_neuron.type = neuron_info.neuron_type
    #             pb_neuron.partId = neuron_info.body_part_id
    #
    #             neuron_spec = self.spec.get(neuron_info.neuron_type)
    #             serialized_params = neuron_spec.serialize_params(neuron_info.neuron_params)
    #             for param_value in serialized_params:
    #                 param = pb_neuron.param.add()
    #                 param.value = param_value
    #
    #     return neuron_map


    def _parse_neuron_genes(self, genotype, brain):

        for neuron_gene in genotype.neuron_genes:
            if neuron_gene.enabled:
                neuron_info = neuron_gene.neuron

                pb_neuron = brain.neuron.add()
                pb_neuron.id = neuron_info.neuron_id
                pb_neuron.layer = neuron_info.layer
                pb_neuron.type = neuron_info.neuron_type
                pb_neuron.partId = neuron_info.body_part_id

                neuron_spec = self.spec.get(neuron_info.neuron_type)
                serialized_params = neuron_spec.serialize_params(neuron_info.neuron_params)
                for param_value in serialized_params:
                    param = pb_neuron.param.add()
                    param.value = param_value





    def _parse_connection_genes(self, genotype, brain):
        for conn_gene in genotype.connection_genes:
            if conn_gene.enabled:

                mark_from = conn_gene.mark_from
                mark_to = conn_gene.mark_to

                from_id = genotype.find_gene_by_mark(mark_from).neuron.neuron_id
                to_id = genotype.find_gene_by_mark(mark_to).neuron.neuron_id

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

            neuron_spec = self.spec.get(neuron_type)
            if neuron_spec is None:
                err("Unknown neuron type '%s'" % neuron_type)
            neuron_params = neuron_spec.unserialize_params(neuron.param)


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
