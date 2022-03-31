#=============================================================================
# Refinitiv Data Platform demo app to get OAuth access tokens
# Following sequence is followed:
#   1. Read access token from the already created token file, if the token is not expired
#   2. Try using refresh token, if token is expired
#   3. Try to use password grant if refresh token fails, or no token file exists
#   For password grant:
#       a. Use credentials file, if available
#       b. Use the command line parameters, if available
#       c. Use the hardcoded USERNAME, PASSWORD parameters from this module
#
# CLIENT_ID see instructions at https://developers.refinitiv.com/en/api-catalog/refinitiv-data-platform/refinitiv-data-platform-apis/quick-start
#-----------------------------------------------------------------------------
#   This source code is provided under the Apache 2.0 license
#   and is provided AS IS with no warranty or guarantee of fit for purpose.
#   Copyright (C) 2021 Refinitiv. All rights reserved.
#=============================================================================
import requests, json, time, getopt, sys, configparser, traceback
from loggingFileDist import get_app_logger, get_error_logger

app_logger = get_app_logger("app_info")
error_logger = get_error_logger("app_error")

# User Credentials
USERNAME  = "---YOUR PROVIDED RDP MACHINE ID---"
PASSWORD  = "---YOUR PASSWORD---"
CLIENT_ID = "---YOUR GENERATED CLIENT ID---"

# Application Constants
base_URL = "https://api.refinitiv.com"
category_URL = "/auth/oauth2"
RDP_version = "/v1"
endpoint_URL = "/token"
CLIENT_SECRET = ""
SCOPE = "trapi"

CREDENTIALS_FILE = "global.ini"
TOKEN_FILE = "token.txt"


#==============================================
def _loadCredentialsFromFile():
#==============================================
    global USERNAME, PASSWORD, CLIENT_ID
    try:
        config = configparser.ConfigParser()
        config.read(CREDENTIALS_FILE)

        USERNAME = config['RDP']['username']
        PASSWORD = config['RDP']['password']
        CLIENT_ID = config['RDP']['clientId']

        app_logger.info("Read credentials from file")
    except Exception as e:
        # ignore if no creds file
        app_logger.error(e, exc_info=True)
        error_logger.error(e, exc_info=True)
        pass
    return USERNAME


#==============================================
def _requestNewToken(refreshToken):
#==============================================
    # try to read user credentials from a file
    _loadCredentialsFromFile()
    TOKEN_ENDPOINT = base_URL + category_URL + RDP_version + endpoint_URL

    if refreshToken is None:
        # formulate the request payload
        tData = {
            "username": USERNAME,
            "password": PASSWORD,
            "grant_type": "password",
            "scope": SCOPE,
            "takeExclusiveSignOnControl": "true"
        }
    else:
        tData = {
            "refresh_token": refreshToken,
            "grant_type": "refresh_token",
        }

    # Make a REST call to get latest access token
    response = requests.post(
        TOKEN_ENDPOINT,
        headers={
            "Accept": "application/json"
        },
        data=tData,
        auth=(
            CLIENT_ID,
            CLIENT_SECRET
        )
    )

    if (response.status_code == 400) and ('invalid_grant' in response.text):
        app_logger.error("Sleep 5 seconds, Failed to get access token {0} - {1}".format(response.status_code, response.text))
        error_logger.error("Sleep 5 seconds, Failed to get access token {0} - {1}".format(response.status_code, response.text))
        time.sleep(5)
        return None

    if response.status_code != 200:
        app_logger.error("Sleep 5 seconds, Failed to get access token {0} - {1}".format(response.status_code, response.text))
        error_logger.error("Sleep 5 seconds, Failed to get access token {0} - {1}".format(response.status_code, response.text))
        time.sleep(5)
        raise Exception("Failed to get access token {0} - {1}".format(response.status_code, response.text))

    # return the new token
    return json.loads(response.text)


#==============================================
def _saveToken(tknObject):
#==============================================
    tf = open(TOKEN_FILE, "w+")
    app_logger.info("Saving the new token")
    # append the expiry time to token
    tknObject["expiry_tm"] = time.time() + int(tknObject["expires_in"]) - 10
    # store it in the file
    json.dump(tknObject, tf, indent=4)
    tf.close()

    username = _loadCredentialsFromFile()
    user_data = {
        "username": username
    }
    user_file = open("current_user.json", "w+")
    app_logger.info("Saving the current user: {}".format(username))
    # store it in the file
    json.dump(user_data, user_file, indent=2)
    user_file.close()


#==============================================
def _loadToken():
#==============================================
    tknObject = None
    try:
        # read the token from a file
        tf = open(TOKEN_FILE, "r+")
        tknObject = json.load(tf)
        tf.close()
        app_logger.info("Existing token read from: " + TOKEN_FILE)
    except Exception:
        pass

    return tknObject


#==============================================
def changePassword(user, oldPass, clientID, newPass):
#==============================================
    TOKEN_ENDPOINT = base_URL + category_URL + RDP_version + endpoint_URL

    tData = {
        "username": user,
        "password": oldPass,
        "grant_type": "password",
        "scope": SCOPE,
        "takeExclusiveSignOnControl": "true",
        "newPassword": newPass
    }

    # make a REST call to get latest access token
    response = requests.post(
        TOKEN_ENDPOINT,
        headers = {
            "Accept": "application/json"
        },
        data = tData,
        auth = (
            clientID,
            CLIENT_SECRET
        )
    )

    if response.status_code != 200:
        app_logger.error("Failed to change password {0} - {1}".format(response.status_code, response.text))
        error_logger.error("Failed to change password {0} - {1}".format(response.status_code, response.text))
        raise Exception("Failed to change password {0} - {1}".format(response.status_code, response.text))

    tknObject = json.loads(response.text)
    # persist this token for future queries
    _saveToken(tknObject)
    # return access token
    return tknObject["access_token"]


#==============================================
def getToken():
#==============================================
    tknObject = _loadToken()

    if tknObject is not None:
        # is access token valid
        if tknObject["expiry_tm"] > time.time():
            _loadCredentialsFromFile()
            # return access token
            return tknObject["access_token"]

        app_logger.info("Token expired, refreshing a new one...")

        # get a new token using refresh token
        tknObject = _requestNewToken(tknObject["refresh_token"])
        # if refresh grant failed
        if tknObject is None:
            app_logger.info("Refresh token expired, using Password Grant...")
            # use password grant
            tknObject = _requestNewToken(None)
    else:
        app_logger.info("Getting a new token using Password Grant...")
        tknObject = _requestNewToken(None)

    # persist this token for future queries
    _saveToken(tknObject)
    # return access token
    return tknObject["access_token"]



#==============================================
if __name__ == "__main__":	
#==============================================
    print("Getting OAuth access token...")
    try:
        opts, args = getopt.getopt(sys.argv[1:], "", ["user=", "password=", "client_id=", "auth_url=", "version="])
    except getopt.GetoptError:
        print('Usage: python rdpToken.py [--user user] [--password password] [--client_id client_id]')
        sys.exit(2)
    for opt, arg in opts:
        if opt in "--user":
            USERNAME = arg
        elif opt in "--password":
            PASSWORD = arg
        elif opt in "--client_id":
            CLIENT_ID = arg
        elif opt in "--auth_url":
            base_URL = arg
        elif opt in "--version":
            RDP_version = arg
    accessToken = getToken()
    print("Received an access token")

