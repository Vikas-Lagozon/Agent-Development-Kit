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
    logger,
    safe_path, get_ext, _ensure_parent, READ_DISPATCH, TEXT_EXTENSIONS,
    _read_text, _read_binary_b64, _write_text, WRITE_DISPATCH, _write_binary_b64
)


async def read_file_tool(file_path: str) -> Dict[str, Any]:
    logger.debug(f"read_file_tool called | file_path='{file_path}'")
    try:
        fp = safe_path(file_path)
    except ValueError as e:
        logger.warning(f"read_file_tool | invalid path '{file_path}': {e}")
        return {"status": "error", "message": str(e)}

    if not os.path.exists(fp):
        logger.warning(f"read_file_tool | file not found: '{fp}'")
        return {"status": "error", "message": f"File not found: {file_path}"}
    if not os.path.isfile(fp):
        logger.warning(f"read_file_tool | path is not a file: '{fp}'")
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
        logger.error(f"read_file_tool | failed to read '{fp}': {exc}", exc_info=True)
        return {"status": "error", "message": str(exc)}

    logger.info(f"read_file_tool | success | format='{fmt}' | path='{fp}'")
    return {"status": "ok", "file_path": fp, "format": fmt, "content": content}


async def write_file_tool(file_path: str, content: str) -> Dict[str, Any]:
    logger.debug(f"write_file_tool called | file_path='{file_path}'")
    try:
        fp = safe_path(file_path)
    except ValueError as e:
        logger.warning(f"write_file_tool | invalid path '{file_path}': {e}")
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
        logger.error(f"write_file_tool | failed to write '{fp}': {exc}", exc_info=True)
        return {"status": "error", "message": str(exc)}

    logger.info(f"write_file_tool | success | path='{fp}'")
    return {"status": "ok", "message": f"File written: {fp}"}


async def edit_file_tool(file_path: str, old_text: str, new_text: str) -> Dict[str, Any]:
    logger.debug(f"edit_file_tool called | file_path='{file_path}'")
    try:
        fp = safe_path(file_path)
    except ValueError as e:
        logger.warning(f"edit_file_tool | invalid path '{file_path}': {e}")
        return {"status": "error", "message": str(e)}

    if not os.path.exists(fp):
        logger.warning(f"edit_file_tool | file not found: '{fp}'")
        return {"status": "error", "message": f"File not found: {file_path}"}
    if not os.path.isfile(fp):
        logger.warning(f"edit_file_tool | not a file: '{fp}'")
        return {"status": "error", "message": f"Not a file: {file_path}"}

    ext = get_ext(fp)
    if ext in {".docx", ".xlsx", ".xls", ".pdf", ".pptx"}:
        logger.warning(f"edit_file_tool | unsupported format '{ext}' for '{fp}'")
        return {
            "status": "error",
            "message": f"edit_file_tool does not support {ext}. Use read_file_tool → modify → write_file_tool.",
        }

    try:
        original = _read_text(fp)
    except Exception as exc:
        logger.error(f"edit_file_tool | cannot read '{fp}': {exc}", exc_info=True)
        return {"status": "error", "message": f"Cannot read file: {exc}"}

    count = original.count(old_text)
    if count == 0:
        logger.warning(f"edit_file_tool | old_text not found in '{fp}'")
        return {"status": "error", "message": "old_text not found in file.", "replacements_made": 0}

    try:
        _write_text(fp, original.replace(old_text, new_text))
    except Exception as exc:
        logger.error(f"edit_file_tool | cannot write '{fp}': {exc}", exc_info=True)
        return {"status": "error", "message": f"Cannot write file: {exc}"}

    logger.info(f"edit_file_tool | success | replacements={count} | path='{fp}'")
    return {"status": "ok", "replacements_made": count, "message": f"Replaced {count} occurrence(s)."}


async def append_file_tool(file_path: str, content: str) -> Dict[str, Any]:
    logger.debug(f"append_file_tool called | file_path='{file_path}'")
    try:
        fp = safe_path(file_path)
    except ValueError as e:
        logger.warning(f"append_file_tool | invalid path '{file_path}': {e}")
        return {"status": "error", "message": str(e)}

    ext = get_ext(fp)
    if ext in {".docx", ".xlsx", ".xls", ".pdf", ".pptx"}:
        logger.warning(f"append_file_tool | unsupported format '{ext}' for '{fp}'")
        return {
            "status": "error",
            "message": f"append_file_tool does not support {ext}. Use read + write instead.",
        }

    try:
        _ensure_parent(fp)
        with open(fp, "a", encoding="utf-8") as fh:
            fh.write(content)
    except Exception as exc:
        logger.error(f"append_file_tool | failed for '{fp}': {exc}", exc_info=True)
        return {"status": "error", "message": str(exc)}

    logger.info(f"append_file_tool | success | path='{fp}'")
    return {"status": "ok", "message": f"Content appended to: {fp}"}


async def clear_file_tool(file_path: str) -> Dict[str, Any]:
    logger.debug(f"clear_file_tool called | file_path='{file_path}'")
    try:
        fp = safe_path(file_path)
    except ValueError as e:
        logger.warning(f"clear_file_tool | invalid path '{file_path}': {e}")
        return {"status": "error", "message": str(e)}

    if not os.path.exists(fp):
        logger.warning(f"clear_file_tool | file not found: '{fp}'")
        return {"status": "error", "message": f"File not found: {file_path}"}

    ext = get_ext(fp)
    if ext in {".docx", ".xlsx", ".xls", ".pdf", ".pptx"}:
        logger.warning(f"clear_file_tool | unsupported format '{ext}' for '{fp}'")
        return {
            "status": "error",
            "message": f"clear_file_tool does not support {ext}. Use write_file_tool with empty content.",
        }

    open(fp, "w").close()
    logger.info(f"clear_file_tool | success | path='{fp}'")
    return {"status": "ok", "message": f"File cleared: {fp}"}


async def copy_file_tool(source_path: str, destination_path: str) -> Dict[str, Any]:
    logger.debug(f"copy_file_tool called | src='{source_path}' dst='{destination_path}'")
    try:
        src = safe_path(source_path)
        dst = safe_path(destination_path)
    except ValueError as e:
        logger.warning(f"copy_file_tool | invalid path: {e}")
        return {"status": "error", "message": str(e)}

    if not os.path.exists(src):
        logger.warning(f"copy_file_tool | source not found: '{src}'")
        return {"status": "error", "message": f"Source not found: {source_path}"}
    if not os.path.isfile(src):
        logger.warning(f"copy_file_tool | source is not a file: '{src}'")
        return {"status": "error", "message": f"Source is not a file: {source_path}"}

    try:
        _ensure_parent(dst)
        shutil.copy2(src, dst)
    except Exception as exc:
        logger.error(f"copy_file_tool | failed '{src}' → '{dst}': {exc}", exc_info=True)
        return {"status": "error", "message": str(exc)}

    logger.info(f"copy_file_tool | success | '{src}' → '{dst}'")
    return {"status": "ok", "message": f"Copied '{src}' → '{dst}'"}


async def move_file_tool(source_path: str, destination_path: str) -> Dict[str, Any]:
    logger.debug(f"move_file_tool called | src='{source_path}' dst='{destination_path}'")
    try:
        src = safe_path(source_path)
        dst = safe_path(destination_path)
    except ValueError as e:
        logger.warning(f"move_file_tool | invalid path: {e}")
        return {"status": "error", "message": str(e)}

    if not os.path.exists(src):
        logger.warning(f"move_file_tool | source not found: '{src}'")
        return {"status": "error", "message": f"Source not found: {source_path}"}
    if not os.path.isfile(src):
        logger.warning(f"move_file_tool | source is not a file: '{src}'")
        return {"status": "error", "message": f"Source is not a file: {source_path}"}

    try:
        _ensure_parent(dst)
        shutil.move(src, dst)
    except Exception as exc:
        logger.error(f"move_file_tool | failed '{src}' → '{dst}': {exc}", exc_info=True)
        return {"status": "error", "message": str(exc)}

    logger.info(f"move_file_tool | success | '{src}' → '{dst}'")
    return {"status": "ok", "message": f"Moved '{src}' → '{dst}'"}


async def delete_file_tool(file_path: str) -> Dict[str, Any]:
    logger.debug(f"delete_file_tool called | file_path='{file_path}'")
    try:
        fp = safe_path(file_path)
    except ValueError as e:
        logger.warning(f"delete_file_tool | invalid path '{file_path}': {e}")
        return {"status": "error", "message": str(e)}

    if not os.path.exists(fp):
        logger.warning(f"delete_file_tool | file not found: '{fp}'")
        return {"status": "error", "message": f"File not found: {file_path}"}
    if not os.path.isfile(fp):
        logger.warning(f"delete_file_tool | not a file: '{fp}'")
        return {"status": "error", "message": f"Not a file: {file_path}"}

    os.remove(fp)
    logger.info(f"delete_file_tool | success | path='{fp}'")
    return {"status": "ok", "message": f"Deleted file: {fp}"}
