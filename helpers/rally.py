import sys
import time
import json
import re
import time
import string
from collections import OrderedDict

import requests

RALLY_BASE_URL = 'https://rally1.rallydev.com/slm/webservice/v2.0'
RALLY_ART_ID_PATTERN = re.compile(r'\b((?:US|S|DE|DS|TA|TC|F|I|T)\d{1,7})\b')

PAGESIZE = 2000

ENTITY = {"S"  : "HierarchicalRequirement",
          "US" : "HierarchicalRequirement",
          "DE" : "Defect",
          "DS" : "DefectSuite",
          "TA" : "Task",
          "TC" : "TestCase",
          "F"  : "Feature",
          "I"  : "Initiative",
          "T"  : "Theme",
         }

DEFECT_FIELDS = "FormattedID Name Workspace Project SubmittedBy Blocked BlockedReason Description Environment Owner State ScheduleState Priority Severity Resolution Ready LastUpdateDate Tags".split(' ')
STORY_FIELDS = "FormattedID Name Workspace Project CreatedBy Owner Blocked BlockedReason Description ScheduleState Release Feature PlanEstimate LastUpdateDate Tags".split(' ')

ART_FIELDS = {'DE' : DEFECT_FIELDS,
              'S'  : STORY_FIELDS,
              'US' : STORY_FIELDS,
             }

def rallyFIDs(target):
    """
        Given a target String that may have Rally FormattedIDs in it, extract those
        and return a list of emptiness or the items in there that match the Rally FID pattern.
    """
    hits = RALLY_ART_ID_PATTERN.findall(target)
    return hits

def artPrefix(target):
    """
        Given a target that is a FormattedID, burn off the trailing digits 
        returning the artifact prefix letters as a string.
    """
    letters = [char for char in target[:2] if char not in string.digits]
    return "".join(letters)


def getRallyArtifact(apikey, workspace, fid):
    headers = {'zsessionid': apikey}
    entity = ENTITY[artPrefix(fid)]
    fields = ART_FIELDS[artPrefix(fid)]
    specific_fid = f'(FormattedID = "{fid}")'
    params = {'workspace' : f'workspace/{workspace}',
              #'fetch'     : 'true',
              'fetch'    : f'{",".join(fields)}',
              'query'     : specific_fid
             }

    url = f'{RALLY_BASE_URL}/{entity}'
    print(f'getRallyArtifact parmams: {params}')
    #print(f'headers {headers}')
    #print(f'url {url}')
    response = requests.get(url, headers=headers, params=params)
    print(f'status_code: {response.status_code}')
    result = json.loads(response.text)
    errors = result['QueryResult']['Errors']
    if errors:
        print(f'result Errors: {errors}')
    warnings = result['QueryResult']['Warnings']
    if warnings:
        print(f'result Warnings: {warnings}')
    items = result['QueryResult']['Results']
    print(f'results items ({result["QueryResult"]["TotalResultCount"]}): {repr(items)}')
    bloated_item = items.pop(0)  # we expect only 1 item to be returned
    raw_item = {key : value for key, value in bloated_item.items() if key in fields}
    item = OrderedDict()
    item['entity'] = 'Story' if entity == 'HierarchicalRequirement' else entity
    for attr in fields:
        value = raw_item.get(attr, None)
        if value:
            if attr in ['Workspace', 'Project', 'SubmittedBy', 'CreatedBy', 'Owner']:
                value = raw_item[attr]['_refObjectName']
            if attr == 'LastUpdateDate':
                value = value.replace('T', ' ')
            if attr == 'Ready':
                value = 'yes' if value else 'no'
            if attr == 'PlanEstimate':
                value = str(value).split('.')[0]
            if attr == 'Release':
                value = raw_item[attr]['_refObjectName']
            if attr == 'Feature':
                # placeholder for now, this won't work
                # have to chase the raw_item[attr] ref value via WSAPI to get the FormattedID
                value = raw_item[attr]['_ref'] 
            if attr == 'Tags':
                if raw_item['Tags']['Count'] == 0:
                    continue
                tags_collection_ref = raw_item['Tags']['_ref']
                tags = getTags(headers, tags_collection_ref)
                value = ", ".join(tags)

            item[attr] = value 

    return item

def getTags(headers, tags_ref):
    response = requests.get(tags_ref, headers=headers)
    if response.status_code != 200:
        return []
    result = json.loads(response.text)
    if result['QueryResult']['Errors']:
        return []
    items = result['QueryResult']['Results']
    tags = [item['Name'] for item in items]
    return tags

