from pathlib import Path

import maya_utils
import rigging
from rigging.settings_binding import Binding_Sets


def get_file_list(file_arg, extension_arg):
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
                for file in [f for f in file_list if Path(f).suffix == extension_arg]:
                    file_path = os.path.join(root, file)
                    return_file_list.append(file_path)

    return (return_file_list, file_arg, extension_arg)
    
def file_commands(file_path, batch_dir, extension_arg):
    try:
        import pymel.core as pm
        import v1_core
        
        import metadata
        from metadata.network_core import ImportedCore
        
        if 'heads' in file_path:
            return    
        
        # Batch Functionality Goes Here
        core_node = metadata.meta_network_utils.get_network_core()
        core_network = metadata.meta_network_utils.create_from_node(core_node)
        imported_network = core_network.get_downstream(ImportedCore)
        
        if imported_network:
            import_list = imported_network.get_connections()
            skeleton_list = pm.ls(import_list, type='joint')
            #check_vector = pm.dt.Vector([9.13441276550293, 0.5546402931213379, 0.44310522079467773])
            check_vector = pm.dt.Vector([8.9632568359375, 0.6904257535934448, 0.4381442666053772])
            lip_vector = pm.PyNode("b_mouth_bottom").translate.get()
            if (lip_vector - check_vector).length() > 0.001:
                #settings_path = r"W:\Projects\Iterant_Games\Second Layer\Assets\Content\Characters\Human\base_female\heads\caucasian\caucasian_a_offset_settings.json"
                settings_path = r"W:\Projects\Iterant_Games\Second Layer\Assets\Content\Characters\Human\base_male\heads\caucasian\caucasian_a_offset_settings.json"
                rigging.file_ops.load_settings_from_json(skeleton_list[0], settings_path, Binding_Sets.TRANSFORMS.value, False, skeleton_list, False, False)
                
                pm.select(skeleton_list[0], r=True)
                # raise Exception
                maya_utils.scene_utils.re_export_from_selection()

    except Exception as err:
        print(err)
        exception_text = v1_core.exceptions.get_exception_message()

        split_dir = os.path.splitext(batch_dir)
        fail_dir = os.path.join(split_dir[0], "batch_fails")
        if not os.path.exists(fail_dir):
            os.makedirs(fail_dir)
            
        folder_list = split_dir[0].split(os.path.sep)
        error_file_name = Path(file_path).name
        text_error_path = os.path.join(fail_dir, error_file_name.replace(extension_arg, '.txt'))
        if not os.path.exists(os.path.dirname(text_error_path)):
            os.makedirs(os.path.dirname(text_error_path))
        f = open(text_error_path,"w+")
        f.write(exception_text)
        f.close()

        print(exception_text)
    
directory_path = r"W:\Projects\Iterant_Games\Second Layer\Assets\Content\Characters\Human\base_male"
file_list, batch_dir, extension_arg = get_file_list(directory_path, ".fbx")
for file_path in file_list:
    pm.newFile(force=True)
    print(file_path)
    if(extension_arg == ".ma"):
        pm.openFile(file_path, f=True)
    else:
        maya_utils.scene_utils.import_file_safe(file_path, tag_imported=True, returnNewNodes=True)
    file_commands(file_path, batch_dir, extension_arg)