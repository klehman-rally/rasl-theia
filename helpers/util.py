import json
import hmac
import hashlib


def verifyToken(request, config):
    atok = request.form.get('token', '*MISSING*')
    etok = config.get('SLACK_VERIFY_TOKEN', '*UNASSIGNED*')
    if atok != etok:
        raise ValueError('Invalid request/originator unknown')
    return True


def verifySlackSignature(request, raw_req_data, config):
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
        as other code seen in various articles flaked out, due to the issues
        covered in the above discussion.
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
def experimental_verifySlackSignature(request, raw_req_data, config):
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

    return True
