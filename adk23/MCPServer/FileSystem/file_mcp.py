"""
File MCP Module
===============
Strictly file operations: read, write, edit, append, clear, copy, move, delete.
"""

import base64
import os
import shutil
from typing import Any, Dict

from .utils import (
    safe_path, get_ext, _ensure_parent, READ_DISPATCH, TEXT_EXTENSIONS,
    _read_text, _read_binary_b64, _write_text, WRITE_DISPATCH, _write_binary_b64
)


async def read_file_tool(file_path: str) -> Dict[str, Any]:
    try:
        fp = safe_path(file_path)
    except ValueError as e:
        return {"status": "error", "message": str(e)}

    if not os.path.exists(fp):
        return {"status": "error", "message": f"File not found: {file_path}"}
    if not os.path.isfile(fp):
        return {"status": "error", "message": f"Path is not a file: {file_path}"}

    ext = get_ext(fp)
    try:
        if ext in READ_DISPATCH:
            content = READ_DISPATCH[ext](fp)
            fmt = ext.lstrip(".")
        elif ext in TEXT_EXTENSIONS or ext == "":
            content = _read_text(fp)
            fmt = "text"
        else:
            try:
                content = _read_text(fp)
                fmt = "text"
            except UnicodeDecodeError:
                content = _read_binary_b64(fp)
                fmt = "base64"
    except Exception as exc:
        return {"status": "error", "message": str(exc)}

    return {"status": "ok", "file_path": fp, "format": fmt, "content": content}


async def write_file_tool(file_path: str, content: str) -> Dict[str, Any]:
    try:
        fp = safe_path(file_path)
    except ValueError as e:
        return {"status": "error", "message": str(e)}

    ext = get_ext(fp)
    try:
        if ext in WRITE_DISPATCH:
            WRITE_DISPATCH[ext](fp, content)
        elif ext in TEXT_EXTENSIONS or ext == "":
            _write_text(fp, content)
        else:
            try:
                base64.b64decode(content, validate=True)
                _write_binary_b64(fp, content)
            except Exception:
                _write_text(fp, content)
    except Exception as exc:
        return {"status": "error", "message": str(exc)}

    return {"status": "ok", "message": f"File written: {fp}"}


async def edit_file_tool(file_path: str, old_text: str, new_text: str) -> Dict[str, Any]:
    try:
        fp = safe_path(file_path)
    except ValueError as e:
        return {"status": "error", "message": str(e)}

    if not os.path.exists(fp):
        return {"status": "error", "message": f"File not found: {file_path}"}
    if not os.path.isfile(fp):
        return {"status": "error", "message": f"Not a file: {file_path}"}

    ext = get_ext(fp)
    if ext in {".docx", ".xlsx", ".xls", ".pdf", ".pptx"}:
        return {
            "status": "error",
            "message": f"edit_file_tool does not support {ext}. Use read_file_tool → modify → write_file_tool.",
        }

    try:
        original = _read_text(fp)
    except Exception as exc:
        return {"status": "error", "message": f"Cannot read file: {exc}"}

    count = original.count(old_text)
    if count == 0:
        return {"status": "error", "message": "old_text not found in file.", "replacements_made": 0}

    try:
        _write_text(fp, original.replace(old_text, new_text))
    except Exception as exc:
        return {"status": "error", "message": f"Cannot write file: {exc}"}

    return {"status": "ok", "replacements_made": count, "message": f"Replaced {count} occurrence(s)."}


async def append_file_tool(file_path: str, content: str) -> Dict[str, Any]:
    try:
        fp = safe_path(file_path)
    except ValueError as e:
        return {"status": "error", "message": str(e)}

    ext = get_ext(fp)
    if ext in {".docx", ".xlsx", ".xls", ".pdf", ".pptx"}:
        return {
            "status": "error",
            "message": f"append_file_tool does not support {ext}. Use read + write instead.",
        }

    try:
        _ensure_parent(fp)
        with open(fp, "a", encoding="utf-8") as fh:
            fh.write(content)
    except Exception as exc:
        return {"status": "error", "message": str(exc)}

    return {"status": "ok", "message": f"Content appended to: {fp}"}


async def clear_file_tool(file_path: str) -> Dict[str, Any]:
    try:
        fp = safe_path(file_path)
    except ValueError as e:
        return {"status": "error", "message": str(e)}

    if not os.path.exists(fp):
        return {"status": "error", "message": f"File not found: {file_path}"}

    ext = get_ext(fp)
    if ext in {".docx", ".xlsx", ".xls", ".pdf", ".pptx"}:
        return {
            "status": "error",
            "message": f"clear_file_tool does not support {ext}. Use write_file_tool with empty content.",
        }

    open(fp, "w").close()
    return {"status": "ok", "message": f"File cleared: {fp}"}


async def copy_file_tool(source_path: str, destination_path: str) -> Dict[str, Any]:
    try:
        src = safe_path(source_path)
        dst = safe_path(destination_path)
    except ValueError as e:
        return {"status": "error", "message": str(e)}

    if not os.path.exists(src):
        return {"status": "error", "message": f"Source not found: {source_path}"}
    if not os.path.isfile(src):
        return {"status": "error", "message": f"Source is not a file: {source_path}"}

    try:
        _ensure_parent(dst)
        shutil.copy2(src, dst)
    except Exception as exc:
        return {"status": "error", "message": str(exc)}

    return {"status": "ok", "message": f"Copied '{src}' → '{dst}'"}


async def move_file_tool(source_path: str, destination_path: str) -> Dict[str, Any]:
    try:
        src = safe_path(source_path)
        dst = safe_path(destination_path)
    except ValueError as e:
        return {"status": "error", "message": str(e)}

    if not os.path.exists(src):
        return {"status": "error", "message": f"Source not found: {source_path}"}
    if not os.path.isfile(src):
        return {"status": "error", "message": f"Source is not a file: {source_path}"}

    try:
        _ensure_parent(dst)
        shutil.move(src, dst)
    except Exception as exc:
        return {"status": "error", "message": str(exc)}

    return {"status": "ok", "message": f"Moved '{src}' → '{dst}'"}


async def delete_file_tool(file_path: str) -> Dict[str, Any]:
    try:
        fp = safe_path(file_path)
    except ValueError as e:
        return {"status": "error", "message": str(e)}

    if not os.path.exists(fp):
        return {"status": "error", "message": f"File not found: {file_path}"}
    if not os.path.isfile(fp):
        return {"status": "error", "message": f"Not a file: {file_path}"}

    os.remove(fp)
    return {"status": "ok", "message": f"Deleted file: {fp}"}

