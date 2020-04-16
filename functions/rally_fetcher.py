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
    workspace = '65842453532'
    if apikey:
        art_info = getRallyArtifact(apikey, workspace, rally_fid)
        print(f'art_info: {repr(art_info)}')
    
    response = '{"text":"Hola Slacker, digesting your request..."}'
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


def rallyInfoFetcher():
    """
    """
    pass



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
    req_data = request.form

    # alt 2.5
    #req_data = jsonify(request.form)

    # alt 3
    #data = request.form.to_dict(flat=False)
    #req_data = jsonify(data)

    # alt 4
    #length = request.headers["Content-Length"]
    #req_data = request.stream.read(length)

    payload = str.encode(f'v0:{timestamp}:{req_data}')
    print(f'payload: {payload}')

    secret = str.encode(config['SLACK_SIGNING_SECRET'])
    #print(f'slack shush: {secret}')
    request_digest = hmac.new(secret, payload, hashlib.sha256).hexdigest()
    request_hash = f'v0={request_digest}'
    print(f'request_hash: {request_hash}')

    if not hmac.compare_digest(request_hash, signature):
        print('message not deemed valid...')
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


