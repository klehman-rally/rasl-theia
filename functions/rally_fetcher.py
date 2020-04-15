import json
import requests
import re
from helpers.util import verifySlackSignature


def seerally(request):
    """
        Responds to any HTTP request.
        Args:
            request (flask.Request): HTTP request object.
            the guts of the info is in request.form (an ImmutableMultDict instance)
            and will typically have the following items:
              token        : 8AhHFCl1kJLyNdE3frhr9cLt
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
    #verified_req = verifySlackSignature(request, config)
    response_url = request.form['response_url']
    print(f'would send response to: {response_url}')

    response = '{"text":"Hola Slacker, digesting your request..."}'
    return response


def inhaleConfig():
    with open('config.json', 'r') as f:
        data = f.read()
    config = json.loads(data)
    return config

def rallyInfoFetcher():
    """
    """
    pass
