#!/usr/bin/env python3

#
#      RESCS SHACL Shapes: Build Tools for the RESCS SHACL Shapes Library
#      Copyright (C) 2022 SWITCH
#
#      This program is free software: you can redistribute it and/or modify
#      it under the terms of the GNU Affero General Public License as published
#      by the Free Software Foundation, either version 3 of the License, or
#      (at your option) any later version.
#
#      This program is distributed in the hope that it will be useful,
#      but WITHOUT ANY WARRANTY; without even the implied warranty of
#      MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#      GNU Affero General Public License for more details.
#
#      You should have received a copy of the GNU Affero General Public License
#      along with this program.  If not, see <https://www.gnu.org/licenses/>.

from pyld import jsonld
import os
import json
from typing import List, Dict
from rdflib import Graph
from rdflib.query import Result


def absolute_from_rel_file_path(relative_path: str) -> str:
    """
    Given a path relative to this file,
    returns the absolute path.

    :param relative_path: the path relative to this file.
    :return: the absolute path.
    """
    dirname = os.path.dirname(__file__)
    return os.path.join(dirname, relative_path)


def remove_and_conjunction_from_shapes(graph: List) -> List:
    """
    Removes sh:and conjunction from shapes.
    If present, transforms second element of sh:and to sh:property.


    :param graph: The graph containing the shapes.
    :return: The transformed graph.
    """

    # Attention: shallow copy
    copy = graph.copy()

    for node_shape in copy:

        if not node_shape['@type'] == 'http://www.w3.org/ns/shacl#NodeShape':
            continue

        target_class = node_shape['http://www.w3.org/ns/shacl#targetClass']['@id']

        if target_class != 'http://schema.org/Thing':
            # sh:and: take second element if present (local props), first element is the superclass's shape.
            and_conjunction = node_shape['http://www.w3.org/ns/shacl#and']['@list']
            if len(and_conjunction) > 1:
                props = and_conjunction[1]['http://www.w3.org/ns/shacl#property']
                node_shape['http://www.w3.org/ns/shacl#property'] = props

            # Remove the sh:and conjunction -> inference has to be used instead when validating
            #
            # not sure if this mutates the originally given graph since we are
            # operating on a shallow copy
            del node_shape['http://www.w3.org/ns/shacl#and']

    return copy

def determine_inherited_properties(ontology_file_path: str, transformed_graph_file_path: str) -> Dict:
    """
    Determines properties defined on super classes of each shape.

    :param ontology_file_path: path of ontology file
    :param transformed_graph_file_path: path of transformed shapes graph
    :return: a SPARQL Select results with the following variables:
             1. shape (IRI of the node shape for which the inherited properties are determined),
             2. superClassShape (shape targeting a superclass),
             3. superClassShapePropPath (properties defined for this superclass)
    """

    g: Graph = Graph()
    g.parse(absolute_from_rel_file_path(ontology_file_path))
    g.parse(absolute_from_rel_file_path(transformed_graph_file_path))

    # For each node shape, determine its superclasses
    # and the shapes and property definitions associated with those.
    query = """
PREFIX schema: <http://schema.org/>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
PREFIX sh: <http://www.w3.org/ns/shacl#>

SELECT ?shape ?superClassShape ?superClassShapePropPath WHERE {
    ?shape a sh:NodeShape ;
        sh:targetClass ?targetClass .       
    
    OPTIONAL {

        ?targetClass rdfs:subClassOf+ ?superClass .
        ?superClassShape sh:targetClass ?superClass .
        ?superClassShape sh:property ?superClassShapeProp .
        ?superClassShapeProp sh:path ?superClassShapePropPath .
    }
} ORDER BY ?shape ?superClassShape ?superClassShapePropPath
    """

    q_res: Result = g.query(query)

    res = q_res.serialize(format='json')
    if res is not None:
        res_json = res.decode('utf-8')
    else:
        raise Exception('Could not read query results')

    res_dict = json.loads(res_json)

    return res_dict

def close_shapes(transformed_shapes: Dict) -> Dict:
    """
    Adds closed:true to all node shapes and add the ignored properties (inherited properties).

    Attention: This functionality cannot be used since sh:closed does not support inheritance,
    see <https://stackoverflow.com/questions/70785194/shacl-closed-shape-with-superclass-inheritance>.

    """
    # Attention: shallow copy
    copy = jsonld.compact(transformed_shapes.copy(), {})

    props = determine_inherited_properties('../ontology/ontology.json', '../ontology/shapes_graph_transformed.json')

    for node_shape in copy["@graph"]:
        node_shape_id = node_shape['@id']

        if node_shape_id == "http://rescs.org/dash/thing/ThingShape":
            # only inclcude rdf:type for schema:Thing
            node_shape['http://www.w3.org/ns/shacl#closed'] = True
            node_shape['http://www.w3.org/ns/shacl#ignoredProperties'] = {
                '@list': [
                    {'@id': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type'}
                ]
            }
        else:
            # print(node_shape_id)

            # collect inherited property ids
            inherited_props = list(filter(lambda res: res['shape']['value'] == node_shape_id, props['results']['bindings']))
            inherited_prop_ids = list(map(lambda prop: prop['superClassShapePropPath']['value'],inherited_props))

            # print(inherited_prop_ids)
            # print('*******')

            ignored_props = list(map(lambda prop: { '@id': prop}, inherited_prop_ids))
            ignored_props.append({'@id': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type'})

            # close node shape and add inherited properties to ignored properties
            node_shape['http://www.w3.org/ns/shacl#closed'] = True
            node_shape['http://www.w3.org/ns/shacl#ignoredProperties'] = {
                '@list': ignored_props
            }

    return copy

context = {
    "owl": "http://www.w3.org/2002/07/owl#",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "prov": "http://www.w3.org/ns/prov#",
    "dcat": "http://www.w3.org/ns/dcat#",
    "sh": "http://www.w3.org/ns/shacl#",
    "shsh": "http://www.w3.org/ns/shacl-shacl#",
    "dcterms": "http://purl.org/dc/terms/",
    "schema": "http://schema.org/",
    "rescs": "http://rescs.org/"
}

# read shapes graph
f = open(absolute_from_rel_file_path('../ontology/shapes_graph.json'), 'r')
graph = json.load(f)
compacted = jsonld.compact(graph, {})
f.close()

# remove sh:and from shapes graph (use inheritance instead when validating)
transformed_graph = remove_and_conjunction_from_shapes(compacted['@graph'])

# compact the transformed graph
transformed_compacted = jsonld.compact(transformed_graph, context)

# write the compacted transformed graph back
f = open(absolute_from_rel_file_path('../ontology/shapes_graph_transformed.json'), 'w')
f.write(json.dumps(transformed_compacted))
f.close()

