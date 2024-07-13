import os
import sys



def main():
    sys.path.append(os.path.join(os.environ['V1TOOLSROOT'], 'V1.Python', 'V1PyCore'))

    import v1_core
    v1_core.dotnet_setup.init_dotnet() # Fails on initial mayapy initialization, so re-run it

    import Freeform.Core
    import System

    file_list = []
    output_path = os.path.join(v1_core.global_settings.GlobalSettings.get_user_freeform_folder(), "_ue_existing_files.txt")
    with open(output_path, "r") as f:
        file_list = f.readlines()
        f.close()

    p4_missing_file_list = []
    for file in [x for x in file_list if x.strip()]:
        status = Freeform.Core.Helpers.Perforce.FileStatus(file.strip())
        if status == None:
            exportList = System.Collections.Generic.List[str]()
            exportList.Add(file.replace('\\\\', '\\'))
            path_exists = os.path.exists(file.replace('\\\\', '\\'))
            added_list = []
            err = ""
            try:
                added_list = Freeform.Core.Helpers.Perforce.AddFiles(exportList)
            except Exception as e:
                err = e
            
            success = "Failed to Add" if not added_list else "Added to Default Changelist"
            p4_missing_file_list.append(file.strip() + "  =>  " + success + "\n")

    output_path = os.path.join(v1_core.global_settings.GlobalSettings.get_user_freeform_folder(), "_ue_p4_added_files.txt")
    with open(output_path, "w") as f:
        f.truncate(0)
        f.writelines(p4_missing_file_list)
        f.close()
    
if __name__ == "__main__":
    main()