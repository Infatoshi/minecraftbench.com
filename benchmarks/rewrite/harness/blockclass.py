"""Block-id -> class table for macro accuracy. Single source of truth (FORMAT.md is informative).

Vanilla 1.11.2 numeric ids. Ids not listed map to "other".
"""

import numpy as np

CLASSES: dict[str, list[int]] = {
    "air": [0],
    "stone-family": [1],
    "dirt/grass": [2, 3],
    "sand/gravel": [12, 13],
    "water": [8, 9],
    "lava": [10, 11],
    "ores": [14, 15, 16, 21, 56, 73, 74, 129],
    "wood": [17, 162],
    "leaves": [18, 161],
    "vegetation": [31, 32, 37, 38, 39, 40, 81, 83, 86, 103, 106, 110, 111, 141, 142, 175],
    "snow/ice": [78, 79, 80, 174],
    "clay/terracotta": [82, 159, 172],
    "bedrock": [7],
    "structure-ish": [48, 49, 52, 54, 30, 66, 5, 85, 113, 50, 216],
}

CLASS_NAMES: list[str] = list(CLASSES.keys()) + ["other"]

CLASS_OF: dict[int, str] = {}
for _cls, _ids in CLASSES.items():
    for _bid in _ids:
        if _bid in CLASS_OF:
            raise ValueError(f"block id {_bid} in two classes")
        CLASS_OF[_bid] = _cls

# id -> class index lookup, "other" for anything unlisted (ids are 0..255 in 1.11.2 + Add nibble)
CLASS_INDEX = np.full(4096, CLASS_NAMES.index("other"), dtype=np.int16)
for _bid, _cls in CLASS_OF.items():
    CLASS_INDEX[_bid] = CLASS_NAMES.index(_cls)


def class_of_ids(ids: np.ndarray) -> np.ndarray:
    """Vector of block ids -> vector of class indices into CLASS_NAMES."""
    return CLASS_INDEX[ids]
