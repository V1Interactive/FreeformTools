'''
Freeform Rigging and Animation Tools
Copyright (C) 2020  Micah Zahm

Freeform Rigging and Animation Tools is free software: you can redistribute it 
and/or modify it under the terms of the GNU General Public License as published 
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Freeform Rigging and Animation Tools is distributed in the hope that it will 
be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Freeform Rigging and Animation Tools.  
If not, see <https://www.gnu.org/licenses/>.
'''

import logging
import logging.config # Max/Unreal don't catch this on import logging
import os
import shutil

'''
Error Levels:

CRITICAL	50
ERROR	40
WARNING	30
INFO	20
DEBUG	10
NOTSET	0
'''

def log_config(log_path):
    '''
    Create the configuration dictionary for the logging module

    Args:
        log_path (string): Full path to the file to log to
    '''
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "simple": {
                "format": "%(asctime)s - %(levelname)s - %(message)s"
            }
        },

        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": "INFO",
                "formatter": "simple",
                "stream": "ext://sys.stdout"
            },

            "debug_file_handler": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "DEBUG",
                "formatter": "simple",
                "filename": log_path,
                "maxBytes": 10485760,
                "backupCount": 20,
                "encoding": "utf8"
            }
        },

        "root": {
            "level": "DEBUG",
            "handlers": ["console", "debug_file_handler"]
        }
    }
    return config


def logging_wrapper(method, source_name, *args, **kwargs):
    '''
    Wrapper to log any individual method call

    Args:
        method (method): The method to wrap
        source_name (string): Name to tag into the logging file for this log
        args (args): Args for the method
        kwargs (kwargs): Kwargs for the method
    '''
    def method_wrap(*args, **kwargs):
        print_args = [x for x in args if (not type(x) == dict) and (not type(x) == list)]
        get_logger().debug("{0} -----> {1}.{2} ~~ Args:{2} Kwargs:{3}".format(source_name, method.__module__, method.__name__, print_args, kwargs))
        return method(*args, **kwargs)

    return method_wrap, args, kwargs


def setup_logging(log_name):
    '''
    Setup logging settings and log file, copy old log file to a backup, and create a new one

    Args:
        log_name (string): Name of the log file to output to
    '''
    user_dir = os.path.expanduser('~')
    user_dir = os.path.join(user_dir, 'V1') if "Documents" in user_dir else os.path.join(user_dir, 'Documents', 'V1')
    if not os.path.exists(user_dir):
        os.makedirs(user_dir)
    output_path = os.path.join(user_dir, '{0}_log.log'.format(log_name))

    if os.path.exists(output_path):
        shutil.copyfile(output_path, output_path.replace(log_name, log_name+"_bck"))
        try:
            os.remove(output_path)
        except Exception, e:
            pass

    logging.config.dictConfig(log_config(output_path))
    

def get_logger():
    '''
    Get the Singleton 'root' logger from logging module

    Returns:
        (Logger): Logger object
    '''
    logger = logging.getLogger()
    return logger