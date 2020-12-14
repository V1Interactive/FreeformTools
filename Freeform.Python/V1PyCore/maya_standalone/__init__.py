import pkgutil
import sys

for loader, name, is_pkg in pkgutil.walk_packages(__path__):
	if not is_pkg:
		module = loader.find_module(name).load_module(name)
		setattr(sys.modules[__package__], name, module)