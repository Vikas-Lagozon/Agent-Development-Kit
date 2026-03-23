"""
Directory MCP Module
====================
Strictly directory operations: create, delete, rename, list files/directories, tree view.
"""

import os
import shutil
from typing import Any, Dict, List

from .utils import logger, safe_path, get_ext, BASE_DIR, IGNORED_NAMES

async def create_directory_tool(folder_path: str) -> Dict[str, Any]:
    logger.debug(f"create_directory_tool called | folder_path='{folder_path}'")
    try:
        dp = safe_path(folder_path)
    except ValueError as e:
        logger.warning(f"create_directory_tool | invalid path '{folder_path}': {e}")
        return {"status": "error", "message": str(e)}

    try:
        os.makedirs(dp, exist_ok=True)
    except Exception as exc:
        logger.error(f"create_directory_tool | failed to create '{dp}': {exc}", exc_info=True)
        return {"status": "error", "message": str(exc)}

    logger.info(f"create_directory_tool | success | path='{dp}'")
    return {"status": "ok", "message": f"Directory ready: {dp}", "path": dp}


async def delete_directory_tool(folder_path: str, recursive: bool = False) -> Dict[str, Any]:
    logger.debug(f"delete_directory_tool called | folder_path='{folder_path}' recursive={recursive}")
    try:
        dp = safe_path(folder_path)
    except ValueError as e:
        logger.warning(f"delete_directory_tool | invalid path '{folder_path}': {e}")
        return {"status": "error", "message": str(e)}

    if not os.path.exists(dp):
        logger.warning(f"delete_directory_tool | directory not found: '{dp}'")
        return {"status": "error", "message": f"Directory not found: {folder_path}"}
    if not os.path.isdir(dp):
        logger.warning(f"delete_directory_tool | not a directory: '{dp}'")
        return {"status": "error", "message": f"Not a directory: {folder_path}"}
    if os.path.abspath(dp) == BASE_DIR:
        logger.warning("delete_directory_tool | attempted to delete BASE_DIR — blocked.")
        return {"status": "error", "message": "Cannot delete the base (root) directory."}

    try:
        if recursive:
            shutil.rmtree(dp)
        else:
            os.rmdir(dp)
    except OSError as exc:
        logger.error(f"delete_directory_tool | OSError for '{dp}': {exc}", exc_info=True)
        return {
            "status": "error",
            "message": str(exc) + (
                "  Hint: Pass recursive=true to delete a non-empty directory."
                if not recursive else ""
            ),
        }
    except Exception as exc:
        logger.error(f"delete_directory_tool | failed for '{dp}': {exc}", exc_info=True)
        return {"status": "error", "message": str(exc)}

    logger.info(f"delete_directory_tool | success | path='{dp}'")
    return {"status": "ok", "message": f"Directory deleted: {dp}"}


async def rename_directory_tool(source_path: str, destination_path: str) -> Dict[str, Any]:
    logger.debug(f"rename_directory_tool called | src='{source_path}' dst='{destination_path}'")
    try:
        src = safe_path(source_path)
        dst = safe_path(destination_path)
    except ValueError as e:
        logger.warning(f"rename_directory_tool | invalid path: {e}")
        return {"status": "error", "message": str(e)}

    if not os.path.exists(src):
        logger.warning(f"rename_directory_tool | source not found: '{src}'")
        return {"status": "error", "message": f"Source not found: {source_path}"}
    if not os.path.isdir(src):
        logger.warning(f"rename_directory_tool | source is not a directory: '{src}'")
        return {"status": "error", "message": f"Source is not a directory: {source_path}"}

    try:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.move(src, dst)
    except Exception as exc:
        logger.error(f"rename_directory_tool | failed '{src}' → '{dst}': {exc}", exc_info=True)
        return {"status": "error", "message": str(exc)}

    logger.info(f"rename_directory_tool | success | '{src}' → '{dst}'")
    return {"status": "ok", "message": f"Directory moved/renamed: '{src}' → '{dst}'"}


async def list_files_tool(folder_path: str = ".") -> List[Dict[str, Any]]:
    logger.debug(f"list_files_tool called | folder_path='{folder_path}'")
    try:
        dp = safe_path(folder_path)
    except ValueError as e:
        logger.warning(f"list_files_tool | invalid path '{folder_path}': {e}")
        return [{"status": "error", "message": str(e)}]

    if not os.path.exists(dp):
        logger.warning(f"list_files_tool | directory not found: '{dp}'")
        return [{"status": "error", "message": f"Directory not found: {folder_path}"}]
    if not os.path.isdir(dp):
        logger.warning(f"list_files_tool | not a directory: '{dp}'")
        return [{"status": "error", "message": f"Not a directory: {folder_path}"}]

    result = []
    for name in sorted(os.listdir(dp)):
        if name in IGNORED_NAMES:
            continue
        full = os.path.join(dp, name)
        if os.path.isfile(full):
            result.append({
                "name":          name,
                "relative_path": os.path.relpath(full, BASE_DIR),
                "extension":     get_ext(name),
                "size_bytes":    os.path.getsize(full),
            })

    logger.info(f"list_files_tool | success | found {len(result)} file(s) in '{dp}'")
    return result


async def list_directories_tool(folder_path: str = ".") -> List[Dict[str, Any]]:
    logger.debug(f"list_directories_tool called | folder_path='{folder_path}'")
    try:
        dp = safe_path(folder_path)
    except ValueError as e:
        logger.warning(f"list_directories_tool | invalid path '{folder_path}': {e}")
        return [{"status": "error", "message": str(e)}]

    if not os.path.exists(dp):
        logger.warning(f"list_directories_tool | directory not found: '{dp}'")
        return [{"status": "error", "message": f"Directory not found: {folder_path}"}]
    if not os.path.isdir(dp):
        logger.warning(f"list_directories_tool | not a directory: '{dp}'")
        return [{"status": "error", "message": f"Not a directory: {folder_path}"}]

    result = []
    for name in sorted(os.listdir(dp)):
        if name in IGNORED_NAMES:
            continue
        full = os.path.join(dp, name)
        if os.path.isdir(full):
            result.append({
                "name":          name,
                "relative_path": os.path.relpath(full, BASE_DIR),
            })

    logger.info(f"list_directories_tool | success | found {len(result)} dir(s) in '{dp}'")
    return result


async def list_tree_tool(folder_path: str = ".", max_depth: int = 5) -> Dict[str, Any]:
    max_depth = min(max_depth, 10)
    logger.debug(f"list_tree_tool called | folder_path='{folder_path}' max_depth={max_depth}")

    try:
        dp = safe_path(folder_path)
    except ValueError as e:
        logger.warning(f"list_tree_tool | invalid path '{folder_path}': {e}")
        return {"status": "error", "message": str(e)}

    if not os.path.exists(dp):
        logger.warning(f"list_tree_tool | directory not found: '{dp}'")
        return {"status": "error", "message": f"Directory not found: {folder_path}"}
    if not os.path.isdir(dp):
        logger.warning(f"list_tree_tool | not a directory: '{dp}'")
        return {"status": "error", "message": f"Not a directory: {folder_path}"}

    def _build(path: str, depth: int) -> Dict[str, Any]:
        name = os.path.basename(path) or path
        node: Dict[str, Any] = {"type": "directory", "name": name, "children": []}
        if depth >= max_depth:
            node["children"].append({"type": "truncated", "message": "max_depth reached"})
            return node
        try:
            entries = sorted(os.listdir(path))
        except PermissionError:
            logger.warning(f"list_tree_tool | permission denied: '{path}'")
            node["children"].append({"type": "error", "message": "Permission denied"})
            return node
        for entry in entries:
            if entry in IGNORED_NAMES:
                continue
            full = os.path.join(path, entry)
            if os.path.isdir(full):
                node["children"].append(_build(full, depth + 1))
            else:
                node["children"].append({
                    "type":          "file",
                    "name":          entry,
                    "relative_path": os.path.relpath(full, BASE_DIR),
                    "extension":     get_ext(entry),
                    "size_bytes":    os.path.getsize(full),
                })
        return node

    tree = _build(dp, 0)
    logger.info(f"list_tree_tool | success | root='{dp}'")
    return {"status": "ok", "root": os.path.relpath(dp, BASE_DIR), "tree": tree}