import pymel.core as pm


from v1_shared.shared_utils import get_first_or_default, get_index_or_default, get_last_or_default



def shift_down():
    mods = pm.getModifiers()
    return (mods & 1) > 0

def capslock_down():
    mods = pm.getModifiers()
    return (mods & 2) > 0

def ctrl_down():
    mods = pm.getModifiers()
    return (mods & 4) > 0

def alt_down():
    mods = pm.getModifiers()
    return (mods & 8) > 0