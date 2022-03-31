import logging
import os, sys
from pathlib import Path

formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')

app_loggers = {}
error_loggers = {}


# -----------------------------------------------------------
# Set Up logger and create log directory
# -----------------------------------------------------------
def setup_logger(name, log_file, level=logging.INFO, log_sys_type=sys.stdout):
    """To setup as many loggers as you want"""
    
    log_path = Path(log_file)
    log_dir = log_path.parent
    print("log_path {}, log_dir {}".format(log_path, log_dir))
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    handler = logging.FileHandler(log_file)
    handler.setFormatter(formatter)

    if log_sys_type is not None:
        sout_handler = logging.StreamHandler(log_sys_type)
        sout_handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)
    if log_sys_type is not None:
        logger.addHandler(sout_handler)

    return logger

# -----------------------------------------------------------
# Get logger info from global variables
# -----------------------------------------------------------
def get_app_logger(logger_name, log_file="log/app.log"):
    global app_loggers

    if app_loggers.get(logger_name):
        return app_loggers.get(logger_name)
    else:
        app_logger = setup_logger(logger_name, log_file)
        app_loggers[logger_name] = app_logger
        return app_logger

# -----------------------------------------------------------
# Get logger error from global variables
# -----------------------------------------------------------
def get_error_logger(logger_name, log_file="log/error.log"):
    global error_loggers

    if error_loggers.get(logger_name):
        return error_loggers.get(logger_name)
    else:
        error_logger = setup_logger(logger_name, log_file, level=logging.ERROR, log_sys_type=None)
        error_loggers[logger_name] = error_logger
        return error_logger