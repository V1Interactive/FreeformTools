import os
import sys
import time
import subprocess

import v1_core


def get_file_list():
    file_list_directory = os.path.join(os.path.expanduser("~"), "Documents", "batch")
    # If an arg is passed in it is the relative path to the directory to look for export_file_list's in
    if len(sys.argv) > 1:
        config_manager = v1_core.global_settings.ConfigManager()
        data_path = config_manager.content_root_path()
        arg_path = sys.argv[1]
        file_list_directory = arg_path.replace("..", data_path)

    export_file_list = [os.path.join(file_list_directory, x) for x in os.listdir(file_list_directory) if "export_file_list" in x]
    
    return export_file_list 

def main():
    for file in get_file_list():
        maya_py_cmd = "start C:\\\"Program Files\"\\Autodesk\\Maya2018\\bin\\mayapy.exe %V1TOOLSROOT%\\V1.Python\\Maya\\batches\\cinematic_anim_check.py {0}".format(file)
        os.system(maya_py_cmd)
    
if __name__ == "__main__":
    main()
