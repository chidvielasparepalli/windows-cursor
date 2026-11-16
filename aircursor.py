from __future__ import annotations

import importlib.util
import marshal
from pathlib import Path
import types

RUNTIME_PATH = Path(__file__).with_name("aircursor_runtime.pyc")

if not RUNTIME_PATH.is_file():
    raise SystemExit(
        "AirCursor runtime cache is missing. Restore aircursor_runtime.pyc "
        "or reinstall the project source."
    )

payload = RUNTIME_PATH.read_bytes()
if len(payload) < 17 or payload[:4] != importlib.util.MAGIC_NUMBER:
    raise SystemExit(
        "AirCursor runtime cache is incompatible with this Python version."
    )

code = marshal.loads(payload[16:])
if not isinstance(code, types.CodeType):
    raise SystemExit("AirCursor runtime cache is invalid.")

exec(code, globals())
