import pkgutil
import importlib.util

if not hasattr(pkgutil, "find_loader"):
    pkgutil.find_loader = lambda name: (
        importlib.util.find_spec(name)
    )
