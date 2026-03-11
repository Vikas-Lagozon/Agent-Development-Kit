"""
Directory MCP Module
====================
Strictly directory operations: create, delete, rename, list files/directories, tree view.
"""

import os
import shutil
from typing import Any, Dict, List

from .utils import safe_path, get_ext, BASE_DIR


async def create_directory_tool(folder_path: str) -> Dict[str, Any]:
    try:
        dp = safe_path(folder_path)
    except ValueError as e:
        return {"status": "error", "message": str(e)}

    try:
        os.makedirs(dp, exist_ok=True)
    except Exception as exc:
        return {"status": "error", "message": str(exc)}

    return {"status": "ok", "message": f"Directory ready: {dp}", "path": dp}


async def delete_directory_tool(folder_path: str, recursive: bool = False) -> Dict[str, Any]:
    try:
        dp = safe_path(folder_path)
    except ValueError as e:
        return {"status": "error", "message": str(e)}

    if not os.path.exists(dp):
        return {"status": "error", "message": f"Directory not found: {folder_path}"}
    if not os.path.isdir(dp):
        return {"status": "error", "message": f"Not a directory: {folder_path}"}
    if os.path.abspath(dp) == BASE_DIR:
        return {"status": "error", "message": "Cannot delete the base (root) directory."}

    try:
        if recursive:
            shutil.rmtree(dp)
        else:
            os.rmdir(dp)
    except OSError as exc:
        return {
            "status": "error",
            "message": str(exc) + (
                "  Hint: Pass recursive=true to delete a non-empty directory."
                if not recursive else ""
            ),
        }
    except Exception as exc:
        return {"status": "error", "message": str(exc)}

    return {"status": "ok", "message": f"Directory deleted: {dp}"}


async def rename_directory_tool(source_path: str, destination_path: str) -> Dict[str, Any]:
    try:
        src = safe_path(source_path)
        dst = safe_path(destination_path)
    except ValueError as e:
        return {"status": "error", "message": str(e)}

    if not os.path.exists(src):
        return {"status": "error", "message": f"Source not found: {source_path}"}
    if not os.path.isdir(src):
        return {"status": "error", "message": f"Source is not a directory: {source_path}"}

    try:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.move(src, dst)
    except Exception as exc:
        return {"status": "error", "message": str(exc)}

    return {"status": "ok", "message": f"Directory moved/renamed: '{src}' → '{dst}'"}


async def list_files_tool(folder_path: str = ".") -> List[Dict[str, Any]]:
    try:
        dp = safe_path(folder_path)
    except ValueError as e:
        return [{"status": "error", "message": str(e)}]

    if not os.path.exists(dp):
        return [{"status": "error", "message": f"Directory not found: {folder_path}"}]
    if not os.path.isdir(dp):
        return [{"status": "error", "message": f"Not a directory: {folder_path}"}]

    result = []
    for name in sorted(os.listdir(dp)):
        full = os.path.join(dp, name)
        if os.path.isfile(full):
            result.append({
                "name":          name,
                "relative_path": os.path.relpath(full, BASE_DIR),
                "extension":     get_ext(name),
                "size_bytes":    os.path.getsize(full),
            })
    return result


async def list_directories_tool(folder_path: str = ".") -> List[Dict[str, Any]]:
    try:
        dp = safe_path(folder_path)
    except ValueError as e:
        return [{"status": "error", "message": str(e)}]

    if not os.path.exists(dp):
        return [{"status": "error", "message": f"Directory not found: {folder_path}"}]
    if not os.path.isdir(dp):
        return [{"status": "error", "message": f"Not a directory: {folder_path}"}]

    result = []
    for name in sorted(os.listdir(dp)):
        full = os.path.join(dp, name)
        if os.path.isdir(full):
            result.append({
                "name":          name,
                "relative_path": os.path.relpath(full, BASE_DIR),
            })
    return result


async def list_tree_tool(folder_path: str = ".", max_depth: int = 5) -> Dict[str, Any]:
    max_depth = min(max_depth, 10)

    try:
        dp = safe_path(folder_path)
    except ValueError as e:
        return {"status": "error", "message": str(e)}

    if not os.path.exists(dp):
        return {"status": "error", "message": f"Directory not found: {folder_path}"}
    if not os.path.isdir(dp):
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
            node["children"].append({"type": "error", "message": "Permission denied"})
            return node
        for entry in entries:
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
    return {"status": "ok", "root": os.path.relpath(dp, BASE_DIR), "tree": tree}