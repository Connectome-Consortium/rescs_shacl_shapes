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

import json
import sys
from typing import List, Optional, Dict
from decouple import config
from utils.file_helper_methods import absolute_from_rel_file_path
from utils.nexus_interaction import get_composite_view, update_composite_view, create_composite_view

# TOKEN has to be set
# in file .env (project root): TOKEN="..."
TOKEN = config('TOKEN')
NEXUS_ENVIRONMENT = config('NEXUS')
ORG = config('ORG')
PROJECT = config('PROJECT')
VERIFY_SSL: bool = bool(int(config('VERIFY_SSL')))  # throws an uncaught error if not numerical / integer


# get composite view
view_name = 'compositeview01'
f = open(absolute_from_rel_file_path('../compositeviews/' + view_name + '/composite_view.json', __file__), 'r')
comp_view = json.load(f)
f.close()

# get referenced ES projections by its nname, e.g., researchproject.json.
for index, es_proj_name in enumerate(comp_view['projections']):
    # Check if it is a dict (SPARQL projection)
    # If it is not a dict, it is an ES projection name to be resolved.
    if not isinstance(es_proj_name, dict):
        # get the referenced ES projection by its name
        f = open(absolute_from_rel_file_path('../compositeviews/' + view_name + '/' + es_proj_name, __file__),
                 'r')
        es_projection = json.load(f)
        f.close()
        # replace the current index with the referred ES projection
        comp_view['projections'][index] = es_projection

# get sparql projection belonging to composite view
f = open(absolute_from_rel_file_path('../compositeviews/' + view_name + '/es_projection_query.rq', __file__), 'r')
sparql_proj_query = f.read()
f.close()

# get ES settings belonging to composite view
f = open(absolute_from_rel_file_path('../compositeviews/' + view_name + '/es_settings.json', __file__), 'r')
es_settings = json.load(f)
f.close()

# add SPARQL query and ES settings to composite view's ES projection
for es_proj in comp_view['projections']:
    if es_proj['@type'] == 'ElasticSearchProjection':
        es_proj['query'] = sparql_proj_query
        es_proj['settings'] = es_settings

comp_view_rev: Optional[Dict] = get_composite_view(comp_view['@id'], NEXUS_ENVIRONMENT, ORG, PROJECT, TOKEN, VERIFY_SSL)

if comp_view_rev is not None:
    # composite view already exists, update it in Nexus
    try:
        rev = int(comp_view_rev['_rev'])
    except KeyError as e:
        raise Exception('No _rev given in composite view')

    update_res = update_composite_view(comp_view, rev, NEXUS_ENVIRONMENT, ORG, PROJECT, TOKEN, VERIFY_SSL)
    print('updated:', update_res)
else:
    # composite view does not exist yet in Nexus, create it
    created_res = create_composite_view(comp_view, NEXUS_ENVIRONMENT, ORG, PROJECT, TOKEN, VERIFY_SSL)
    print('created:', created_res)
