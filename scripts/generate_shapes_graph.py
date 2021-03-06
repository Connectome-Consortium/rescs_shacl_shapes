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

from typing import Union
from typing import List
from typing import Dict

import os
from pyld import jsonld
import json
import glob

def absolute_from_rel_file_path(relative_path: str) -> str:
    """
    Given a path relative to this file,
    returns the absolute path.

    :param relative_path: the path relative to this file.
    :return: the absolute path.
    """
    dirname = os.path.dirname(__file__)
    return os.path.join(dirname, relative_path)

def determine_property_range(prop: Dict) -> Dict:
    """
    Given a property's datatype, class, or nodeKind, determines its range.

    :param prop: the property whose range is to be determined
    :return: a dictionary
    {
        'http://schema.org/rangeIncludes': {
            '@id': range
        }
    }
    """

    if "http://www.w3.org/ns/shacl#datatype" in prop:
        return {
            'http://schema.org/rangeIncludes': prop['http://www.w3.org/ns/shacl#datatype']
        }
    elif "http://www.w3.org/ns/shacl#class" in prop:
        return {
            'http://schema.org/rangeIncludes': prop['http://www.w3.org/ns/shacl#class']
        }
    elif "http://www.w3.org/ns/shacl#nodeKind" in prop:
        return {
            'http://schema.org/rangeIncludes': prop['http://www.w3.org/ns/shacl#nodeKind']
        }
    else:
        raise TypeError("Unknown range for " + str(prop))


def generate_property_def(prop: Dict, shacl_target_class: str) -> Dict:
    """
    Given a SHACL PropertyShape, generates an RDF definition from it.
    :param prop: the given PropertyShape.
    :param shacl_target_class: the shape's target class.
    :return: a dictionary representing the PropertyShape in RDF
    """

    prop_def = {
        "@id": prop['http://www.w3.org/ns/shacl#path']['@id'],
        "@type": "http://www.w3.org/1999/02/22-rdf-syntax-ns#Property",
        "http://schema.org/domainIncludes": {
            "@id": shacl_target_class
        },
        "http://www.w3.org/2000/01/rdf-schema#label": prop["http://www.w3.org/ns/shacl#name"],
        "http://www.w3.org/2000/01/rdf-schema#comment": prop["http://www.w3.org/ns/shacl#description"]
    }

    if not 'http://www.w3.org/ns/shacl#or' in prop:
        prop_def.update(determine_property_range(prop))
    else:
        defs = []
        for p in prop['http://www.w3.org/ns/shacl#or']['@list']:
            defs.append(determine_property_range(p))

        prop_def.update({
            'http://schema.org/rangeIncludes': list(map(lambda r: r['http://schema.org/rangeIncludes'], defs))
        })

    return prop_def


def analyse_property_shapes(props: Union[Dict, List[Dict]], target_class: str) -> List[Dict]:
    """
    Given a PropertyShape or a list of PropertyShapes, turns them into an RDF representation.

    :param props: a PropertyShape or a list of PropertyShapes.
    :param target_class:
    :return:
    """

    prop_defs = []
    if isinstance(props, list):
        for prop in props:
            prop_defs.append(generate_property_def(prop, target_class))
    else:
        prop_defs.append(generate_property_def(props, target_class))

    return prop_defs

def generate_property_defs_from_shapes(graph: List) -> List:
    """
    From the SHACL shapes, generate the property definitions.

    :param graph: The graph containing the shapes
    :return: The property definitions.
    """
    # property defs
    properties = []
    # for the given NodeShapes, analyse their properties
    for node_shape in graph:

        if not node_shape['@type'] == 'http://www.w3.org/ns/shacl#NodeShape':
            continue

        target_class = node_shape['http://www.w3.org/ns/shacl#targetClass']['@id']

        if target_class == 'http://schema.org/Thing':
            # Thing shape: only local properties
            props = analyse_property_shapes(node_shape['http://www.w3.org/ns/shacl#property'], target_class)
            properties.extend(props)
        else:
            # sh:and: take second element if present (local props), first element is the superclass's shape.
            and_conjunction = node_shape['http://www.w3.org/ns/shacl#and']['@list']
            if len(and_conjunction) > 1:
                props = analyse_property_shapes(and_conjunction[1]['http://www.w3.org/ns/shacl#property'], target_class)
                properties.extend(props)

    return properties

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

onto: Dict = {
    "@graph": []
}

# get shapes from files
# this only works for the current folder structure: shapes/[name]/schema.json
for filename in glob.iglob(absolute_from_rel_file_path('../shapes/') + '**/schema.json', recursive=True):
    f = open(filename)
    shape = json.load(f)
    f.close()
    compacted = jsonld.compact(shape, {})
    onto['@graph'].append(compacted['https://bluebrain.github.io/nexus/vocabulary/shapes'])

# write shapes to file
f = open(absolute_from_rel_file_path('../ontology/shapes_graph.json'), 'w')
f.write(json.dumps(jsonld.compact(onto, context)))
f.close()

# get class defs from ontology file
f = open(absolute_from_rel_file_path('../ontology/ontology.json'))
schema = json.load(f)
f.close()
compacted = jsonld.compact(schema, {})

# print(compacted)
# append classes from ontology.json
onto['@graph'].extend(compacted['@graph'])

# append properties extracted from SHACL shapes
properties = generate_property_defs_from_shapes(onto['@graph'])
onto['@graph'].extend(properties)

onto = jsonld.compact(onto, context)

onto_json = json.dumps(onto)

# write shapes and ontology to file
f = open(absolute_from_rel_file_path('../ontology/shapes_ontology_graph.json'), 'w')
f.write(onto_json)
f.close()
