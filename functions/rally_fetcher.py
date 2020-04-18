import os
import json
import requests
import re

from flask import jsonify, make_response

from helpers.rally import rallyFIDs, getRallyArtifact
#from helpers.util import verifySlackSignature

import hmac
import hashlib

def seerally(request):
    """
        Responds to any HTTP request.
        Args:
            request (flask.Request): HTTP request object.
            the guts of the info is in request.form (an ImmutableMultDict instance)
            and will typically have the following items:
              token        : jT9AcTUPWqtcPQofmAF6APMc
              team_id      : T85AUPHJ4
              team_domain  : ca-agilecentral
              channel_id   : C011LE84T6J
              channel_name : rasl
              user_id      : U01050ZL0Q1
              user_name    : kiplin.lehman
              command      : /seerally
              text         : US1987
              response_url : https://hooks.slack.com/commands/T85AUPHJ4/1062528018130/RmDtib4gK4opYm574qVGmS0B
              trigger_id   : 1055794393350.277368799616.09508f061b903b44eb8e68770cd68282

        Processing:

        Returns:
            The response text or any set of values that can be turned into a
            Response object using
            `make_response <http://flask.pocoo.org/docs/1.0/api/#flask.Flask.make_response>`.
    """
    print(f'request headers: {repr(request.headers)}')  # there are headers...
    #print(f"request.__dict__ {request.__dict__}")      # lot of environment things in there ...
    # do this before pulling anything else out of the request 
    # to avoid contamination or inadvertent draining of buffers...
    try:   
        raw_req_data = request.get_data()
        #print(f'raw_req_data of length {len(raw_req_data)}: |{raw_req_data}|')
    except Exception as exc:
        print(exc)

    #print(f'request method: {request.method}')
    #print(f'request data: {request.data}')
    #print(f'request args: {request.args}')
    #request_json = request.get_json()  # this seems to return None as there is no data
    #print(f'request origin: {request.origin}')
    #print(f'request mimetype: {request.mimetype}')
    #print(f'request remote_addr: {request.remote_addr}')

    #####
    #   
    #  Check the token value against expected, abort with 404 if not perfect 
    #  Check command is /seerally
    #  Check that team_domain is ca-agilecentral, team_id is as expected
    #  Check that text has a single Rally Artifact FormattedID item
    #  Check that response_url is present and looks plausible
    #  Check that channel_id is in our config and has an associated Rally WSAPI API Key
    #  
    #####

    config = inhaleConfig()
    verifySignature(request, raw_req_data, config)
    print('request signature indicates valid Slack origination')

    #verifyToken(request, config)
    #print('request token indicates valid Slack origination')

    response_url = request.form['response_url']
    #print(f'would send response to: {response_url}')

    # grab the command, check for expected value
    command = request.form.get('command', '')
    if command != "/seerally":
        return make_response(jsonify({"text": "invalid command specification"}), 404)
    # extract the first "word" that looks like a Rally artifact FormattedID
    # and attempt to find it via requests.get

    form_text = request.form.get('text', '')
    rally_fids = rallyFIDs(form_text)
    if rally_fids:
        rally_fid = rally_fids.pop(0)

    slack_channel = request.form.get('channel_id')
    raw_ralmap = os.environ.get('RALLY_MAP', ' / ')
    ck_pairs = raw_ralmap.split(',')
    ralmap = {pair.split(' / ')[0] : pair.split(' / ')[1] for pair in ck_pairs}
    apikey = ralmap[slack_channel] if slack_channel in ralmap else None
    # we hard-code the Rally workspace ObjectID here, 
    # but we'd need to put it in the RALLY_MAP as part of a triple
    # with channel_id / api_key / workspace_id,  ... or something similar
    workspace = '65842453192'
    if not apikey:
        response = {"text":"Hola Slacker, I have no info for you..."}
        return jsonify(response)

    art_info = getRallyArtifact(apikey, workspace, rally_fid)
    print(f'art_info: {repr(art_info)}')
    slack_blocks = slackifyRallyArtifact(art_info)
    package = {"text"   : "info for Rally artifact",
               "response_type": "ephemeral",
               "blocks" : slack_blocks
              }

    print(f"response package: {package}")
    response = jsonify(package)
    return response


def inhaleConfig():
    with open('config.json', 'r') as f:
        data = f.read()
    config = json.loads(data)
    return config


def verifyToken(request, config):
    atok = request.form.get('token', '*MISSING*')
    etok = config.get('SLACK_VERIFY_TOKEN', '*UNASSIGNED*')
    if atok != etok:
        raise ValueError('Invalid request/originator unknown')
    return True


def slackifyRallyArtifact(item):
    """
     DE3243 Foobar is nuts but you have dutiful sinews
    <------------------------------------------------->
     Workspace xxxxxxxx   Project XXXXXXXXXX
     SubmittedBy          Owner
     Environment          Ready
     State                ScheduleState
     LastUpdateDate       Tags
    <------------------------------------------------->
     Description

     The above is the gross level formatting to be done with fields from the item.
     Using the Slack Block approach, for the big belly section we'll use the fields
     construct where you can have 2 colums of info.  Each entry in a column will be
     mrkdwn formatted with the field name in normal text and the field value immediately
     to the right and in bold text.  We'll need to process in pairs, as an example
     we'll take 'FoundInBuild' and 'FixedInBuild' as a pair.  They'll each get an element
     in the Blocks construct being populated.
       "fields" : [
        ...
        {"type": "mrkdwn", "text": "Environment *Production*"}
        {"type": "mrkdwn", "text": "Ready -no-"}
        ...
        ]

     The whole Blocks construction consists of

       FormattedID Name
       <divider>
         Field pairs
         Field pairs
         ...
       <divider>
       Description
       <divider>
        help and a note to make the results available to all in the channel
    """
    blocks = []

    print("in slackifyRallyArtifact")
    fake_link   = f'<fakeLink.toArtifact.rallydev.com|*{item["FormattedID"]}*>'
    headline    = mrkdwnSection(f'{fake_link} {item["Name"]}')
    # Limit the description to a max of 2000 chars
    description = f'_{item["Description"][:2000]}_'  # underscores make this italicized
    # Slack only allows 10 items in a 2 columns "fields" construct
    field_pairs = [('Workspace',      'Project'      ), 
                   ('SubmittedBy',    'Owner'        ), 
                   ('Environment',    'Ready'        ), 
                   ('State',          'ScheduleState'), 
                   ('LastUpdateDate', 'Tags'         )
                  ]
    print("... calling pairedFields for the item and the pairs")
    fields = pairedFields(item, field_pairs)
    blocks = [headline, divider(), fields]

    #  deal with Blocked and BlockedReason this separately from fields
    #  and only include it after the fields if the item is Blocked 
    blocked = False
    if item.get('Blocked', False):
        blocked = True
        not_speced = 'No reason for the block has been supplied'
        blocked_reason = item.get('BlockedReason', not_speced)
        blockage = mrkdwnSection(f'*BLOCKED* - {blocked_reason}')
        blocks.append(blockage)

    blocks.append(divider())
    blocks.append(mrkdwnSection(description))
    print("back to caller with the blocks...")
    return blocks

def divider():
    return { "type": "divider" }

def mrkdwnSection(text):
    section = {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f'{text}'}
              }
    return section

def pairedFields(item, pairs):
    """
        A pair results in two slack fields items where 
        each field is normal case name of field and the field value in bold.
        There is some special casing for the Ready, Tags and LastUpdateDate field
        where they either don't get their value bolded or get semi-truncated.
    """
    field_items = []
    for left, right in pairs:

        left_raw_value  = item.get(left,  '')
        right_raw_value = item.get(right, '')
        # only bold the value with *<value>* if there is a value
        left_value  = f'*{left_raw_value}*'  if left_raw_value else ''
        right_value = f'*{right_raw_value}*' if right_raw_value else ''
        if left == 'LastUpdateDate':
            left_value = f'*{left_raw_value[:-5]} Z*' # cut off the millis part
        if right == 'Ready':
            if not right_value:
                right_value = 'no'
        if right == 'Tags':
            if not right_value:
                right_value = '-none-'
        lcol = {"type": "mrkdwn", "text": f'{left}  {left_value}'}
        rcol = {"type": "mrkdwn", "text": f'{right} {right_value}'}
        field_items.append(lcol)
        field_items.append(rcol)
        #print(f' left: {lcol}')
        #print(f'right: {rcol}')

    return { "type": "section", "fields": field_items }


def verifySignature(request, raw_req_data, config):
    """
        The Slack doco (and their example code in their Python slackeventsapi/server.py code)
        states that you have to put together the version, timestamp, request data into
        a bytestring after slamming them together like f'v0:{timestamp}:{request.get_data()}'.
        However the request data is already a bytestring so you have to str.encode the 
        leading part first and then append the request data bytestring.
        Then, you use that along with the Slack signing secret to obtain an hmac (sha256)
        item that you call hexdigest on to obtain a value that is compared to the signature
        that was passed along in the request header.
        However, using that technique is brittle, as if you don't read the data from the 
        request *very* early, it seems to vanish if you've attempted to use request.data
        or request.get_json(), etc.
        The data is available when you access request.form (unknown as to whether that
        access triggers the "draining" of request.data inside that instance) but it 
        isn't in a form that'll match the request's Content-Length value.
        This working function took an inordinate amount of time to perform
        as other code seen in various articles, due to the above discussion.
    """
    timestamp = request.headers.get('X-Slack-Request-Timestamp', '')
    signature = request.headers.get('X-Slack-Signature', '')
    print(f'message timestamp: {timestamp}')
    print(f'message signature: {signature}')
    if not timestamp or not signature:
        raise ValueError('Invalid request/credentials, missing elements')

    payload = str.encode(f'v0:{timestamp}:') + raw_req_data
    #print(f'signature check payload: {payload}')

    # from gcp-github-app helpers/signature.py ->validateGithubSignature function
    # HMAC requires its key to be bytes 
    secret = str.encode(config['SLACK_SIGNING_SECRET'])
    mac_digest = hmac.new(secret, payload, hashlib.sha256).hexdigest()
    request_hash = f'v0={mac_digest}'
    print(f'request sig hash : {request_hash}')

    if not hmac.compare_digest(request_hash, signature):
        raise ValueError('Invalid request/credentials.')
    return True

############## only dump this when verifySignature above is working... ########
def inner_verifySignature(request, raw_req_data, config):
    timestamp = request.headers.get('X-Slack-Request-Timestamp', '')
    signature = request.headers.get('X-Slack-Signature', '')
    print(f'message timestamp: {timestamp}')
    print(f'message signature: {signature}')
    if not timestamp or not signature:
        raise ValueError('Invalid request/credentials, missing elements')

    # from gcp-github-app helpers/signature.py ->validateGithubSignature function
    # HMAC requires its key to be bytes 
    #mac = hmac.new(secret, msg=request.data, digestmod=hashlib.sha256)
    #return hmac.compare_digest(mac.hexdigest(), signature)

    # original
    #payload = str.encode('v0:{}:'.format(timestamp)) + request.get_data()
    # using f-string
    #payload = str.encode(f'v0:{timestamp}:') + request.get_data()

    #command  = request.form['command']
    #text     = request.form['text']
    # alt 1
    #req_data = f'command={command}&text={text}'   

    # alt 2
    #req_data = request.form

    # alt 3
    #req_data = request.form.to_dict(flat=True)
    #print(f"request.form.to_dict(flat=True) results in a {type(req_data)} instance, with {len(req_data)} keys")
    #req_data = json.dumps(req_data)

    # alt 4   so apparently we get a big fat nothing out of this...
    #length = request.headers["Content-Length"]
    #req_str_dat = request.stream.read(length)
    #print(f'request.stream.read({length}) results in a '
    #       f'{type(req_str_dat)} instance, size {len(req_str_dat)}')

    # alt 5   and we get a big fat nothing out of this too
    #body = request.get_data() 
    #print(f"request.get_data() returned a {type(body)} instance, size {len(body)}")
    #req_data = body.decode('utf-8')

    #print(f'req_data: {req_data}')

    #payload = str.encode(f'v0:{timestamp}:') + req_data
    #payload = str.encode(f'v0:{timestamp}:{req_data}')
    #payload = f'v0:{timestamp}:{req_data}'
    payload = str.encode(f'v0:{timestamp}:') + raw_req_data
    print(f'payload: {payload}')

    secret = str.encode(config['SLACK_SIGNING_SECRET'])
    #print(f'slack shush: {secret}')
    # HMAC requires its key to be bytes... 
    request_digest = hmac.new(secret, payload, hashlib.sha256).hexdigest()
    request_hash = f'v0={request_digest}'
    print(f'request_hash: {request_hash}')

    if not hmac.compare_digest(request_hash, signature):
        print('message deemed NOT valid...')
        #raise ValueError('Invalid request/credentials, comparison failed')


def example_blocks():
    blocks = [
               {
                "type": "section",
                "text": {
                         "text": "A message *with some bold text* and _some italicized text_.",
                         "type": "mrkdwn"
                        },
                "fields": [
                        { "type": "mrkdwn", "text": "*Priority*" },
                        { "type": "mrkdwn", "text": "*Type*"     },
                        { "type": "plain_text", "text": "High"   },
                        { "type": "plain_text", "text": "String" }
                 ]
               },
               { "type": "divider" },
               {
                "type": "section",
                "text": {
                         "type": "mrkdwn",
                         "text": "<fakeLink.toArtifact.rallydev.com|*DE108345*> No more heavy wet snowstorms for me thank you"
                        }
               },
               { "type": "divider" },
               {
                "type": "section",
                "fields": [
                            { "type": "mrkdwn", "text": "Workspace : *Geronimo's Plunge Pool*" },
                            { "type": "mrkdwn", "text": "Project: *Moki and his pony*" },
                            { "type": "mrkdwn", "text": "Submitter : *Neruda Placebo*" },
                            { "type": "mrkdwn", "text": "Owner: *Sanford Benton*" }
                          ]
               },
               { "type": "divider" },
               {
                "type": "section",
                "text": { "type": "mrkdwn", "text": "_Bogons and Whiners live next door_" }
               }
           ]
    return blocks

def minimal_blocks():
    resp = {"text" : "a little bogosity for your evening entertainment",
            "blocks" : [{"type" : "section", 
                         "text":{"text":"_Alice Merton_ *rulz*!","type":"mrkdwn"},
                         "fields": [{"type": "mrkdwn", "text": "Name"}, 
                                    {"type": "mrkdwn", "text": "Wheat"}, 
                                    {"type": "mrkdwn", "text": "*bottoluini*"}, 
                                    {"type": "mrkdwn", "text": "*farina*"}
                                   ]            
                        }, 
                        {"type": "divider"}
                       ]
           }
    print(f"returning resp which is a {type(resp)} instance with:")
    print(repr(resp))
    return resp

