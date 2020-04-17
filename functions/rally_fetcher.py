import os
import json
import requests
import re

from flask import jsonify

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
              trigger_id   : 1055794393350.277368799616.09508f061b903b44eb8e68770cd68282"

        Processing:

        Returns:
            The response text or any set of values that can be turned into a
            Response object using
            `make_response <http://flask.pocoo.org/docs/1.0/api/#flask.Flask.make_response>`.
    """
    print(f'request headers: {repr(request.headers)}')  # there are headers...
    try:
        formls  = "  ".join([f'{k}: {v}' for k,v in request.form.items()])
        print(f'form items: {formls}')
    except Exception as exc:
        print(exc)
    try:
        form_data = jsonify(request.form)
        print(f'form data as json: {form_data}')
    except Exception as exc:
        print(exc)

    #print(f'request method: {request.method}')
    #print(f'request data: {request.data}')
    #print(f'request args: {request.args}')
    #argls = "  ".join([f'{k} : {v}' for k, v in request.args.items()])
    #print(f'req arlgs: {argls}')
    #request_json = request.get_json()  # this seems to return None as there is no data
    #print(f'request origin: {request.origin}')
    #print(f'request mimetype: {request.mimetype}')
    #print(f'request remote_addr: {request.remote_addr}')

    #####
    #   
    #  Check the token value against expected, abort with 503 if not perfect 
    #  Check command is /seerally
    #  Check that team_domain is ca-agilecentral, team_id is as expected
    #  Check that text has a single Rally Artifact FormattedID item
    #  Check that response_url is present and looks plausible
    #  Check that channel_id is in our config and has an associated Rally WSAPI API Key
    #  
    #####

    config = inhaleConfig()
    #verified_req = verifySlackSignature(request, config)  # something is horked with signing...
    #ok = verifySignature(request, config)
    ok = inner_verifySignature(request, config)
    if ok:
        print('request signature indicates valid Slack origination')
    #else:
    #    print(f'bad request arrangement, no operation...')

    ok = verifyToken(request, config)
    print('request token indicates valid Slack origination')

    response_url = request.form['response_url']
    print(f'would send response to: {response_url}')

    # grab the text, extract the first "word" that looks like a Rally artifact FormattedID
    # and attempt to find it via requests.get
    rally_fids = rallyFIDs(request.form.get('text', ''))
    if rally_fids:
        rally_fid = rally_fids.pop(0)

    slack_channel = request.form.get('channel_id')
    raw_ralmap = os.environ.get('RALLY_MAP', ' / ')
    ck_pairs = raw_ralmap.split(',')
    ralmap = {pair.split(' / ')[0] : pair.split(' / ')[1] for pair in ck_pairs}
    apikey = ralmap[slack_channel] if slack_channel in ralmap else None
    # we hard-code the Rally workspace ObjectID here, but we'd need to put it in the RALLY_MAP...
    workspace = '65842453192'
    if not apikey:
        response = {"text":"Hola Slacker, I have no info for you......"}
        return response

    art_info = getRallyArtifact(apikey, workspace, rally_fid)
    print(f'art_info: {repr(art_info)}')
    slack_blocks = slackifyRallyArtifact(art_info)

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
    return jsonify(resp)
"""
    blocks = {[
               {
                "type": "section",
                "text": {
                         "text": "A message *with some bold text* and _some italicized text_.",
                         "type": "mrkdwn"
                        },
                "fields": [
                        {
                           "type": "mrkdwn",
                           "text": "*Priority*"
                        },
                        {
                           "type": "mrkdwn",
                           "text": "*Type*"
                        },
                        {
                           "type": "plain_text",
                           "text": "High"
                        },
                        {
                            "type": "plain_text",
                            "text": "String"
                        }
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
                            {
                              "type": "mrkdwn",
                              "text": "Workspace : *Geronimo's Plunge Pool*"
                            },
                            {
                              "type": "mrkdwn",
                              "text": "Project: *Moki and his pony*"
                            },
                            {
                              "type": "mrkdwn",
                              "text": "Submitter : *Neruda Placebo*"
                            },
                            {
                              "type": "mrkdwn",
                              "text": "Owner: *Sanford Benton*"
                            }
                          ]
               },
               { "type": "divider" },
               {
                "type": "section",
                "text": {
                          "type": "mrkdwn",
                          "text": "_Bogons and Whiners live next door_"
                        }
               }
           ]
       }
    response = json.dumps(blocks)
    return response

    #response = jsonify(slack_blocks)
    #print(f'slacky_json: {response}')
    #return response
"""


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
     Blocked  T/F         BlockedReason
     Severity             Priority
     Ready                Resolution
     FoundInBuild         FixedInBuild
     State                ScheduleState
     PlanEstimate         Release
     FlowState            Environment
     LastUpdateDate       Tags or DisplayColor
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
        {"type": "mrkdwn", "text": "FoundInBuild: *3.14.2*"}
        {"type": "mrkdwn", "text": "FixedInBuild: **"}
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
    description = f'_{item["Description"]}_'  # underscores make this italicized
    field_pairs = [('Workspace',      'Project'      ), 
                   ('SubmittedBy',    'Owner'        ), 
                   ('Blocked',        'BlockedReason'), 
                   ('Ready',          'Resolution'   ), 
                   ('FoundInBuild',   'FixedInBuild' ), 
                   ('State',          'ScheduleState'), 
                   ('PlanEstimate',   'Release'      ),
                   ('FlowState',      'Environment'  ),
                   ('LastUpdateDate', 'Tags'         )
                  ]
    print("... calling pairedFields for the item and the pairs")
    fields = pairedFields(item, field_pairs)
    blocks = [headline,
              divider(),
              fields,
              divider(),
              description
             ]
    print("back to caller with the blocks...")
    return {"blocks": blocks}

def divider():
    return { "type": "divider" }

def mrkdwnSection(text):
    section = {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "f'{text}'"}
              }
    return section

def pairedFields(item, pairs):
    field_items = []
    for left, right in pairs:
        if left == 'Blocked':
            if not item.get('Blocked', False):  # if not Blocked don't include this pair
                continue
        if left == 'FoundInBuild':
            if not item.get(left, False) and not item.get(right, False):
                continue
        if left == 'PlanEstimate':
            if not item.get(left, False) and not item.get(right, False):
                continue
        if left == 'FlowState':
            if not item.get(left, False) and not item.get(right, False):
                continue

        lcol = {"type": "mrkdwn", "text": "f'{left}  : *{item.get( left, '')}*'"}
        rcol = {"type": "mrkdwn", "text": "f'{right} : *{item.get(right, '')}*'"}
        field_items.append(lcol)
        field_items.append(rcol)

    return { "type": "section", "fields": field_items }


def inner_verifySignature(request, config):
    timestamp = request.headers.get('X-Slack-Request-Timestamp', '')
    signature = request.headers.get('X-Slack-Signature', '')
    print(f'message timestamp: {timestamp}')
    print(f'message signature: {signature}')
    if not timestamp or not signature:
        raise ValueError('Invalid request/credentials, missing elements')

    # from gcp-github-app helpers/signature.py ->validateGithubSignature function
    # HMAC requires its key to be bytes, but data is strings.
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

    # alt 2.5
    #req_data = jsonify(request.form)

    # alt 3
    #req_data = request.form.to_dict(flat=False)
    req_data = request.form.to_dict(flat=True)
    print(f"request.form.to_dict results in a {type(req_data)} instance")

    # alt 3.5
    #data = request.form.to_dict(flat=False)
    #req_data = jsonify(data)

    # alt 4
    #length = request.headers["Content-Length"]
    #req_data = request.stream.read(length)

    # alt 5
    #body = request.get_data()
    #req_data = body.decode('utf-8')

    print(f'req_data: {req_data}')

    #payload = str.encode(f'v0:{timestamp}:') + req_data
    #payload = str.encode(f'v0:{timestamp}:{req_data}')
    payload = f'v0:{timestamp}:{req_data}'
    print(f'payload: {payload}')

    secret = str.encode(config['SLACK_SIGNING_SECRET'])
    #print(f'slack shush: {secret}')
    request_digest = hmac.new(secret, payload.encode('utf-8'), hashlib.sha256).hexdigest()
    request_hash = f'v0={request_digest}'
    print(f'request_hash: {request_hash}')

    if not hmac.compare_digest(request_hash, signature):
        print('message deemed NOT valid...')
        #raise ValueError('Invalid request/credentials, comparison failed')


def verifySignature(request, config):
    """
        The Slack doco (and their example code in their Python slackeventsapi/server.py code)
        states that you have to put together the version, timestamp, request data into
        a bytestring after slamming them together like f'v0:{timestamp}:{request.get_data()}'.
        Then, you use that along with the Slack signing secret to obtain an hmac (sha256)
        item that you call hexdigest on to obtain a value that is compared to the signature
        that was passed along in the request header.
        However, using that technique doesn't work, mostly because there is never anything
        in request.data or request.get_data().  This seems to be related to how Slack
        handles slash commands. They provide form data (request.form) in an ImmutableMultDict
        instance. They have other example doco related to signing that implies that the
        request data that should be or is actually used is a quasi query-string of
        'command=/foobar&text=whatever'.  Processing the message to come up with that and
        use it in the signature checking also doesn't work out.
        This signature thing is great, but if they use other stuff that they don't document
        or change what they do but don't document it, then it is all for nothing...
    """
    timestamp = request.headers.get('X-Slack-Request-Timestamp', '')
    signature = request.headers.get('X-Slack-Signature', '')

    command = request.form['command']
    text    = request.form['text']
    vbody = f'command={command}&text={text}' 
    #req = str.encode('v0:{}:'.format(timestamp)) + request.get_data()
    #req = str.encode('v0:{}:{}'.format(timestamp, req_data))
    req_data = str.encode(f'v0:{timestamp}:{vbody}')
    print(f"pre-sig check req: {req_data}")
    request_digest = hmac.new(str.encode(config['SLACK_SIGNING_SECRET']),
                              req_data, hashlib.sha256).hexdigest()
    request_hash = f'v0={request_digest}'
    print(f'verf request_hash: {request_hash}')

    if not hmac.compare_digest(request_hash, signature):
        raise ValueError('Invalid request/credentials.')
    print('request signature indicates valid Slack origination')
    return True


