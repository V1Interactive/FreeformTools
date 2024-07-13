import os
import sys
import time
import subprocess


def get_file_list():
    pycore_path = os.path.join(os.environ["V1TOOLSROOT"], "Freeform.Python", "V1PyCore")
    sys.path.append(pycore_path)
    
    export_list_directory = ""
    python_file = ""
    search_extension = ""
    # If an arg is passed in it is the path or relative path to the directory to look for export_file_list's in
    if len(sys.argv) > 1:
        export_list_directory = sys.argv[1]
        python_file = sys.argv[2]
        search_extension = sys.argv[3]

    export_files = []
    if os.path.exists(export_list_directory):
        export_files = [os.path.join(export_list_directory, x) for x in os.listdir(export_list_directory) if "export_file_list" in x]
    
    return (export_files, export_list_directory, python_file, search_extension)

def main():
    print("RUNNING MULTI EXPORT")
    export_files, export_list_directory, python_file, search_extension = get_file_list()
    if export_files:
        for file in export_files:
            maya_py_cmd = "start W:\\\"Program Files\"\\Autodesk\\MayaCreative2023\\bin\\mayapy.exe %V1TOOLSROOT%\\Freeform.Python\\V1PyCore\\batches\\{0} \"{1}\\\" {2}".format(python_file, file, search_extension)
            os.system(maya_py_cmd)
    else:
        maya_py_cmd = "start W:\\\"Program Files\"\\Autodesk\\MayaCreative2023\\bin\\mayapy.exe %V1TOOLSROOT%\\Freeform.Python\\V1PyCore\\batches\\{0} \"{1}\\\" {2}".format(python_file, export_list_directory, search_extension)
        os.system(maya_py_cmd)

    
if __name__ == "__main__":
    main()