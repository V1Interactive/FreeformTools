import sys
import os
from pathlib import Path


def get_file_list():
    # If this was run from commandline with a parameter use the parameter as the file path

    file_arg = sys.argv[1] if len(sys.argv) > 1 else None
    extension_arg = sys.argv[2] if len(sys.argv) > 2 else ".ma"
    if file_arg is None:
        return []

    file_path = Path(file_arg)
    return_file_list = []
    if file_path.exists():
        # If we passed in a file read it
        if file_path.suffix:
            with open(file_arg) as f:
                content = f.readlines()
            return_file_list = [x.strip() for x in content] 
        # if we passed in a directory walk it and gather maya files
        else:
            for root, dir_list, file_list in os.walk(file_arg):
                print(root)
                for file in [f for f in file_list if Path(f).suffix == extension_arg]:
                    file_path = os.path.join(root, file)
                    return_file_list.append(file_path)

    return (return_file_list, file_arg, extension_arg)

def file_commands(batch_dir, extension_arg):
    try:
        import pymel.core as pm
        import v1_core
        
        # Batch Functionality Goes Here

    except Exception as err:
        print(err)
        exception_text = v1_core.exceptions.get_exception_message()

        split_dir = os.path.splitext(batch_dir)
        fail_dir = os.path.join(split_dir[0], "batch_fails")
        if not os.path.exists(fail_dir):
            os.makedirs(fail_dir)

        folder_list = split_dir[0].split(os.path.sep)
        error_file_name = '_'.join([x for x in str(pm.sceneName()).split('/') if x not in folder_list])
        text_error_path = os.path.join(fail_dir, error_file_name.replace(extension_arg, '.txt'))
        if not os.path.exists(os.path.dirname(text_error_path)):
            os.makedirs(os.path.dirname(text_error_path))
        f = open(text_error_path,"w+")
        f.write(exception_text)
        f.close()

        print(exception_text)


def main():
    ## In UI For Testing
    #import pymel.core as pm

    #file_list, batch_dir = get_file_list()
    #for file in file_list:
    #    print(file)
    #    pm.openFile(file, f=True)
    #    file_commands(batch_dir)

    # Standalone
    import maya.standalone
    maya.standalone.initialize()
    try:
        import v1_core
        v1_core.dotnet_setup.init_dotnet(["HelixDCCTools", "HelixResources", "Freeform.Core", "Freeform.Rigging"]) # Sometimes fails on initial mayapy initialization, so re-run it
        v1_core.environment.set_environment()

        import pymel.core as pm

        print("==============================================")
        print("============== STARTING BATCH ================")
        print("==============================================")
        file_list, batch_dir, extension_arg = get_file_list()
        for file in file_list:
            print("==============================================")
            print("================ WORKING ON ==================")
            print("==============================================")
            print(file)
            #pm.openFile(file, f=True)
            #file_commands(batch_dir, extension_arg)
    except:
        pass
    finally:
        maya.standalone.uninitialize()
    
if __name__ == "__main__":
    main()