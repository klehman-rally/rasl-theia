import sys
import time
import json
import re
import time
from collections import OrderedDict

import requests

RALLY_BASE_URL = 'https://rally1.rallydev.com/slm/webservice/v2.0'
RALLY_ART_ID_PATTERN = re.compile(r'\b((?:US|S|DE|TA|DS|F|I|T)\d{1,6})\b')
PAGESIZE = 2000

DEFECT_FIELDS = "FormattedID Name Workspace Project SubmittedBy Blocked BlockedReason Description Environment FlowState Owner State ScheduleState Priority Severity Resolution Ready LastUpdateDate Tags".split(' ')

def rallyFIDs(target):
    """
        Given a target String that may have Rally FormattedIDs in it, extract those
        and return a list of emptiness or the items in there that match the Rally FID pattern.
    """
    hits = RALLY_ART_ID_PATTERN.findall(target)
    return hits

def getRallyArtifact(apikey, workspace, fid):
    headers = {'zsessionid': apikey}
    #entity  = "Artifact"
    entity  = "Defect"
    #fields  = 'FormattedID,Name,ObjectID,Tags,State,PlanEstimate,Owner,Assigned,Description'
    #fields  = 'FormattedID,Name,ObjectID,Tags,State,Owner,Description'
    specific_fid = f'(FormattedID = "{fid}")'
    params = {'workspace' : f'workspace/{workspace}',
              #'fetch'     : 'true',
              'fetch'    : f'{",".join(DEFECT_FIELDS)}',
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
    raw_item = {key : value for key, value in bloated_item.items() if key in DEFECT_FIELDS}
    item = OrderedDict()
    for attr in DEFECT_FIELDS:
        value = raw_item.get(attr, None)
        if value:
            if attr in ['Workspace', 'Project', 'FlowState', 'SubmittedBy']:
                value = raw_item[attr]['_refObjectName']
            if attr == 'CreatedBy':
                value = raw_item['CreatedBy']['Name']
            if attr == 'LastUpdateDate':
                value = value.replace('T', ' ')
            if attr == 'Tags':
                if raw_item['Tags']['Count'] == 0:
                    continue
                tags_collection_ref = raw_item['Tags']['_ref']
                tags = getTags(headers, tags_collection_ref)
                value = ", ".join(tags)

            item[attr] = value 

    return item

def getTags(headers, tags_ref):
    response = requests.get(tags_ref, headers=headers, params=params)
    if response.status_code != 200:
        return []
    result = json.loads(response.text)
    if result['QueryResult']['Errors']:
        return []
    items = result['QueryResult']['Results']
    tags = [item['Name'] for item in items]
    return tags

