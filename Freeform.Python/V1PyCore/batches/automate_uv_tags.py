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
        
        # if "heads" in file_path:
            # return
        
        # Batch Functionality Goes Here
        core_node = metadata.meta_network_utils.get_network_core()
        core_network = metadata.meta_network_utils.create_from_node(core_node)
        imported_network = core_network.get_downstream(ImportedCore)
        
        if imported_network:
            import_list = imported_network.get_connections()
            skeleton_list = pm.ls(import_list, type='joint')
            transform_list = [x for x in import_list if x not in skeleton_list]
            transform_list = list(set(transform_list))
            existing_uv_property = None
            for obj in transform_list:
                meta_type_list = [x.get() for x in obj.listAttr(ud=True) if 'meta_type' in x.name()]
                if any([x for x in meta_type_list if "EditUVProperty" in x]):
                    existing_uv_property = True
                if existing_uv_property:
                    break
            if transform_list and not existing_uv_property:
                uv_property = metadata.meta_properties.EditUVProperty()
                uv_property.connect_nodes(transform_list)
                
                if 'legs' in file_path or 'eyes' in file_path or 'base_skin' in file_path:
                    uv_property.set_lower_half()
                elif 'torso' in file_path or 'hair' in file_path or 'heads' in file_path:
                    uv_property.set_upper_half()
                
                if 'eyes' in file_path or 'hair' in file_path:
                    mat_name = "hair_eyes"
                elif 'base_skin' in file_path or 'heads' in file_path:
                    mat_name = "skin"
                else:
                    mat_name = "clothes"
                uv_property.set('material_name', mat_name)
                
                uv_property.bake_to_connected()
                
                pm.select(transform_list[0], r=True)
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
for file_path in file_list[1:]:
    pm.newFile(force=True)
    print(file_path)
    if(extension_arg == ".ma"):
        pm.openFile(file_path, f=True)
    else:
        maya_utils.scene_utils.import_file_safe(file_path, tag_imported=True, returnNewNodes=True)
    file_commands(file_path, batch_dir, extension_arg)