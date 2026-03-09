"""
Metadata MCP Module
===================
Strictly file/folder metadata: info (size, timestamps, etc.), supported formats.
"""

import os
from typing import Any, Dict

from .utils import (
    safe_path, get_ext, READ_DISPATCH, TEXT_EXTENSIONS, BASE_DIR,
    HAS_DOCX, HAS_XLSX, HAS_PDF_READ, HAS_PDF_WRITE, HAS_PPTX
)


async def file_info_tool(file_path: str) -> Dict[str, Any]:
    try:
        fp = safe_path(file_path)
    except ValueError as e:
        return {"status": "error", "message": str(e)}

    if not os.path.exists(fp):
        return {"status": "error", "message": f"Path not found: {file_path}"}

    stat = os.stat(fp)
    ext  = get_ext(fp)

    if ext in READ_DISPATCH:
        fmt = ext.lstrip(".")
    elif ext in TEXT_EXTENSIONS:
        fmt = "text"
    elif os.path.isdir(fp):
        fmt = "directory"
    else:
        fmt = "binary/unknown"

    return {
        "status":        "ok",
        "file_path":     fp,
        "extension":     ext,
        "format":        fmt,
        "size_bytes":    stat.st_size,
        "created_time":  stat.st_ctime,
        "modified_time": stat.st_mtime,
        "is_file":       os.path.isfile(fp),
        "is_directory":  os.path.isdir(fp),
    }


async def supported_formats_tool() -> Dict[str, Any]:
    return {
        "status":        "ok",
        "base_directory": BASE_DIR,
        "read_and_write": {
            "text/code/config": {
                "extensions": sorted(TEXT_EXTENSIONS),
                "requires":   "built-in",
                "installed":  True,
            },
            "json":     {"extensions": [".json"],         "requires": "built-in",    "installed": True},
            "csv/tsv":  {"extensions": [".csv", ".tsv"],  "requires": "built-in",    "installed": True},
            "docx":     {"extensions": [".docx"],         "requires": "python-docx", "installed": HAS_DOCX},
            "xlsx/xls": {"extensions": [".xlsx", ".xls"], "requires": "openpyxl",    "installed": HAS_XLSX},
            "pptx":     {"extensions": [".pptx"],         "requires": "python-pptx", "installed": HAS_PPTX},
        },
        "read_only": {
            "pdf": {"extensions": [".pdf"], "requires": "pdfplumber", "installed": HAS_PDF_READ},
        },
        "write_only": {
            "pdf (new file)": {"extensions": [".pdf"], "requires": "reportlab", "installed": HAS_PDF_WRITE},
        },
        "fallback": {
            "binary": {
                "extensions": ["any unrecognised extension"],
                "read":       "returned as base64 string",
                "write":      "content decoded from base64 to bytes",
                "requires":   "built-in",
            },
        },
    }

