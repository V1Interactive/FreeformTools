import site
import sys
import os
import random

def get_file_list():
    # If this was run from commandline with a parameter use the parameter as the file path

    file_arg = sys.argv[1] if len(sys.argv) > 1 else None
    if file_arg is None:
        return []

    return_file_list = []
    if os.path.exists(file_arg):
        # If we passed in a file read it
        if os.path.splitext(file_arg)[-1]:
            with open(file_arg) as f:
                content = f.readlines()
            return_file_list = [x.strip() for x in content] 
        # if we passed in a directory walk it and gather maya files
        else:
            for root, dir_list, file_list in os.walk(file_arg):
                for file in [f for f in file_list if os.path.splitext(f)[-1] == '.ma']:
                    file_path = os.path.join(root, file)
                    return_file_list.append(file_path)

    return (return_file_list, file_arg)

def file_commands(batch_dir):
    try:
        import pymel.core as pm
        import v1_core
        import maya_utils
        import metadata
        import exporter.usertools

        from metadata.exporter_properties import ExportDefinition, CharacterAnimationAsset, DynamicAnimationAsset

        #import rigging
        #import rigging.usertools
        #import metadata
        #from metadata.network_core import CharacterCore, JointsCore
        #from rigging.component_registry import Component_Registry

        #character_node = metadata.meta_network_utils.get_all_network_nodes(CharacterCore)[0]
        #character_network = metadata.meta_network_utils.create_from_node(character_node)
        #character_joint = character_network.get_downstream(JointsCore).get_connections()[0]
        #skeleton_dict = rigging.skeleton.get_skeleton_dict(character_joint)

        #fk_pelvis = Component_Registry().get('FK')()
        #fk_pelvis.rig(skeleton_dict, 'center', 'pelvis', world_space=True)

        #fk_spine = Component_Registry().get('FK')()
        #fk_spine.rig(skeleton_dict, 'center', 'spine', world_space=True)

        #rig_swapper = rigging.usertools.character_picker.RigSwapper([], character_node)
        #rig_fil_path = r"W:\Projects\2L_Games\Data\Characters\Human\base_female\rigging\base_female_rig.ma"
        #rig_swapper.import_rigs([rig_fil_path])

        #fk_pelvis.bake_and_remove()
        #fk_spine.bake_and_remove()

        #pm.saveFile(force=True)

        # If there's only 1 asset group, connect all export assets to it
        # This is to ensure cinematic batch exports always export everything
        export_definition_list = metadata.meta_network_utils.get_all_network_nodes(ExportDefinition)
        if len(export_definition_list) == 1:
            definition_network = metadata.meta_network_utils.create_from_node(export_definition_list[0])

            character_asset_list = metadata.meta_network_utils.get_all_network_nodes(CharacterAnimationAsset)
            dynamic_asset_list = metadata.meta_network_utils.get_all_network_nodes(DynamicAnimationAsset)

            connected_nodes = definition_network.get_connections()
            for anim_asset_node in [x for x in (character_asset_list + dynamic_asset_list) if x not in connected_nodes]:
                definition_network.connect_node(anim_asset_node)

        exporter.usertools.helix_exporter.HelixExporter.export_all()
        
    except Exception as err:
        print(err)
        exception_text = v1_core.exceptions.get_exception_message()

        split_dir = os.path.splitext(batch_dir)
        fail_dir = os.path.join(split_dir[0], "batch_fails")
        if not os.path.exists(fail_dir):
            os.makedirs(fail_dir)

        folder_list = split_dir[0].split(os.path.sep)
        error_file_name = '_'.join([x for x in str(pm.sceneName()).split('/') if x not in folder_list])
        text_error_path = os.path.join(fail_dir, error_file_name.replace('.ma', '.txt'))
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
    site.addsitedir(r"W:/Program Files/Autodesk/Maya2022/plug-ins/xgen/scripts") # Prevents startup errors loading xgen
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
        file_list, batch_dir = get_file_list()
        for file in file_list:
            # If paths are relative they need to be passed in relative to Robotore/Data
            if ".." in file:
                content_root = v1_core.environment.get_project_root()
                data_path = os.path.join(content_root, 'Robogore', 'Data')
                file = file.replace("..", data_path)

            print("==============================================")
            print("================ WORKING ON ==================")
            print("==============================================")
            print(file)
            pm.openFile(file, f=True)
            file_commands(batch_dir)
    except:
        pass
    finally:
        maya.standalone.uninitialize()
    
if __name__ == "__main__":
    main()