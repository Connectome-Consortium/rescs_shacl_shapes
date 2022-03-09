#!/usr/bin/env python3

from decouple import config
import requests
import json
from typing import Dict
import os
from typing import List
from urllib import parse

# TOKEN has to be set
# in file .env (project root): TOKEN="..."
TOKEN = config('TOKEN')
NEXUS_ENVIRONMENT = config('NEXUS')
ORG = config('ORG')
PROJECT = config('PROJECT')
VERIFY_SSL: bool = bool(int(config('VERIFY_SSL'))) # throws an uncaught error if not numerical / integer

def absolute_from_rel_file_path(relative_path: str) -> str:
    """
    Given a path relative to this file,
    returns the absolute path.

    :param relative_path: The path relative to this file.
    :return: The absolute path.
    """
    dirname = os.path.dirname(__file__)
    return os.path.join(dirname, relative_path)


def get_composite_view(id: str) -> Dict:
    """
    Given the id of a composite view, fetches it from Nexus.

    :param id: The composite view's id, e.g, connectome-projection-composite-01.
    :return: The composite view fetched from Nexus.
    """
    req = requests.get(
        NEXUS_ENVIRONMENT + '/views/' + ORG + '/' + PROJECT + '/' + id,
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {TOKEN}'
        },
        verify=VERIFY_SSL
    )

    return req.json()

def update_composite_view(composite_view: Dict) -> None:
    """
    Given a CompositeView, updates it in Nexus.
    """

    # get composite view's id
    composite_view_id = composite_view['@id']

    # get the current revision of the composite view
    composite_view_rev = get_composite_view(composite_view_id)

    # store the current revision number
    rev: int = int(composite_view_rev['_rev'])

    req = requests.put(
        NEXUS_ENVIRONMENT + '/views/' + ORG + '/' + PROJECT + '/' + parse.quote_plus(NEXUS_ENVIRONMENT + '/resources/' + ORG + '/' + PROJECT + '/_/' + composite_view_id),
        params={ 'rev': rev },
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {TOKEN}'
        },
        data=json.dumps(composite_view),
        verify=VERIFY_SSL
    )

    print(req.status_code)
    print(req.json())


def create_composite_view(composite_view: Dict) -> None:
    """
    Given a CompositeView, registers it in Nexus.
    """

    req = requests.post(
        NEXUS_ENVIRONMENT + '/views/' + ORG + '/' + PROJECT,
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {TOKEN}'
        }, data=json.dumps(composite_view), verify=VERIFY_SSL)

    print(req.status_code)
    print(req.json())


order: List[str] = ['dataset']

for view_name in order:
    print(view_name)
    f = open(absolute_from_rel_file_path('../compositeviews/' + view_name + '.json'))
    view = json.load(f)
    f.close()

    update_composite_view(view)