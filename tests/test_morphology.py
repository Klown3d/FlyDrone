import struct

import pytest

from flydrone.data.morphology import parse_header


def test_neuroglancer_skeleton_layout(tmp_path):
    path = tmp_path / "synthetic.bin"
    vertices = [(1.0, 2.0, 3.0), (4.0, 5.0, 6.0), (7.0, 8.0, 9.0)]
    payload = struct.pack("<II", 3, 2)
    payload += struct.pack("<9f", *(v for xyz in vertices for v in xyz))
    payload += struct.pack("<4I", 0, 1, 1, 2)
    payload += struct.pack("<3f", 10.0, 11.0, 12.0)
    path.write_bytes(payload)
    assert parse_header(path) == {"vertices": 3, "edges": 2, "bytes": len(payload)}


def test_rejects_truncated_skeleton(tmp_path):
    path = tmp_path / "bad.bin"
    path.write_bytes(struct.pack("<I", 9))
    with pytest.raises(ValueError, match="Missing edge count"):
        parse_header(path)
