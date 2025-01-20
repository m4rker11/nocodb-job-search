import importlib
import pkgutil

from .base import BaseTransformation

def find_transformations_in_package(package_name="transformations"):
    """
    Dynamically discovers and imports all modules in the given package,
    returning a dict of { transformation_name: instance_of_that_transformation }.
    """
    package = importlib.import_module(package_name)
    transformations = {}
    for _, module_name, is_pkg in pkgutil.iter_modules(package.__path__):
        if not is_pkg:
            full_module_name = f"{package_name}.{module_name}"
            module = importlib.import_module(full_module_name)
            for name, obj in vars(module).items():
                if (
                    isinstance(obj, type)
                    and issubclass(obj, BaseTransformation)
                    and obj is not BaseTransformation
                ):
                    instance = obj()
                    transformations[instance.name] = instance
    return transformations