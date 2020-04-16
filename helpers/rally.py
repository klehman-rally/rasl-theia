import sys
import time
import json
import re
import time

import requests

RALLY_BASE_URL = 'https://rally1.rallydev.com/slm/webservice/v2.0'
RALLY_ART_ID_PATTERN = re.compile(r'\b((?:US|S|DE|TA|DS|F|I|T)\d{1,6})\b')
PAGESIZE = 2000

def rallyFIDs(target):
    """
        Given a target String that may have Rally FormattedIDs in it, extract those
        and return a list of emptiness or the items in there that match the Rally FID pattern.
    """
    hits = RALLY_ART_ID_PATTERN.findall(target)
    return hits

def getRallyArtifact(apikey, workspace, fid):
    headers = {'zsessionid': apikey}
    entity  = "Artifact"
    fields  = 'FormattedID,Name,ObjectID,Tags,State,PlanEstimate,Owner,Assigned,Description'
    specific_fid = f'(FormattedID = "{fid}")'
    params = {'workspace' : f'workspace/{workspace}',
              'fetch'     : fields,
              'query'     : specific_fid
             }

    url = f'{RALLY_BASE_URL}/{entity}'
    print(f'getRallyArtifact parmams: {params}')
    print(f'headers {headers}')
    print(f'url {url}')
    response = requests.get(url, headers=headers, params=params)
    print(f'status_code: {response.status_code}')
    result = json.loads(response.text)
    errors = result['QueryResult']['Errors']
    print(f'result Errors: {errors}')
    return result['QueryResult']['Results']

def validRallyIdent(apikey, sub_id):
    headers = {'zsessionid': apikey}
    entity  = "User"
    fields  = "SubscriptionID"
    url = f'{RALLY_BASE_URL}/{entity}?fetch={fields}'
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 401:
            # the api_key was probably bad
            return None, '401 - Rally resource needs full authentication'
        message_dict = json.loads(response.text)
        user = message_dict['User']
        user_info = {'name'     : user['_refObjectName'], 
                     'shortRef' : user['_ref'].split('v2.0/')[1], 
                     'sub_id'   : user['SubscriptionID']}
        print(f'Found user {repr(user_info)}')
    except Exception as exc:
        print("unable to query Rally for User\n", 
              file=sys.stderr)
        return None, exc
    if not sub_id:
        return None, 'No subscription id value provided'
    user_exists_in_sub = ((user != None) and ('SubscriptionID' in user) and (user['SubscriptionID'] == int(sub_id)))
    if user_exists_in_sub:
        return user_exists_in_sub, None
    else:
        return None, 'the api_key provided is not valid for the subscription id value'

def getArtifactWorkspaceRef(apikey, artifact_ref, transaction_id):
    headers = {'zsessionid': apikey}
    params = {'fetch': 'Workspace'}
    try:
        response = requests.get(artifact_ref, headers=headers, params=params)
        if re.search(r'<html>|<html |<!DOCTYPE html>', response.text):
            mo = re.search(r'<title>(?P<html_err>.+?)</title>', response.text)
            html_err = mo.group('html_err') if mo else response.text
            html_err = html_err.replace("\n", '\\n')
            err_desc = f'getArtifactWorkspaceRef response is HTML, not JSON data'
            print(f'transaction_id: {transaction_id} - {err_desc} --> {html_err}',
                  file=sys.stderr)
            return None
        result = json.loads(response.text)
    except Exception as exc:
        err_desc = f'unable to query Rally for specific Artifact: {artifact_ref}'
        print(f'transaction_id: {transaction_id} - {err_desc} --> exception: {exc}', 
              file=sys.stderr)
        return None

    operation_result = result.get('OperationResult', None)
    if operation_result:
        if operation_result.get('Errors', None):
            err_desc = f'getArtifactWorkspaceRef encountered error: {operation_result["Errors"]}'
            print(f'transaction_id: {transaction_id} - {err_desc}',
                  file=sys.stderr)
            return None

    target_artifact_type = list(result.keys())[0]
    workspace = result[target_artifact_type]['Workspace']['_ref']
    return workspace

def getSubscription(api_key, sub_id, transaction_id):
    endpoint = '/subscription'
    url = f'{RALLY_BASE_URL}{endpoint}'
    headers = {'zsessionid': api_key}
    params = {'fetch': 'SubscriptionID,Workspaces'}
    try:
        response = requests.get(url, headers=headers, params=params)
        if re.search(r'<html>|<html |<!DOCTYPE html>', response.text):
            mo = re.search(r'<title>(?P<html_err>.+?)</title>', response.text)
            html_err = mo.group('html_err') if mo else response.text
            html_err = html_err.replace("\n", '\\n')
            err_desc = 'getSubscription response is HTML, not JSON data'
            print(f'transaction_id: {transaction_id}  sub_id: {sub_id} - {err_desc} --> {html_err}', 
                  file=sys.stderr)
            return None
        subscription = json.loads(response.text)['Subscription']
        desc = (f'getSubscription returned sub_id: {subscription["SubscriptionID"]} '
                f'with access to {subscription["Workspaces"]["Count"]} workspaces')
        print(f'transaction_id: {transaction_id} - {desc}')
    except Exception as exc:
        err_desc = 'getSubscription hit an exception when getting Rally subscription'
        print(f'transaction_id: {transaction_id}  sub_id: {sub_id} - {err_desc} Exception: {exc}',
              file=sys.stderr)
        return None
    return subscription

def getCurrentUserWorkspaces(api_key, sub_id, transaction_id):

    subscription = getSubscription(api_key, sub_id, transaction_id)
    if not subscription:
        desc = (f'getCurrentUserWorkspaces was unable to obtain list of current user workspaces, '
                f'no such subscription available')
        print(f'transaction_id: {transaction_id}  sub_id: {sub_id} - {desc}')
        return []
    workspaces_ref = subscription['Workspaces']['_ref']
    short_refs = []
    if not workspaces_ref:
        return short_refs

    before = time.time()
    short_refs = getPagedRallyWorkspaces(api_key, transaction_id, sub_id, workspaces_ref)
    after  = time.time()
    elapsed = after - before
    stats = (f'getCurrentUsersWorkspaces took {elapsed:6.3f} secs '
             f'to obtain {len(short_refs)} Open workspaces')
    print(f'transaction_id: {transaction_id}  sub_id: {sub_id} - {stats}')

    return short_refs

def getPagedRallyWorkspaces(api_key, transaction_id, sub_id, workspaces_ref):
    max_pages  = 100  # we expect there will never be a customer with more than 200K workspaces
    short_refs = []
    headers = {'zsessionid': api_key}
    start = 1
    for page in range(1, max_pages):
        try:
            query_string = f'query=(State = "Open")&pagesize={PAGESIZE}&start={start}'
            response = requests.get(f'{workspaces_ref}?{query_string}', headers=headers)
            if re.search(r'<html>|<html |<!DOCTYPE html>', response.text):
                mo = re.search(r'<title>(?P<html_err>.+?)</title>', response.text)
                html_err = mo.group('html_err') if mo else response.text
                html_err = html_err.replace("\n", '\\n')
                err_desc = f'getCurrentUserWorkspaces response is HTML, not JSON data'
                print((f'transaction_id: {transaction_id}  sub_id: {sub_id} '
                       f'request page: {page} - {err_desc} --> {html_err}'),
                      file=sys.stderr)
                return []

            query_result = json.loads(response.text)['QueryResult']
            total_result_count = query_result['TotalResultCount']
            workspaces         = query_result['Results']

        except Exception as exc:
            err_desc = (f'getCurrentUserWorkspaces hit an exception when '
                        f'getting workspaces in Rally subscription')
            print(f'transaction_id: {transaction_id}  sub_id: {sub_id}  request page: {page} - {err_desc}',
                 file=sys.stderr)
            print(f'{exc}', file=sys.stderr)
            return []

        short_refs.extend([workspace['_ref'].split('/v2.0/', 1)[1] for workspace in workspaces])
        if len(short_refs) >= total_result_count:
            break
        start += PAGESIZE

    return short_refs

def _protectedRallyQuery(url, headers=None, workspace_ref=None, query=None, fetch='true', start=1):
    """
        generic method to make a query to Rally in a protected way,
        returns a status, result, error_text tuple.
        If all went well the return tuple     will be True, Python dictionary of data, None
        If a problem occured the return tuple will be False, None, String
    """
    status     = True  # assume the best
    error_text = ""
    result     = {}
    response   = None

    try:
        query_spec = {'workspace' : workspace_ref, 
                      'query'     : query, 
                      'fetch'     : fetch, 
                      'pagesize'  : PAGESIZE, 
                      'start'     : start}
        response = requests.get(url, headers=headers, params=query_spec)
        if re.search(r'<html>|<html |<!DOCTYPE html>', response.text):
            mo = re.search(r'<title>(?P<html_err>.+?)</title>', response.text)
            html_err = mo.group('html_err') if mo else response.text
            html_err = html_err.replace("\n", '\\n')
            error_text = (f'Rally query response for  workspace: {workspace_ref}, '
                          f'query: {query}  is HTML, not JSON data --> {html_err}')
            return False, result, error_text
        result = json.loads(response.text)
    except Exception as exc:
        output = "undetermined error"
        if response:
            try:
                if re.search(r'<html>|<html |<!DOCTYPE html>', response.text):
                    mo = re.search(r'<title>(?P<html_err>.+?)</title>', response.text)
                    output = mo.group('html_err') if mo else response.text
                else:
                    output = response.text
            except:
                output = response.text
        output = output.replace("\n", '\\n')
        error_text = (f'Rally query hit an exception for workspace: {workspace_ref}, '
                      f'query: {query}  response text: {output}  exception: {exc}')
        return False, result, error_text

    errors = result['QueryResult']['Errors']
    if errors:
        status = False
        error_text = (f'Rally returned query error {result["QueryResult"]["Errors"]}, '
                      f'workspace: {workspace_ref}, query: {query} ')
    else:
        result = result['QueryResult']['Results']

    return status, result, error_text
