# Copyright (c) D4rkf1eld 2026. All rights reserved.

from typing import Any, Dict

import dataclasses
import importlib

import numpy as np

from dataclasses import is_dataclass
from enum import Enum
from pathlib import Path

_TYPE_KEY = "__type__"
_VALUE_KEY = "value"

def _class_fqname(cls: type) -> str:
    """
    Get the fully-qualified name of a class, including its module and qualified name (which includes nesting for inner classes).
    This is used for accurately identifying classes during serialization and deserialization.
    """

    return f"{cls.__module__}:{cls.__qualname__}"

def _import_by_fqname(fqname: str) -> Any:
    """
    Import and retrieve a Python object (e.g. class, function, variable) based on its fully-qualified name,
    which includes the module path and the qualified name of the object within that module.
    """

    if ":" not in fqname:
        raise ValueError(f"The fully-qualified name '{fqname}' is not valid. It must be in the format 'module_path:qualified_name'. \n Please provide a valid fully-qualified name. \n")

    module_name, qualname = fqname.split(":", 1)

    module = importlib.import_module(module_name)

    obj: Any = module

    for part in qualname.split("."):
        obj = getattr(obj, part)

    return obj

def _to_json_serializable(obj: Any, path: str) -> Any:
    """
    Recursively convert Python objects to JSON-serializable structures, with special handling for dataclasses, enums, pathlib.Path, and other common types.
    The resulting JSON structure includes type tags to allow for accurate reconstruction of the original Python objects when deserializing from JSON.
    """

    # Explicitly reject callables (e.g. functions, methods, lambdas) as they cannot be serialized to JSON
    if callable(obj):
        raise TypeError(f"The object at '{path}' is a callable (e.g. function, method, lambda) which cannot be serialized to JSON. \n Object: {obj!r} \n")

    # Handle JSON primitives directly, as they are already serializable
    if obj is None or isinstance(obj, (bool, int, str)):
        return obj

    # Handle floats, but explicitly reject NaN and Infinity as they are not JSON-serializable
    if isinstance(obj, float):
        if obj != obj:
            raise ValueError(f"The object at '{path}' is a float NaN which cannot be serialized to JSON. \n Object: {obj!r} \n")

        if obj in (float("inf"), float("-inf")):
            raise ValueError(f"The object at '{path}' is a float Infinity which cannot be serialized to JSON. \n Object: {obj!r} \n")

        return obj

    # Handle numpy arrays by converting them to plain JSON lists recursively
    if isinstance(obj, np.ndarray):
        return [_to_json_serializable(v, path = f"{path}[{i}]") for i, v in enumerate(obj.tolist())]

    # Handle pathlib.Path objects by converting them to their string representation and tagging them with a type identifier for accurate reconstruction during deserialization
    if isinstance(obj, Path):
        return {_TYPE_KEY: "path", _VALUE_KEY: str(obj)}

    # Handle enums by storing their class's fully-qualified name (that is, the full module path plus the class name) and their member name
    if isinstance(obj, Enum):
        return {_TYPE_KEY: "enum", "class": _class_fqname(obj.__class__), _VALUE_KEY: obj.name}

    # Handle dataclasses by storing their class's fully-qualified name and a mapping of their field names to their JSON-serializable values, recursively converting field values as needed
    if is_dataclass(obj) and not isinstance(obj, type):
        cls = obj.__class__

        field_map: Dict[str, Any] = {}

        for f in dataclasses.fields(obj):
            field_map[f.name] = _to_json_serializable(getattr(obj, f.name), path = f"{path}.{f.name}")

        return {_TYPE_KEY: "dataclass", "class": _class_fqname(cls), "fields": field_map}

    # Handle lists, tuples, and sets by recursively converting their elements to JSON-serializable values,
    # and tagging tuples and sets with type identifiers for accurate reconstruction during deserialization (since JSON does not have native tuple or set types).
    if isinstance(obj, list):
        return [_to_json_serializable(v, path = f"{path}[{i}]") for i, v in enumerate(obj)]

    if isinstance(obj, tuple):
        return {_TYPE_KEY: "tuple", "items": [_to_json_serializable(v, path = f"{path}[{i}]") for i, v in enumerate(obj)]}

    if isinstance(obj, set):
        return {_TYPE_KEY: "set", "items": [_to_json_serializable(v, path = f"{path}{{item}}") for v in obj]}

    # Handle dicts by recursively converting their keys and values to JSON-serializable values.
    # Since JSON requires string keys, if all keys are strings, serialize it directly as a JSON object.
    # If there are non-string keys, serialize the dict as a list of key-value pairs with type tagging for accurate reconstruction during deserialization.
    if isinstance(obj, dict):
        if all(isinstance(k, str) for k in obj.keys()):
            out: Dict[str, Any] = {}

            for k, v in obj.items():
                out[k] = _to_json_serializable(v, path = f"{path}.{k}")

            return out

        return {_TYPE_KEY: "dict_items", "items": [[_to_json_serializable(k, path = f"{path}.<key>"), _to_json_serializable(v, path = f"{path}[{i}]")] for i, (k, v) in enumerate(obj.items())]}

    # If it goes beyond the handled types, raise an error indicating bad things
    raise TypeError(f"The object at '{path}' of type {type(obj).__name__} is not JSON-serializable and cannot be converted to a JSON-serializable structure. \n Object: {obj!r}")

def _from_serialized_json(node: Any) -> Any:
    """
    Recursively reconstruct Python objects from JSON-deserialized structures that were created by the
    _to_json_serializable() function, using the type tags to accurately restore dataclasses, enums, pathlib.Path,
    and other special types.
    """

    # Handle JSON primitives directly, as they do not require any special reconstruction
    if node is None or isinstance(node, (bool, int, float, str)):
        return node

    # Lists require reconstructing each element, while dicts may either be plain dicts or tagged structures,
    # that require special handling based on their type tags.
    if isinstance(node, list):
        return [_from_serialized_json(v) for v in node]

    if isinstance(node, dict):
        tag = node.get(_TYPE_KEY)

        if tag == "path":
            return Path(node[_VALUE_KEY])

        if tag == "tuple":
            return tuple(_from_serialized_json(v) for v in node.get("items", []))

        if tag == "set":
            return set(_from_serialized_json(v) for v in node.get("items", []))

        if tag == "dict_items":
            items = node.get("items", [])

            out: Dict[Any, Any] = {}

            for k_ser, v_ser in items:
                out[_from_serialized_json(k_ser)] = _from_serialized_json(v_ser)

            return out

        if tag == "enum":
            cls = _import_by_fqname(node["class"])

            if not (isinstance(cls, type) and issubclass(cls, Enum)):
                raise TypeError(f"The restored class for enum is not a subclass of the real Enum type: {node['class']!r}. \n")

            return cls[node[_VALUE_KEY]]

        if tag == "dataclass":
            cls = _import_by_fqname(node["class"])

            if not (isinstance(cls, type) and is_dataclass(cls)):
                raise TypeError(f"The restored class for dataclass is not a real dataclass type: {node['class']!r}. \n")

            fields_dict = node.get("fields", {})

            if not isinstance(fields_dict, dict):
                raise TypeError(f"The 'fields' value for the dataclass {node['class']!r} is not a dict as expected. \n")

            restored_fields = {k: _from_serialized_json(v) for k, v in fields_dict.items()}

            # Build the initial kwargs for init = True fields
            init_kwargs: Dict[str, Any] = {}
            post_kwargs: Dict[str, Any] = {}

            for f in dataclasses.fields(cls):
                if f.name in restored_fields:
                    if f.init:
                        init_kwargs[f.name] = restored_fields[f.name]

                    else:
                        post_kwargs[f.name] = restored_fields[f.name]

            obj = cls(**init_kwargs)

            # Set the non-init fields after object creation, using object.__setattr__ for frozen dataclasses
            # to bypass immutability restrictions, and setattr for regular classes or non-frozen dataclasses.
            for name, value in post_kwargs.items():
                if getattr(cls, "__dataclass_params__", None) and cls.__dataclass_params__.frozen:
                    object.__setattr__(obj, name, value)

                else:
                    setattr(obj, name, value)

            return obj

        # If there is no special type tag, treat it as a regular dict and recursively reconstruct its keys and values
        return {k: _from_serialized_json(v) for k, v in node.items()}

    raise TypeError(f"The JSON node {node!r} cannot be deserialized into a Python object because it is of an unsupported type {type(node).__name__}. \n")