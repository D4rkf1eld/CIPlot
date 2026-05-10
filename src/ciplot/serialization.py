# Copyright (c) D4rkf1eld 2026. All rights reserved.

from typing import Any, Dict, List, Optional

import copy

import dataclasses
import importlib

import numpy as np

from dataclasses import is_dataclass
from enum import Enum
from pathlib import Path

from .config import ExportCfg

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

def _python_code_class_name_from_fqname(fqname: str) -> str:
    """
    Extract the short Python class name from a fully-qualified serialized class name.
    Example: "some.module:Outer.Inner" -> "Inner".
    """

    if ":" in fqname:
        _, qualname = fqname.split(":", 1)

    else:
        qualname = fqname

    return qualname.split(".")[-1]

def _collect_general_settings_python_code_requirements(node: Any,
                                                       class_names: List[str],
                                                       needs_path_import: List[bool]) -> None:
    """
    Collect dataclass / enum class names and whether pathlib.Path is needed by the generated Python code.
    The class_names list preserves first-use order for stable and readable import output.
    """

    if isinstance(node, list):
        for item in node:
            _collect_general_settings_python_code_requirements(item, class_names, needs_path_import)

        return

    if not isinstance(node, dict):
        return

    tag = node.get("__type__")

    if tag in ("dataclass", "enum"):
        class_name = _python_code_class_name_from_fqname(str(node.get("class", "")))

        if class_name and class_name not in class_names:
            class_names.append(class_name)

    elif tag == "path":
        needs_path_import[0] = True

    if tag == "dataclass":
        fields = node.get("fields", {})

        if isinstance(fields, dict):
            for value in fields.values():
                _collect_general_settings_python_code_requirements(value, class_names, needs_path_import)

        return

    if tag in ("tuple", "set"):
        for item in node.get("items", []):
            _collect_general_settings_python_code_requirements(item, class_names, needs_path_import)

        return

    if tag == "dict_items":
        for key, value in node.get("items", []):
            _collect_general_settings_python_code_requirements(key, class_names, needs_path_import)
            _collect_general_settings_python_code_requirements(value, class_names, needs_path_import)

        return

    for value in node.values():
        _collect_general_settings_python_code_requirements(value, class_names, needs_path_import)

def _render_general_settings_python_value(node: Any, indent_level: int = 0, indent_size: int = 4) -> str:
    """
    Render one node from export_general_dataclasses_settings_to_json(...) as copyable Python code.
    """

    indent = " " * indent_level
    child_indent = " " * (indent_level + indent_size)

    if node is None or isinstance(node, (bool, int, float, str)):
        return repr(node)

    if isinstance(node, list):
        if not node:
            return "[]"

        rendered_items = []

        for item in node:
            rendered_items.append(f"{child_indent}{_render_general_settings_python_value(item, indent_level + indent_size, indent_size)},")

        return "[\n" + "\n".join(rendered_items) + f"\n{indent}]"

    if isinstance(node, dict):
        tag = node.get("__type__")

        if tag == "path":
            return f"Path({node.get('value')!r})"

        if tag == "enum":
            class_name = _python_code_class_name_from_fqname(str(node.get("class", "")))
            member_name = node.get("value")

            return f"{class_name}.{member_name}"

        if tag == "tuple":
            items = node.get("items", [])

            if not items:
                return "()"

            rendered_items = []

            for item in items:
                rendered_items.append(f"{child_indent}{_render_general_settings_python_value(item, indent_level + indent_size, indent_size)},")

            return "(\n" + "\n".join(rendered_items) + f"\n{indent})"

        if tag == "set":
            items = node.get("items", [])

            if not items:
                return "set()"

            rendered_items = []

            for item in items:
                rendered_items.append(f"{child_indent}{_render_general_settings_python_value(item, indent_level + indent_size, indent_size)},")

            return "{\n" + "\n".join(rendered_items) + f"\n{indent}}}"

        if tag == "dict_items":
            items = node.get("items", [])

            if not items:
                return "{}"

            rendered_items = []

            for key, value in items:
                rendered_key = _render_general_settings_python_value(key, indent_level + indent_size, indent_size)
                rendered_value = _render_general_settings_python_value(value, indent_level + indent_size, indent_size)
                rendered_items.append(f"{child_indent}{rendered_key}: {rendered_value},")

            return "{\n" + "\n".join(rendered_items) + f"\n{indent}}}"

        if tag == "dataclass":
            class_name = _python_code_class_name_from_fqname(str(node.get("class", "")))
            fields = node.get("fields", {})

            if not isinstance(fields, dict):
                raise TypeError(f"Expected serialized dataclass fields to be a dictionary, got {type(fields).__name__}. \n")

            if not fields:
                return f"{class_name}()"

            rendered_fields = []

            for field_name, field_value in fields.items():
                rendered_value = _render_general_settings_python_value(field_value, indent_level + indent_size, indent_size)
                rendered_fields.append(f"{child_indent}{field_name} = {rendered_value},")

            return f"{class_name}(\n" + "\n".join(rendered_fields) + f"\n{indent})"

        if not node:
            return "{}"

        rendered_items = []

        for key, value in node.items():
            rendered_key = repr(key)
            rendered_value = _render_general_settings_python_value(value, indent_level + indent_size, indent_size)
            rendered_items.append(f"{child_indent}{rendered_key}: {rendered_value},")

        return "{\n" + "\n".join(rendered_items) + f"\n{indent}}}"

    raise TypeError(f"Cannot render object of type {type(node).__name__} as Python code. \n")

def _render_general_settings_import_block(raw: Dict[str, Any], import_from: str = "ciplot") -> str:
    """
    Build an import block for the generated Python code.
    """

    class_names: List[str] = []
    needs_path_import = [False]

    _collect_general_settings_python_code_requirements(raw, class_names, needs_path_import)

    lines: List[str] = []

    if needs_path_import[0]:
        lines.append("from pathlib import Path")

    if class_names:
        if lines:
            lines.append("")

        sorted_names = sorted(class_names)

        if len(sorted_names) == 1:
            lines.append(f"from {import_from} import {sorted_names[0]}")

        else:
            lines.append(f"from {import_from} import ({sorted_names[0]},")

            for class_name in sorted_names[1:-1]:
                lines.append(f"{' ' * (len(import_from) + 14)}{class_name},")

            lines.append(f"{' ' * (len(import_from) + 14)}{sorted_names[-1]})")

    return "\n".join(lines)

def _infer_general_settings_plot_function_name(raw: Dict[str, Any]) -> Optional[str]:
    """
    Infer the CIPlot API call that best matches the exported top-level keys.
    """

    if "structured_pages" in raw:
        return "browse_structured_subplot_pages"

    if "multi_series" in raw or "browse_page_settings_cfgs" in raw:
        return "browse_series"

    if "series" in raw:
        return "plot_xy"

    return None

def _render_general_settings_plot_call(raw: Dict[str, Any], plot_function_name: str, indent_size: int = 4) -> str:
    """
    Render an optional CIPlot API call using variables emitted from the JSON file.
    """

    argument_order_by_function = {"plot_xy": ["series",
                                              "markings",
                                              "background",
                                              "plot_cfg",
                                              "x_axis_cfg",
                                              "y_axis_cfg",
                                              "grid_cfg",
                                              "legend_cfg",
                                              "export_cfg"],

                                  "browse_series": ["series",
                                                    "multi_series",
                                                    "markings",
                                                    "background",
                                                    "plot_cfg",
                                                    "x_axis_cfg",
                                                    "y_axis_cfg",
                                                    "grid_cfg",
                                                    "legend_cfg",
                                                    "export_cfg",
                                                    "browse_page_settings_cfgs",
                                                    "start_index",
                                                    "export_all_pages"],

                                  "browse_structured_subplot_pages": ["structured_pages",
                                                                      "markings",
                                                                      "background",
                                                                      "plot_cfg",
                                                                      "x_axis_cfg",
                                                                      "y_axis_cfg",
                                                                      "grid_cfg",
                                                                      "legend_cfg",
                                                                      "export_cfg",
                                                                      "start_index",
                                                                      "export_all_pages"]}

    if plot_function_name not in argument_order_by_function:
        raise ValueError(f"Unsupported plot_function_name: {plot_function_name!r}. \n")

    argument_order = argument_order_by_function[plot_function_name]
    present_args = [arg for arg in argument_order if arg in raw]

    if plot_function_name == "browse_series" and "multi_series" in raw and "series" not in raw:
        present_args = ["series"] + present_args

    child_indent = " " * indent_size
    rendered_args: List[str] = []

    for arg in present_args:
        if arg == "series" and arg not in raw:
            rendered_args.append(f"{child_indent}series = None,")

        else:
            rendered_args.append(f"{child_indent}{arg} = {arg},")

    return f"{plot_function_name}(\n" + "\n".join(rendered_args) + "\n)"

def _make_restored_settings_safe(obj: Any) -> Any:
    """
    Disable write-producing export actions in restored general settings.

    General settings files should restore plotting configuration, not silently grant
    permission to overwrite files.
    """

    if isinstance(obj, ExportCfg):
        return dataclasses.replace(obj,
                                   enable_export = False,
                                   enable_data_export = False,
                                   data_export_with_style = False)

    if isinstance(obj, dict):
        changed = False

        out = {}

        for key, value in obj.items():
            safe_value = _make_restored_settings_safe(value)

            out[key] = safe_value

            if safe_value is not value:
                changed = True

        return out if changed else obj

    if isinstance(obj, list):
        changed = False

        out = []

        for value in obj:
            safe_value = _make_restored_settings_safe(value)

            out.append(safe_value)

            if safe_value is not value:
                changed = True

        return out if changed else obj

    if isinstance(obj, tuple):
        changed = False

        out = []

        for value in obj:
            safe_value = _make_restored_settings_safe(value)

            out.append(safe_value)

            if safe_value is not value:
                changed = True

        return tuple(out) if changed else obj

    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        field_updates = {}

        changed = False

        for field in dataclasses.fields(obj):
            value = getattr(obj, field.name)

            safe_value = _make_restored_settings_safe(value)

            if safe_value is not value:
                field_updates[field.name] = safe_value

                changed = True

        if not changed:
            return obj

        safe_obj = copy.deepcopy(obj)

        for field_name, safe_value in field_updates.items():
            object.__setattr__(safe_obj, field_name, safe_value)

        return safe_obj

    return obj