"""JSON-safe dataclass serialization for design-result persistence.

The design engines return dataclasses (possibly nested - e.g.
``BeamResult.spans: List[BeamSpanResult]``).  To persist results with the
job file and rebuild them when a job is re-opened, we convert them to
plain dicts (``dataclasses.asdict``) and reconstruct them here from the
field type hints.
"""

import dataclasses
import typing
from typing import Any


def as_dict(obj: Any) -> Any:
    """Convert a dataclass (or nested structure) to plain dicts/lists."""
    return dataclasses.asdict(obj)


def _reconstruct(tp: Any, value: Any) -> Any:
    """Reconstruct one value guided by its declared type hint."""
    if value is None:
        return None
    origin = typing.get_origin(tp)
    if origin is not None:
        args = typing.get_args(tp)
        if origin in (list, tuple) and isinstance(value, list):
            item_tp = args[0] if args else Any
            if origin is tuple:
                return tuple(_reconstruct(item_tp, v) for v in value)
            return [_reconstruct(item_tp, v) for v in value]
        if origin is typing.Union:
            # Optional[X] / Union[...]: try the first non-NoneType member
            for a in args:
                if a is type(None):
                    continue
                try:
                    return _reconstruct(a, value)
                except (TypeError, ValueError):
                    continue
            return value
        return value
    if (
        isinstance(tp, type)
        and dataclasses.is_dataclass(tp)
        and isinstance(value, dict)
    ):
        return dataclass_from_dict(tp, value)
    return value


def dataclass_from_dict(cls: type, data: dict) -> Any:
    """Reconstruct a dataclass instance from ``asdict()`` output.

    Nested dataclasses and ``List[SomeDataclass]`` fields are rebuilt
    recursively from the class field type hints.  Unknown keys are
    ignored; missing fields fall back to the dataclass default so old
    saved payloads stay forward-compatible.
    """
    if data is None:
        return None
    if not dataclasses.is_dataclass(cls) or not isinstance(data, dict):
        return data
    hints = typing.get_type_hints(cls)
    kwargs = {}
    for f in dataclasses.fields(cls):
        if f.name not in data:
            continue
        kwargs[f.name] = _reconstruct(
            hints.get(f.name, type(data[f.name])), data[f.name]
        )
    return cls(**kwargs)
