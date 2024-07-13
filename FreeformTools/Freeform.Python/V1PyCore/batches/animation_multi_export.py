import os
import sys
import time
import subprocess


def get_file_list():
    pycore_path = os.path.join(os.environ["V1TOOLSROOT"], "Freeform.Python", "V1PyCore")
    sys.path.append(pycore_path)
    import v1_core
    export_list_directory = ''
    # If an arg is passed in it is the path or relative path to the directory to look for export_file_list's in
    if len(sys.argv) > 1:
        export_list_directory = sys.argv[1]
        if ".." in export_list_directory:
            config_manager = v1_core.global_settings.ConfigManager()
            data_path = config_manager.get_content_path()
            export_list_directory = arg_path.replace("..", data_path)

    export_files = []
    if os.path.exists(export_list_directory):
        export_files = [os.path.join(export_list_directory, x) for x in os.listdir(export_list_directory) if "export_file_list" in x]
    
    return (export_files, export_list_directory)

def main():
    print("RUNNING MULTI EXPORT")
    export_files, export_list_directory = get_file_list()
    if export_files:
        for file in export_files:
            maya_py_cmd = "start W:\\\"Program Files\"\\Autodesk\\Maya2022\\bin\\mayapy.exe %V1TOOLSROOT%\\Freeform.Python\\V1PyCore\\batches\\animation_export.py {0}".format(file)
            os.system(maya_py_cmd)
    else:
        maya_py_cmd = "start W:\\\"Program Files\"\\Autodesk\\Maya2022\\bin\\mayapy.exe %V1TOOLSROOT%\\Freeform.Python\\V1PyCore\\batches\\animation_export.py {0}".format(export_list_directory)
        os.system(maya_py_cmd)

    
if __name__ == "__main__":
    main()