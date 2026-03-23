"""
Dynamic Cross-Platform Code Execution MCP Module
=================================================
Execute code files in ANY project structure.
Automatically searches for files, handles relative/absolute paths, and adapts to any directory layout.
"""

import os
import shlex
import subprocess
import json
from typing import Any, Dict, Optional, Tuple
from pathlib import Path

# Import from utils
from .utils import (
    PlatformInfo,
    LANGUAGE_MAP,
    logger,
    is_supported_on_platform,
    get_language_info,
    get_platform_suggestion,
    get_installation_hint,
    check_available_tools,
)


# ============================================================================
# FILE DISCOVERY & PATH RESOLUTION
# ============================================================================

def find_file(file_path: str, search_from: Optional[str] = None) -> Optional[str]:
    """
    Dynamically find a file in ANY project structure.
    
    Tries multiple strategies:
    1. Direct path (absolute or relative to current directory)
    2. Relative to search_from directory
    3. Search upward in parent directories
    4. Search downward in subdirectories
    5. Search from project root (if found)
    
    Args:
        file_path: File name or relative path to find
        search_from: Optional starting directory for search
    
    Returns:
        Absolute path to file if found, None otherwise
    """
    logger.info(f"Finding file: {file_path}")
    
    # Strategy 1: Direct path exists as-is
    if os.path.isfile(file_path):
        logger.info(f"Found at direct path: {file_path}")
        return os.path.abspath(file_path)
    
    # Strategy 2: Relative to search_from
    if search_from:
        candidate = os.path.join(search_from, file_path)
        if os.path.isfile(candidate):
            logger.info(f"Found relative to search_from: {candidate}")
            return os.path.abspath(candidate)
    
    # Strategy 3: Search upward from current directory
    start_dir = os.path.abspath(search_from or os.getcwd())
    current = start_dir
    
    for _ in range(10):  # Limit search depth to avoid infinite loops
        candidate = os.path.join(current, file_path)
        if os.path.isfile(candidate):
            logger.info(f"Found searching upward: {candidate}")
            return os.path.abspath(candidate)
        
        parent = os.path.dirname(current)
        if parent == current:  # Reached root
            break
        current = parent
    
    # Strategy 4: Search downward from start_dir (recursive)
    for root, dirs, files in os.walk(start_dir):
        # Avoid searching too deep
        if root.count(os.sep) - start_dir.count(os.sep) > 5:
            continue
        
        file_name = os.path.basename(file_path)
        if file_name in files:
            candidate = os.path.join(root, file_name)
            logger.info(f"Found searching downward: {candidate}")
            return os.path.abspath(candidate)
    
    # Strategy 5: If file_path contains directories, try flexible matching
    file_name = os.path.basename(file_path)
    path_parts = Path(file_path).parts
    
    for root, dirs, files in os.walk(start_dir):
        if root.count(os.sep) - start_dir.count(os.sep) > 10:
            continue
        
        for f in files:
            if f == file_name:
                candidate = os.path.join(root, f)
                logger.info(f"Found with flexible matching: {candidate}")
                return os.path.abspath(candidate)
    
    logger.warning(f"File not found anywhere: {file_path}")
    return None


def get_project_root(start_dir: Optional[str] = None) -> str:
    """
    Find project root by looking for common markers.
    
    Looks for:
    - .git directory
    - setup.py
    - pyproject.toml
    - requirements.txt
    - .env
    """
    current = os.path.abspath(start_dir or os.getcwd())
    
    markers = ['.git', 'setup.py', 'pyproject.toml', 'requirements.txt', '.env', '.gitignore']
    
    for _ in range(20):  # Limit iterations
        for marker in markers:
            if os.path.exists(os.path.join(current, marker)):
                logger.info(f"Project root found at: {current}")
                return current
        
        parent = os.path.dirname(current)
        if parent == current:  # Reached filesystem root
            break
        current = parent
    
    logger.info(f"Project root not found, using start dir: {current}")
    return start_dir or os.getcwd()


def resolve_file_path(file_path: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Resolve file path using multiple strategies.
    
    Returns:
        Tuple of (resolved_path, working_directory)
    """
    # Try to find the file
    resolved = find_file(file_path)
    
    if resolved:
        working_dir = os.path.dirname(resolved)
        return resolved, working_dir
    
    # If not found, try alternative approaches
    logger.warning(f"File not found with default search: {file_path}")
    
    # Try from project root
    project_root = get_project_root()
    resolved = find_file(file_path, search_from=project_root)
    
    if resolved:
        working_dir = os.path.dirname(resolved)
        return resolved, working_dir
    
    # If still not found, return None but working_dir as project root
    return None, project_root


# ============================================================================
# MAIN EXECUTION FUNCTIONS (SYNCHRONOUS)
# ============================================================================

def run_code(
    file_path: str,
    args: str = "",
    timeout: int = 300,
    working_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Execute a code file in ANY project structure.
    Dynamically finds files and adapts to different directory layouts.
    
    Args:
        file_path: File name or relative path (e.g., "script.py", "src/main.py", "tests/test.py")
        args: Command-line arguments as a string
        timeout: Execution timeout in seconds
        working_dir: Optional working directory override
    
    Returns:
        Dict with status, returncode, stdout, stderr, and platform info
    """
    logger.info(f"run_code | Searching for: '{file_path}' | working_dir={working_dir}")
    
    # Resolve file path dynamically
    resolved_path, inferred_working_dir = resolve_file_path(file_path)
    
    if not resolved_path:
        logger.error(f"File not found (searched everywhere): {file_path}")
        return {
            "status": "error",
            "message": f"File not found: {file_path}",
            "searched_from": os.getcwd(),
            "project_root": get_project_root(),
            "suggestions": [
                "Try using relative path from project root",
                "Check file name spelling and case",
                "Use find_file() to locate the file first"
            ]
        }
    
    logger.info(f"File found at: {resolved_path}")
    
    # Get language information
    ext = os.path.splitext(resolved_path)[1].lower()
    lang_info = get_language_info(resolved_path)
    
    if not lang_info:
        logger.warning(f"Unsupported extension: {ext}")
        return {
            "status": "error",
            "message": f"Unsupported file type: {ext}",
            "file_path": resolved_path,
            "supported_types": list(LANGUAGE_MAP.keys()),
        }
    
    # Check platform support
    if not is_supported_on_platform(lang_info):
        logger.warning(f"{lang_info['name']} not supported on {PlatformInfo.SYSTEM}")
        return {
            "status": "error",
            "message": f"{lang_info['name']} not supported on {PlatformInfo.SYSTEM}",
            "language": lang_info["name"],
            "platform": PlatformInfo.SYSTEM,
            "suggestion": get_platform_suggestion(lang_info),
        }
    
    logger.info(f"Executing: {lang_info['name']} | {resolved_path}")
    
    # Handle different file types
    file_type = lang_info.get("type")
    
    # Use inferred working dir if not provided
    final_working_dir = working_dir or inferred_working_dir
    
    if file_type == "script":
        return _execute_script(resolved_path, args, lang_info, timeout, final_working_dir)
    elif file_type == "compiled":
        return _execute_compiled(resolved_path, args, lang_info, timeout, final_working_dir)
    elif file_type == "query":
        return _validate_query(resolved_path, lang_info)
    elif file_type == "data":
        return _validate_data(resolved_path, lang_info)
    else:
        return {
            "status": "error",
            "message": f"Unknown file type: {file_type}",
        }


def _execute_script(
    file_path: str,
    args: str,
    lang_info: Dict[str, Any],
    timeout: int,
    working_dir: Optional[str],
) -> Dict[str, Any]:
    """Execute a script file."""
    try:
        # Parse arguments
        parsed_args = shlex.split(args) if args else []
        interpreter = lang_info["interpreter"]
        cmd = [interpreter, file_path] + parsed_args
        
        # Determine working directory
        cwd = working_dir or os.path.dirname(os.path.abspath(file_path))
        env = os.environ.copy()
        
        logger.info(f"Executing: {' '.join(cmd)} | cwd={cwd}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
            env=env,
        )
        
        logger.info(f"Completed with returncode={result.returncode}")
        
        return {
            "status": "ok",
            "file_path": file_path,
            "working_directory": cwd,
            "language": lang_info["name"],
            "type": "script",
            "platform": PlatformInfo.SYSTEM,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "args": parsed_args,
            "command": " ".join(cmd),
        }
    
    except subprocess.TimeoutExpired:
        logger.error(f"Timeout ({timeout}s)")
        return {
            "status": "error",
            "message": f"Timeout ({timeout}s exceeded)",
            "file_path": file_path,
            "language": lang_info["name"],
        }
    
    except FileNotFoundError:
        logger.error(f"Interpreter not found: {lang_info['interpreter']}")
        return {
            "status": "error",
            "message": f"Interpreter not found: {lang_info['interpreter']}",
            "file_path": file_path,
            "language": lang_info["name"],
            "hint": get_installation_hint(lang_info["name"]),
        }
    
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return {
            "status": "error",
            "message": str(e),
            "file_path": file_path,
            "language": lang_info["name"],
        }


def _execute_compiled(
    file_path: str,
    args: str,
    lang_info: Dict[str, Any],
    timeout: int,
    working_dir: Optional[str],
) -> Dict[str, Any]:
    """Compile and execute a compiled language file."""
    try:
        file_dir = working_dir or os.path.dirname(os.path.abspath(file_path))
        file_name = os.path.basename(file_path)
        file_base = os.path.splitext(file_name)[0]
        
        exe_ext = PlatformInfo.get_executable_extension()
        output_exe = os.path.join(file_dir, f"{file_base}{exe_ext}")
        
        compiler = lang_info["compiler"]
        lang_name = lang_info["name"]
        
        if lang_name == "Go":
            compile_cmd = [compiler, "run", file_path]
            is_direct_run = True
        else:
            compile_cmd = [compiler, file_path, "-o", output_exe]
            is_direct_run = False
        
        logger.info(f"Compiling: {' '.join(compile_cmd)}")
        
        compile_result = subprocess.run(
            compile_cmd,
            capture_output=True,
            text=True,
            timeout=60,
            cwd=file_dir,
        )
        
        if compile_result.returncode != 0:
            logger.error(f"Compilation failed")
            return {
                "status": "error",
                "message": "Compilation failed",
                "file_path": file_path,
                "language": lang_name,
                "type": "compiled",
                "stderr": compile_result.stderr,
                "stdout": compile_result.stdout,
            }
        
        if is_direct_run:
            return {
                "status": "ok",
                "file_path": file_path,
                "language": lang_name,
                "type": "compiled",
                "platform": PlatformInfo.SYSTEM,
                "returncode": compile_result.returncode,
                "stdout": compile_result.stdout,
                "stderr": compile_result.stderr,
            }
        
        if not os.path.exists(output_exe):
            return {
                "status": "error",
                "message": f"Executable not created: {output_exe}",
                "file_path": file_path,
                "language": lang_name,
            }
        
        parsed_args = shlex.split(args) if args else []
        run_cmd = [output_exe] + parsed_args
        
        logger.info(f"Running: {' '.join(run_cmd)}")
        
        run_result = subprocess.run(
            run_cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=file_dir,
        )
        
        logger.info(f"Execution completed")
        
        return {
            "status": "ok",
            "file_path": file_path,
            "language": lang_name,
            "type": "compiled",
            "platform": PlatformInfo.SYSTEM,
            "returncode": run_result.returncode,
            "stdout": run_result.stdout,
            "stderr": run_result.stderr,
            "executable": output_exe,
            "args": parsed_args,
        }
    
    except subprocess.TimeoutExpired:
        logger.error(f"Timeout")
        return {
            "status": "error",
            "message": f"Timeout ({timeout}s exceeded)",
            "file_path": file_path,
            "language": lang_info["name"],
        }
    
    except FileNotFoundError:
        logger.error(f"Compiler not found: {lang_info['compiler']}")
        return {
            "status": "error",
            "message": f"Compiler not found: {lang_info['compiler']}",
            "file_path": file_path,
            "language": lang_info["name"],
            "hint": get_installation_hint(lang_info["name"]),
        }
    
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return {
            "status": "error",
            "message": str(e),
            "file_path": file_path,
            "language": lang_info["name"],
        }


def _validate_query(file_path: str, lang_info: Dict[str, Any]) -> Dict[str, Any]:
    """Validate query files."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return {
            "status": "ok",
            "file_path": file_path,
            "type": "query",
            "language": lang_info["name"],
            "content": content,
            "length": len(content),
        }
    
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return {
            "status": "error",
            "message": str(e),
            "file_path": file_path,
        }


def _validate_data(file_path: str, lang_info: Dict[str, Any]) -> Dict[str, Any]:
    """Validate data format files."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        data_type = lang_info["name"]
        
        if data_type == "JSON":
            try:
                parsed = json.loads(content)
                return {
                    "status": "ok",
                    "file_path": file_path,
                    "type": "data",
                    "language": data_type,
                    "valid": True,
                    "message": "Valid JSON",
                    "content": json.dumps(parsed, indent=2),
                }
            except json.JSONDecodeError as e:
                return {
                    "status": "error",
                    "message": f"Invalid JSON: {str(e)}",
                    "file_path": file_path,
                    "language": data_type,
                }
        
        return {
            "status": "ok",
            "file_path": file_path,
            "type": "data",
            "language": data_type,
            "valid": True,
            "message": f"Valid {data_type}",
            "content": content,
            "length": len(content),
        }
    
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return {
            "status": "error",
            "message": str(e),
            "file_path": file_path,
        }


def get_platform_info() -> Dict[str, Any]:
    """Get platform information."""
    import platform as platform_module
    return {
        "system": PlatformInfo.SYSTEM,
        "is_windows": PlatformInfo.IS_WINDOWS,
        "is_linux": PlatformInfo.IS_LINUX,
        "is_macos": PlatformInfo.IS_MACOS,
        "python_version": platform_module.python_version(),
        "python_executable": PlatformInfo.PYTHON_CMD,
        "current_directory": os.getcwd(),
        "project_root": get_project_root(),
        "available_tools": check_available_tools(),
    }


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def list_files(pattern: str = "*", max_depth: int = 5) -> Dict[str, Any]:
    """
    List files matching pattern in current project.
    Useful for discovering available files.
    
    Args:
        pattern: File pattern (e.g., "*.py", "*test*", "main.py")
        max_depth: Maximum search depth
    
    Returns:
        Dict with found files and structure
    """
    from fnmatch import fnmatch
    
    root = get_project_root()
    found_files = []
    
    for dirpath, dirnames, filenames in os.walk(root):
        depth = dirpath.count(os.sep) - root.count(os.sep)
        if depth > max_depth:
            continue
        
        for filename in filenames:
            if fnmatch(filename, pattern):
                full_path = os.path.join(dirpath, filename)
                rel_path = os.path.relpath(full_path, root)
                found_files.append({
                    "relative_path": rel_path,
                    "absolute_path": full_path,
                    "size": os.path.getsize(full_path),
                })
    
    logger.info(f"Found {len(found_files)} files matching {pattern}")
    
    return {
        "pattern": pattern,
        "project_root": root,
        "files_found": len(found_files),
        "files": found_files,
    }