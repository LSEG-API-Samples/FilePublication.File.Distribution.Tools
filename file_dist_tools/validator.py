import configparser
import re

from loggingFileDist import get_app_logger, get_error_logger
from exceptions import *

app_logger = get_app_logger("app_info")
error_logger = get_error_logger("app_error")

RDP_KEY  = "RDP"
GLOBAL_KEY = "CFS_GLOBAL"
CONFIG_KEY = "CFS_CONFIG"
CFS_FILE_KEY = "CFS_FILES"

GLOBAL_CONFIG_FILE = "global.ini"
S3_URL_REGEX = "^https:\/\/(s3\.?[a-zA-Z0-9-]*|[a-zA-Z0-9-]*\.s3\.?[a-zA-Z0-9-]*|[" \
               "a-zA-Z0-9-]*\.mrap\.accesspoint\.s3-global)\.amazonaws\.com\/.*$"
ROLEARN_REGEX = "^arn:aws:iam::[0-9]+:role\/.+$"
CFS_FILES_FIELD_LIST = ["filename", "filetype", "description", "filesizeinbytes", "md5", "s3url", "rolearn"]


# -----------------------------------------------------------
# Validate user input from global configuration file (global.ini)
# -----------------------------------------------------------
def validate_global_config(user_request):
    config = configparser.ConfigParser()
    config.read(GLOBAL_CONFIG_FILE)

    # Check Require field
    if "username" not in config[RDP_KEY] or "password" not in config[RDP_KEY] or "clientId" not in config[RDP_KEY]:
        raise InvalidConfigurationException(GLOBAL_CONFIG_FILE,
                                            "Please specify 'username', 'password' and 'clientId' on your "
                                            "global configuration file")

    # Check Require field
    if "bucketName" not in config[GLOBAL_KEY] or "packageId" not in config[GLOBAL_KEY]:
        raise InvalidConfigurationException(GLOBAL_CONFIG_FILE,
                                            "Please specify 'bucketName' and 'packageId' on your "
                                            "global configuration file")

    for key, value in config[GLOBAL_KEY].items():
        user_request[key] = value
        if value is None or value == "":
            raise InvalidConfigurationException(GLOBAL_CONFIG_FILE,
                                                f"Please specify '{key}' on your global configuration file name ")
        if key == "attributes":
            attributes = []
            attributes_list = [item.strip() for item in value.split(',')]
            for attribute in attributes_list:
                value = attribute.split('=')
                attribute_dict = {"name": value[0], "value": value[1]}
                attributes.append(attribute_dict)
            user_request[key] = attributes


# -----------------------------------------------------------
# Validate user input from configuration file (config.ini)
# -----------------------------------------------------------
def validate_config(config_file, user_request):
    config = configparser.ConfigParser(allow_no_value=True)
    config.read(config_file)

    # Check Require field
    if "filesetName" not in config[CONFIG_KEY]:
        raise InvalidConfigurationException(config_file, "Please specify 'filesetName' on your configuration file name")

    for key, value in config[CONFIG_KEY].items():
        user_request[key] = value

    files = []

    cfs_file_config = list(config[CFS_FILE_KEY].items())
    if len(cfs_file_config) > 11:
        raise InvalidConfigurationException(config_file, f"Please check [{CFS_FILE_KEY}], "
                                                         f"This tools support only 10 files per config")

    column_list = map_column_list(cfs_file_config[0][0])
    for key, value in cfs_file_config[1:]:
        file_raw = key + ":" + value
        # use regex to split comma value ignoring double quote values
        file_list = re.split(r",(?=(?:[^\"]*\"[^\"]*\")*[^\"]*$)", file_raw)
        file_input = {}

        try:
            file_name = file_list[column_list.index("filename")]
            for i in range(0, len(file_list)):
                field_name = column_list[i]
                field_value = file_list[i].replace("\"", "")
                validate_field_value(file_name, field_name, field_value)
                # omit empty field value
                if len(field_value) > 0:
                    file_input[field_name] = field_value
            files.append(file_input)
        except IndexError:
            raise InvalidConfigurationException(config_file, f"Input has invalid column mapping on file: {file_name}")
    user_request["files"] = files


def map_column_list(header_column):
    columns = header_column.split(",")
    formatted_columns = list(map(lambda value: value.lower(), columns))

    if "filename" not in formatted_columns:
        raise InvalidConfigurationException(GLOBAL_CONFIG_FILE, "Required \"filename\" field is missing")

    if "s3url" not in formatted_columns:
        raise InvalidConfigurationException(GLOBAL_CONFIG_FILE, "Required \"s3url\" field is missing")
    return formatted_columns


# -----------------------------------------------------------
# Validate user input from python argument
# -----------------------------------------------------------
def validate_argument(args, user_request):
    # Require field
    if args.filesetname is not None:
        user_request["filesetname"] = args.filesetname
    else:
        raise Exception("ERROR: Please specify -fs <file-set name> or --filesetname <file-set name> ")
    # Require field
    if args.filename is not None:
        user_request["filename"] = args.filename
    else:
        raise Exception("ERROR: Please specify -fn <file name> or --filename <file name> ")

    # Require field
    if args.s3url is not None:
        user_request["s3url"] = args.s3url
    else:
        raise Exception("ERROR: Please specify  -s3url <S3 Url> or --s3url <S3 Url> ")

    # Optional field
    if args.attributes is not None:
        # overide global config
        attributes = []
        attributes_list = [item.strip() for item in args.attributes.split(',')]
        for attribute in attributes_list:
            value = attribute.split('=')
            attribute_dict = {"name": value[0], "value": value[1]}
            attributes.append(attribute_dict)
        user_request["attributes"] = attributes

    # Optional field
    if args.rolearn is not None:
        user_request["roleArn"] = args.rolearn

    # Optional field
    if args.contentfrom is not None:
        # overide global config
        user_request["contentfrom"] = args.contentfrom

    # Optional field
    if args.contentto is not None:
        # overide global config
        user_request["contentto"] = args.contentto

    # Optional field
    if args.availablefrom is not None:
        user_request["availablefrom"] = args.availablefrom

    # Optional field
    if args.availableto is not None:
        user_request["availableto"] = args.availableto

    # Optional field
    if args.description is not None:
        user_request["description"] = args.description

    # Optional field
    if args.filesizeinbytes is not None:
        try:
            user_request["filesizeinbytes"] = int(args.filesizeinbytes)
        except ValueError:
            raise InvalidFieldValueException(None, "filesizeinbytes", args.filesizeinbytes, "value should be numeric value")


def validate_field_value(file_name, field_name, field_value):
    if field_name not in CFS_FILES_FIELD_LIST:
        raise UnrecognizedFieldException(field_name)

    if field_name == "filename":
        if len(field_value) < 1:
            raise InvalidFieldValueException(file_name, field_name, field_value, "should not be empty")

    if field_name == "filesizeinbytes":
        try:
            if len(field_value) > 0:
                int(field_value)
        except ValueError:
            raise InvalidFieldValueException(file_name, field_name, field_value, "value should be numeric value")

    if field_name == "s3url":
        if re.match(S3_URL_REGEX, field_value) is None:
            raise InvalidFieldValueException(file_name,field_name, field_value,
                                             "value should be valid s3 object url (eg. "
                                             "https://bucket.s3.amazonaws.com/key)")

    if field_name == "rolearn":
        if re.match(ROLEARN_REGEX, field_value) is None and len(field_value) > 0:
            raise InvalidFieldValueException(file_name, field_name, field_value,
                                             "value should be valid (eg. "
                                             "arn:aws:iam::123456789012:role/EdsCfsS3Access_role)")
