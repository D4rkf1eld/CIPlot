# Copyright (c) D4rkf1eld 2026. All rights reserved.

from typing import Any, Dict, Mapping, Optional, Sequence, Union

import copy
import dataclasses
import numpy as np

from dataclasses import is_dataclass

from .config import SeriesCfg

def _check_label_uniqueness(series: Sequence[SeriesCfg]):
    """
    Check that all non-empty labels in the series list are unique, and raise an error if duplicate labels are found.
    This is important for the data export functionality to work correctly, as duplicate labels cannot be stored in data records.
    """

    labels = [s.label for s in series if s.label]

    duplicates = set([lab for lab in labels if labels.count(lab) > 1])

    if duplicates:
        raise ValueError(f"Duplicate series labels found: {duplicates}. Please ensure that all non-empty series labels are unique. \n")

def _enforce_json_serializability(data: Any) -> Any:
    """
    Recursively enforce JSON serializability of the data by converting non-serializable types (e.g. numpy arrays) to lists.
    """

    if isinstance(data, np.ndarray):
        return data.tolist()

    elif isinstance(data, dict):
        return {k: _enforce_json_serializability(v) for k, v in data.items()}

    elif isinstance(data, (list, tuple)):
        return [_enforce_json_serializability(v) for v in data]

    else:
        return data

def _deeply_merge_dict(base: Mapping[str, Any], override: Mapping[str, Any]) -> Dict[str, Any]:
    """
    Deeply merge two dictionaries.
    """

    out = copy.deepcopy(dict(base))

    for key, value in override.items():
        if key in out and isinstance(out[key], dict) and isinstance(value, Mapping):
            out[key] = _deeply_merge_dict(out[key], value)

        else:
            out[key] = copy.deepcopy(value)

    return out

def _merge_dataclass_with_mapping(base_obj: Any, override: Mapping[str, Any]) -> Any:
    """
    Merge a dataclass instance with a mapping, deeply merging nested dictionaries.
    """

    if base_obj is None:
        raise TypeError("The base object for merging cannot be None. Please provide a valid dataclass instance as the base object. \n")

    if not is_dataclass(base_obj) or isinstance(base_obj, type):
        raise TypeError(f"Expected a dataclass instance, got {type(base_obj).__name__}.")

    field_names = {f.name for f in dataclasses.fields(base_obj)}
    unknown = set(override.keys()) - field_names

    if unknown:
        raise KeyError(f"Unknown fields in override: {unknown}. Valid fields are: {field_names}. Please check the override mapping for invalid field names. \n")

    updates: Dict[str, Any] = {}

    for f in dataclasses.fields(base_obj):
        base_value = getattr(base_obj, f.name)

        if f.name not in override:
            updates[f.name] = copy.deepcopy(base_value)

            continue

        override_value = override[f.name]

        if is_dataclass(base_value) and isinstance(override_value, Mapping):
            updates[f.name] = _merge_dataclass_with_mapping(base_value, override_value)

        elif isinstance(base_value, dict) and isinstance(override_value, Mapping):
            updates[f.name] = _deeply_merge_dict(base_value, override_value)

        else:
            updates[f.name] = copy.deepcopy(override_value)

    return dataclasses.replace(base_obj, **updates)

def _resolve_cfg_override(base_obj: Optional[Any], override_obj: Optional[Union[Any, Mapping[str, Any]]], target_cls: type) -> Optional[Any]:
    """
    Resolve a configuration override by merging a base dataclass instance with an override that can either be a complete dataclass instance
    or a mapping of field overrides.
    """

    if override_obj is None:
        return copy.deepcopy(base_obj)

    if is_dataclass(override_obj) and not isinstance(override_obj, type):
        if not isinstance(override_obj, target_cls):
            raise TypeError(f"Expected an override of type {target_cls.__name__}, but got {type(override_obj).__name__}. Please provide an override object of the correct type. \n")

        return copy.deepcopy(override_obj)

    if isinstance(override_obj, Mapping):
        if base_obj is None:
            try:
                return target_cls(**copy.deepcopy(dict(override_obj)))

            except TypeError as exc:
                raise TypeError(f"Failed to create an instance of {target_cls.__name__} from the provided override mapping. This may be because the mapping is missing required fields or has invalid field names. \n Original error message: {exc} \n Please check the override mapping and ensure it has the correct structure and field names for {target_cls.__name__}. \n")

        return _merge_dataclass_with_mapping(base_obj, override_obj)

    raise TypeError(f"Invalid override object of type {type(override_obj).__name__}. Expected either an instance of {target_cls.__name__} or a mapping of field overrides. Please provide a valid override object. \n")