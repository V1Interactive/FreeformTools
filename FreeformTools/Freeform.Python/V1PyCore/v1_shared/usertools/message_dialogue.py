import System
import System.Diagnostics
import Freeform.Rigging

import os
import threading
import time

import v1_core
import v1_shared
from v1_shared.decorators import csharp_error_catcher


def get_dialogue_display():
    config_manager = v1_core.global_settings.ConfigManager()
    project_key = v1_core.global_settings.ConfigKey.PROJECT.value
    return config_manager.config_settings.settings.get(project_key)["Display_Dialogues"]

def set_dialogue_display(value):
    config_manager = v1_core.global_settings.ConfigManager()
    project_key = v1_core.global_settings.ConfigKey.PROJECT.value
    config_manager.config_settings.settings.get(project_key)["Display_Dialogues"] = value
    config_manager.config_settings.save_settings()

def open_dialogue(message, title = None, enable_cancel = False, confirm_method = None, cancel_method = None):
    config_manager = v1_core.global_settings.ConfigManager()
    project_key = v1_core.global_settings.ConfigKey.PROJECT.value
    display_dialogue_config = config_manager.get(project_key).get("Display_Dialogues")

    if(display_dialogue_config == True):

        dialogue_ui = MessageDialogue()

        dialogue_ui.vm.Message = message
        dialogue_ui.vm.EnableCancel = enable_cancel

        if title:
            dialogue_ui.vm.WindowTitle = title
        if confirm_method:
            dialogue_ui.vm.ConfirmHandler += confirm_method
        if cancel_method:
            dialogue_ui.vm.ConfirmHandler += cancel_method

        dialogue_ui.show()

        return dialogue_ui.vm.Confirmed

    return True


class MessageDialogue(object):
    '''

    '''

    def __init__(self, file_path = None):
        '''

        '''
        self.process = System.Diagnostics.Process.GetCurrentProcess()
        self.ui = Freeform.Rigging.MessageDialogue.MessageDialogue(self.process)
        self.vm = self.ui.DataContext

        self.vm.CloseWindowEventHandler += self.close

    def show(self):
        '''

        '''
        self.ui.Show()

    def close(self, vm, event_args):
        '''

        '''
        self.vm.CloseWindowEventHandler -= self.close
