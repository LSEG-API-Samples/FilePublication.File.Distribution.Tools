import requests
import os
import rdpToken
import copy
import argparse
import json
import configparser
from json import JSONDecodeError
from retry import retry

from loggingFileDist import get_app_logger, get_error_logger
from validator import validate_argument, validate_config, validate_global_config
from exceptions import *

file_distribution_url = "file-store"
file_distribution_version = "v1"

app_logger = get_app_logger("app_info")
error_logger = get_error_logger("app_error")

GLOBAL_CONFIG_FILE = "global.ini"
RETRY_CONFIG_KEY = "RETRY_CONFIG"
config = configparser.ConfigParser(defaults={
    "RETRY_LIMIT": 3,
    "RETRY_DELAY": 1,
    "RETRY_BACKOFF": 2
})
config.read(GLOBAL_CONFIG_FILE)
RETRY_LIMIT = int(config.get(RETRY_CONFIG_KEY, "RETRY_LIMIT"))
RETRY_DELAY = int(config.get(RETRY_CONFIG_KEY, "RETRY_DELAY"))
RETRY_BACKOFF = int(config.get(RETRY_CONFIG_KEY, "RETRY_BACKOFF"))


# -----------------------------------------------------------
#  Print JSON data with user friendly format
# -----------------------------------------------------------
def print_json_format(json_response):
    for key, value in json_response.items():
        if key == "error":
            for err_key, err_value in value.items():
                app_logger.info("\t{:<8} : {:<15}".format(err_key, str(err_value)))

        elif isinstance(value, list):
            if len(value) == 0:
                app_logger.info("\t{:<15} : {:<15}".format(key, "[]"))
            elif len(value) == 1:
                app_logger.info("\t{:<15} : {:<15}".format(key, str(value)))
            else:
                app_logger.info("\t{:<15} : {:<15}".format(key, "["))
                list_size = len(value)
                for idx, item in enumerate(value):
                    comma_symbols = "" if ((idx + 1) == list_size) else ","
                    app_logger.info("\t{:<15}    {:<15}{}".format("", str(item), comma_symbols))
                app_logger.info("\t{:<15}   {:<15}".format("", "]"))
        else:
            app_logger.info("\t{:<15} : {:<15}".format(key, str(value)))


# -----------------------------------------------------------
# Make a request to publish file to File Distribution API
# -----------------------------------------------------------
@retry(CFSServerException, tries=RETRY_LIMIT, delay=RETRY_DELAY, backoff=RETRY_BACKOFF)
def publish_file(payload):
    app_logger.info("Publishing file . . .")
    access_token = rdpToken.getToken()

    url = "{}/{}/{}/bulk-publish".format(rdpToken.base_URL, file_distribution_url, file_distribution_version)

    headers = {
        "Authorization": "Bearer {}".format(access_token),
        "Content-Type": "application/json"
    }
    response = requests.post(url,
                             json=payload,
                             headers=headers)

    if response.status_code == 201:
        json_response = json.loads(response.text)
        app_logger.info("****************** Publish file successfully *******************")
        app_logger.info("------------------- File Publication Result --------------------")
        print_json_format(json_response)
        app_logger.info("----------------------------------------------------------------")
    # 429: too many request | 500: internal error
    if response.status_code == 429 or response.status_code>= 500:
        app_logger.info("-------------------- File Publication Error --------------------")
        app_logger.info("Failed to publish file, retry to publish again")
        try:
            json_response = json.loads(response.text)
            print_json_format(json_response)
        except JSONDecodeError as e:
            # log in plain value
            app_logger.error(f"Got status code {response.status_code}, message: {response.text}")
            error_logger.error(f"Got status code {response.status_code}, message: {response.text}")
        finally:
            app_logger.info("----------------------------------------------------------------")
            raise CFSServerException("Failed to publish file", payload, response.text)
    else:
        app_logger.info("-------------------- File Publication Error --------------------")
        app_logger.info("Failed to publish file, got status code {} !!!".format(response.status_code))
        try:
            json_response = json.loads(response.text)
            print_json_format(json_response)
        except JSONDecodeError as e:
            # log in plain value
            app_logger.error(f"Got status code {response.status_code}, message: {response.text}")
            error_logger.error(f"Got status code {response.status_code}, message: {response.text}")
        finally:
            app_logger.info("----------------------------------------------------------------")
            raise CFSInvalidInputException("Failed to publish file", payload, response.text)


# -----------------------------------------------------------
# Mapping user request to File request schema
# -----------------------------------------------------------
def modify_file_request(user_request):
    files = []

    file_payload = {
        "fileType": "file",
        "storageLocation": {
            "url": "",
            "@type": "s3",
            "roleArn": ""
        },
        "filename": "",
        "description": "",
        "fileSizeInBytes": 0
    }

    if "files" in user_request:
        for file_input in user_request["files"]:
            file_request = copy.deepcopy(file_payload)
            file_request["storageLocation"]["url"] = file_input["s3url"]
            file_request["filename"] = file_input["filename"]

            if "rolearn" in file_input:
                file_request["storageLocation"]["roleArn"] = file_input["rolearn"]
            else:
                del file_request["storageLocation"]["roleArn"]

            if "description" in file_input:
                file_request["description"] = file_input["description"]
            else:
                del file_request["description"]

            if "filesizeinbytes" in file_input:
                file_request["fileSizeInBytes"] = int(file_input["filesizeinbytes"])
            else:
                del file_request["fileSizeInBytes"]

            files.append(file_request)
    else:
        file_payload["storageLocation"]["url"] = user_request["s3url"]
        file_payload["filename"] = user_request["filename"]

        if "roleArn" in user_request:
            file_payload["storageLocation"]["roleArn"] = user_request["roleArn"]
        else:
            del file_payload["storageLocation"]["roleArn"]

        if "description" in user_request:
            file_payload["description"] = user_request["description"]
        else:
            del file_payload["description"]

        if "filesizeinbytes" in user_request:
            file_payload["fileSizeInBytes"] = int(user_request["filesizeinbytes"])
        else:
            del file_payload["fileSizeInBytes"]
        files.append(file_payload)
    return files


# -----------------------------------------------------------
# Create payload from user request to publish file
# -----------------------------------------------------------
def create_payload(user_request):
    
    files = modify_file_request(user_request)
    payload = {
        "filesetName": user_request["filesetname"],
        "bucketName": user_request["bucketname"],
        "packageId": user_request["packageid"],
        "files": files
    }

    # Optional Field
    if "rolearn" in user_request:
        payload["rolearn"] = user_request["rolearn"]
    if "availablefrom" in user_request:
        payload["availableFrom"] = user_request["availablefrom"]
    if "availableto" in user_request:
        payload["availableTo"] = user_request["availableto"]
    if "contentfrom" in user_request:
        payload["contentFrom"] = user_request["contentfrom"]
    if "contentto" in user_request:
        payload["contentTo"] = user_request["contentto"]
    if "attributes" in user_request:
        payload["attributes"] = user_request["attributes"]
    return payload


# -----------------------------------------------------------
# Read current user from save to config file
# -----------------------------------------------------------
def load_current_user():
    user_object = None
    try:
        '''
        {
            "username": "GE-XXX"
        }
        '''
        # read the token from a file
        tf = open("current_user.json", "r+")
        user_object = json.load(tf)["username"]
        tf.close()
        app_logger.info("successfully get current user: {}".format(user_object))
    except Exception:
        pass

    return user_object


# -----------------------------------------------------------
# Read user input and checking user option for publish file
# -----------------------------------------------------------
def read_args():
    try:
        app_logger.info("################################################################")
        # Read arguments from command line
        args = parser.parse_args()

        user_request = {}
        # Validate global file
        app_logger.info("Validating {} . . .".format(GLOBAL_CONFIG_FILE))
        validate_global_config(user_request)
        app_logger.info("Validation result for {}  : passed".format(GLOBAL_CONFIG_FILE))

        # file input option
        if args.config:
            # Validate require input
            app_logger.info("Validating {} . . .".format(args.config))
            validate_config(args.config, user_request)
            app_logger.info("Validation result for {}  : passed".format(args.config))

        else:
            # Validate require input
            app_logger.info("Validating user arguments . . .")
            validate_argument(args, user_request)
            app_logger.info("Validation result for {}  : passed".format("user arguments"))

        app_logger.info("---------------- File Publication Request ----------------")
        print_json_format(user_request)
        app_logger.info("----------------------------------------------------------")

        app_logger.info("Creating user payload . . .")
        payload = create_payload(user_request)
        app_logger.info("User payload are created!!")

        publish_file(payload)
        app_logger.info("################################################################")

    except Exception as err:
        app_logger.error(err, exc_info=True)
        error_logger.error(err, exc_info=True)
        app_logger.info("program exit")


if __name__ == "__main__":
    description = """File Distribution Publication Tool description
    1) publish single file
     - python publishFile.py -fs <file-set name> -fn <file name> -s3url <s3url>
    or
     - python publishFile.py --filesetname <file-set name> --filename <file name> --s3url <s3url>

    2) publish single file with full detail
     - python publishFile.py -fs <file-set name> -fn <file name> -s3url <s3url> -rn <rolearn>
       -a <attributes> -cf <content from> -ct <content to> -af <available from> -at <available to> 
       -fd <file description> -sb <file size in bytes>
    or
     - python publishFile.py --filesetname <file-set name> --filename <file name> --s3url <s3url> 
       --rolearn <rolearn> --attributes <attributes> --contentfrom <content from> --contentto <content to> 
       --availablefrom <available from> --availableto <available to> --description <file description> 
       --filesizeinbytes <file size in bytes>

    3) publish multiple file
    - python publishFile.py -c config.ini`
    """

    # Initialize parser
    parser = argparse.ArgumentParser(description=description, formatter_class=argparse.RawTextHelpFormatter)

    # Adding optional argument

    parser.add_argument("-c", "--config", help="specify your configuration file")

    parser.add_argument("-fs", "--filesetname", help="specify file-set name")

    parser.add_argument("-fn", "--filename", help="specify file name")

    parser.add_argument("-s3url", "--s3url", help="specify file description")

    parser.add_argument("-rn", "--rolearn", help="specify role arn for s3 file access")

    parser.add_argument("-a", "--attributes", help="specify file-set attributes example DayOfWeek,product")

    parser.add_argument("-cf", "--contentfrom", help="specify file-set content from")

    parser.add_argument("-ct", "--contentto", help="specify file-set content to")

    parser.add_argument("-af", "--availablefrom", help="specify file-set available from")

    parser.add_argument("-at", "--availableto", help="specify file-set available to")

    parser.add_argument("-fd", "--description", help="specify file description")

    parser.add_argument("-sb", "--filesizeinbytes", help="specify file size in bytes")

    try:
        username = rdpToken._loadCredentialsFromFile()
        user_results = load_current_user()
        if user_results is None or str(user_results).strip() == '' or str(user_results) != username:
            if os.path.exists("token.txt"):
                app_logger.info(
                    "Remove token.txt because user_results {} match with criteria compare with {}".format(user_results,
                                                                                                          username))
                os.remove("token.txt")
    except Exception as err:
        app_logger.error(err, exc_info=True)
        error_logger.error(err, exc_info=True)

    read_args()


