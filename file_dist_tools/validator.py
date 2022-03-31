import configparser

from loggingFileDist import get_app_logger, get_error_logger

app_logger = get_app_logger("app_info")
error_logger = get_error_logger("app_error")

RDP_KEY  = "RDP"
GLOBAL_KEY = "CFS_GLOBAL"
CONFIG_KEY = "CFS_CONFIG"
CFS_FILE_KEY = "CFS_FILES"

GLOBAL_CONFIG_FILE = "global.ini"

# -----------------------------------------------------------
# Validate user input from global configuration file (global.ini)
# -----------------------------------------------------------
def validate_global_config(user_request):
    config = configparser.ConfigParser()
    config.read(GLOBAL_CONFIG_FILE)

    # Check Require field
    if "username" not in config[RDP_KEY] or "password" not in config[RDP_KEY] or "clientId" not in config[RDP_KEY]:
        raise Exception("ERROR: Please specify 'username', 'password' and 'clientId' on your global configuration file: {}".format(GLOBAL_CONFIG_FILE))

    # Check Require field
    if "bucketName" not in config[GLOBAL_KEY] or "packageId" not in config[GLOBAL_KEY]:
        raise Exception("ERROR: Please specify 'bucketName' and 'packageId' on your global configuration file: {}".format(GLOBAL_CONFIG_FILE))
    
    for key, value in config[GLOBAL_KEY].items():
        user_request[key] = value
        if value is None or value == "":
            raise Exception("ERROR: Please specify '{}' on your global configuration file name : {}".format(key, GLOBAL_CONFIG_FILE))
        if key == "attributes":
            attributes = []
            attributes_list = [item.strip() for item in value.split(',')]
            for attribute in attributes_list:
                value = attribute.split('=')
                attribute_dict = { "name" : value[0], "value" : value[1]}
                attributes.append(attribute_dict)
            user_request[key] = attributes

# -----------------------------------------------------------
# Validate user input from configuration file (config.ini)
# -----------------------------------------------------------
def validate_config(config_file, user_request):
    config = configparser.ConfigParser()
    config.read(config_file)

    # Check Require field
    if "filesetName" not in config[CONFIG_KEY]:
        raise Exception("ERROR: Please specify 'filesetName' on your configuration file name : {}".format(config_file))
    
    for key, value in config[CONFIG_KEY].items():
        user_request[key] = value

    files = []

    if len(config[CFS_FILE_KEY].items()) > 10:
        raise Exception("ERROR: Please check [{}], This tools support only 10 files per config".format(CFS_FILE_KEY))
    
    for key, value in config[CFS_FILE_KEY].items():
        file_raw =  key + ":" + value
        file_list = file_raw.split(",")
        file_input = {}
        if len(file_list) < 3:
            raise Exception("ERROR: Please check [{}] section in {} should be FileName,S3Url,\"File Description\",FileSizeInBytes(optional)".format(CFS_FILE_KEY, config_file))
        if len(file_list) == 4:
            try:
                file_input["filesizeinbytes"] = int(file_list[3]) # filesizeinbytes is optional field
            except Exception as e:
                app_logger.error(e, exc_info=True)
                error_logger.error(e, exc_info=True)
                raise Exception("ERROR: Please check 'fileSizeInBytes' value,  'fileSizeInBytes' should be number only")
        if len(file_list) == 3:
            try:
                file_input["description"] =  file_list[2][1:-1] # Remove double quote in first and last index string "<description input>"
            except Exception as e:
                app_logger.error(e, exc_info=True)
                error_logger.error(e, exc_info=True)
                raise Exception("ERROR: Please check 'description' value,  'description' should be specify \"\" like an example \"your description\"")
        file_input["filename"]    = file_list[0]
        file_input["s3url"]       = file_list[1]
        
        files.append(file_input)
    user_request["files"] = files

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
            attribute_dict = { "name" : value[0], "value" : value[1]}
            attributes.append(attribute_dict)
        user_request["attributes"] = attributes

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

    if args.filesizeinbytes is not None:
        try:
            user_request["filesizeinbytes"] = int(args.filesizeinbytes) # filesizeinbytes is optional field
        except Exception as e:
            app_logger.error(e, exc_info=True)
            error_logger.error(e, exc_info=True)
            raise Exception("ERROR: Please check 'fileSizeInBytes' value,  'fileSizeInBytes' should be number only")