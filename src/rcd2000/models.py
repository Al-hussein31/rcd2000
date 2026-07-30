from dataclasses import dataclass, field, asdict
from typing import List, Optional, Tuple, Union
import json


@dataclass
class DesignInput:
    fcu: float = 25.0
    fy: float = 460.0
    fyv: float = 250.0
    pb: float = 150.0  # bearing pressure for bases
    beams: List[dict] = field(default_factory=list)
    columns: List[dict] = field(default_factory=list)
    slabs: List[dict] = field(default_factory=list)
    stairs: List[dict] = field(default_factory=list)
    bases: List[dict] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "DesignInput":
        return cls(**{k: v for k, v in data.items()
                      if k in cls.__dataclass_fields__})

    @classmethod
    def from_json(cls, path: str) -> "DesignInput":
        with open(path) as f:
            return cls.from_dict(json.load(f))

    def to_json(self, path: str):
        with open(path, "w") as f:
            json.dump(asdict(self), f, indent=2)


def result_to_dict(obj) -> dict:
    """Convert a dataclass result to a dict, recursing into lists."""
    if hasattr(obj, "__dataclass_fields__"):
        result = {}
        for field_name in obj.__dataclass_fields__:
            value = getattr(obj, field_name)
            if isinstance(value, list):
                result[field_name] = [result_to_dict(v) if hasattr(v, "__dataclass_fields__") else v
                                      for v in value]
            elif hasattr(value, "__dataclass_fields__"):
                result[field_name] = result_to_dict(value)
            else:
                result[field_name] = value
        return result
    return obj
