import hmac
import hashlib

def verifySlackSignature(request, config):
    """
        origin github.com/slackapi/python-slack-events-api/slackeventsapi/server.py

        Given a flask request instance, snag a couple of expected header items
    """
    timestamp = request.headers.get('X-Slack-Request-Timestamp', '')
    signature = request.headers.get('X-Slack-Signature', '')
    if not timestamp or not signature:
        raise ValueError('Invalid request/credentials')

    # from gcp-github-app helpers/signature.py ->validateGithubSignature function
    # HMAC requires its key to be bytes, but data is strings.
    #mac = hmac.new(secret, msg=request.data, digestmod=hashlib.sha256)
    #return hmac.compare_digest(mac.hexdigest(), signature)

    tse = str.encode(f'v0:{timestamp}:')
    payload = tse + request.get_data()
    #payload = str.encode('v0:{}:'.format(timestamp)) + request.get_data()

    secret = str.encode(config['SLACK_SECRET'])
    request_digest = hmac.new(secret, payload, hashlib.sha256).hexdigest()
    request_hash = f'v0={request_digest}'

    if not hmac.compare_digest(request_hash, signature):
        raise ValueError('Invalid request/credentials')

    print('request signature indicates valid Slack origination')
    return True
