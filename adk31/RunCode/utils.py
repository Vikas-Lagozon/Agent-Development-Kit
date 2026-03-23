"""
Shared Utilities for FileSystem MCP Package
===========================================
Centralizes path safety, format detection, read/write helpers, library checks,
and constants. Imported by other modules.

BASE_DIR is now sourced exclusively from config.py (which reads .env).
IGNORED_NAMES is now sourced exclusively from config.py (which reads .env).
"""

import os
import sys
import platform
import subprocess
from typing import Any, Dict, Optional


# ============================================================================
# PLATFORM DETECTION & CODE EXECUTION UTILITIES
# ============================================================================
# ADD THIS TO END OF YOUR utils.py
# This is the SINGLE SOURCE OF TRUTH for all cross-platform code execution


class PlatformInfo:
    """Detect and provide OS-specific information for code execution."""
    
    SYSTEM = platform.system()  # 'Windows', 'Linux', 'Darwin' (macOS)
    IS_WINDOWS = SYSTEM == 'Windows'
    IS_LINUX = SYSTEM == 'Linux'
    IS_MACOS = SYSTEM == 'Darwin'
    IS_POSIX = os.name == 'posix'
    
    PYTHON_CMD = sys.executable
    
    @staticmethod
    def get_shell():
        """Get appropriate shell for the OS."""
        return "powershell" if PlatformInfo.IS_WINDOWS else "bash"
    
    @staticmethod
    def get_executable_extension():
        """Get executable extension for the OS."""
        return ".exe" if PlatformInfo.IS_WINDOWS else ""
    
    @staticmethod
    def get_path_separator():
        """Get path separator for the OS."""
        return "\\" if PlatformInfo.IS_WINDOWS else "/"
    
    @staticmethod
    def which(command: str) -> Optional[str]:
        """Cross-platform version of 'which' command."""
        try:
            result = subprocess.run(
                ["where" if PlatformInfo.IS_WINDOWS else "which", command],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.stdout.strip() if result.returncode == 0 else None
        except Exception:
            return None


# Language mappings for code execution (30+ languages)
LANGUAGE_MAP = {
    ".py": {"interpreter": sys.executable, "type": "script", "name": "Python", "windows_ok": True, "linux_ok": True, "macos_ok": True},
    ".sh": {"interpreter": "bash", "type": "script", "name": "Bash", "windows_ok": False, "linux_ok": True, "macos_ok": True},
    ".bash": {"interpreter": "bash", "type": "script", "name": "Bash", "windows_ok": False, "linux_ok": True, "macos_ok": True},
    ".ps1": {"interpreter": "powershell" if PlatformInfo.IS_WINDOWS else None, "type": "script", "name": "PowerShell", "windows_ok": True, "linux_ok": False, "macos_ok": False},
    ".js": {"interpreter": "node", "type": "script", "name": "JavaScript", "windows_ok": True, "linux_ok": True, "macos_ok": True},
    ".ts": {"interpreter": "ts-node", "type": "script", "name": "TypeScript", "windows_ok": True, "linux_ok": True, "macos_ok": True},
    ".rb": {"interpreter": "ruby", "type": "script", "name": "Ruby", "windows_ok": True, "linux_ok": True, "macos_ok": True},
    ".php": {"interpreter": "php", "type": "script", "name": "PHP", "windows_ok": True, "linux_ok": True, "macos_ok": True},
    ".pl": {"interpreter": "perl", "type": "script", "name": "Perl", "windows_ok": True, "linux_ok": True, "macos_ok": True},
    ".lua": {"interpreter": "lua", "type": "script", "name": "Lua", "windows_ok": True, "linux_ok": True, "macos_ok": True},
    ".r": {"interpreter": "Rscript", "type": "script", "name": "R", "windows_ok": True, "linux_ok": True, "macos_ok": True},
    ".R": {"interpreter": "Rscript", "type": "script", "name": "R", "windows_ok": True, "linux_ok": True, "macos_ok": True},
    ".go": {"compiler": "go", "type": "compiled", "name": "Go", "windows_ok": True, "linux_ok": True, "macos_ok": True},
    ".rs": {"compiler": "rustc", "type": "compiled", "name": "Rust", "windows_ok": True, "linux_ok": True, "macos_ok": True},
    ".c": {"compiler": "gcc", "type": "compiled", "name": "C", "windows_ok": True, "linux_ok": True, "macos_ok": True},
    ".cpp": {"compiler": "g++", "type": "compiled", "name": "C++", "windows_ok": True, "linux_ok": True, "macos_ok": True},
    ".cc": {"compiler": "g++", "type": "compiled", "name": "C++", "windows_ok": True, "linux_ok": True, "macos_ok": True},
    ".cxx": {"compiler": "g++", "type": "compiled", "name": "C++", "windows_ok": True, "linux_ok": True, "macos_ok": True},
    ".cs": {"compiler": "csc", "type": "compiled", "name": "C#", "windows_ok": True, "linux_ok": True, "macos_ok": True},
    ".java": {"compiler": "javac", "type": "compiled", "name": "Java", "windows_ok": True, "linux_ok": True, "macos_ok": True},
    ".swift": {"compiler": "swift", "type": "compiled", "name": "Swift", "windows_ok": True, "linux_ok": True, "macos_ok": True},
    ".sql": {"type": "query", "name": "SQL", "windows_ok": True, "linux_ok": True, "macos_ok": True},
    ".graphql": {"type": "query", "name": "GraphQL", "windows_ok": True, "linux_ok": True, "macos_ok": True},
    ".gql": {"type": "query", "name": "GraphQL", "windows_ok": True, "linux_ok": True, "macos_ok": True},
    ".json": {"type": "data", "name": "JSON", "windows_ok": True, "linux_ok": True, "macos_ok": True},
    ".yaml": {"type": "data", "name": "YAML", "windows_ok": True, "linux_ok": True, "macos_ok": True},
    ".yml": {"type": "data", "name": "YAML", "windows_ok": True, "linux_ok": True, "macos_ok": True},
    ".xml": {"type": "data", "name": "XML", "windows_ok": True, "linux_ok": True, "macos_ok": True},
    ".md": {"type": "data", "name": "Markdown", "windows_ok": True, "linux_ok": True, "macos_ok": True},
}


def is_supported_on_platform(lang_info: Dict[str, Any]) -> bool:
    """Check if language is supported on current platform."""
    if PlatformInfo.IS_WINDOWS:
        return lang_info.get("windows_ok", False)
    elif PlatformInfo.IS_LINUX:
        return lang_info.get("linux_ok", False)
    elif PlatformInfo.IS_MACOS:
        return lang_info.get("macos_ok", False)
    return False


def get_language_info(file_path: str) -> Optional[Dict[str, Any]]:
    """Get language information for a file extension."""
    ext = os.path.splitext(file_path)[1].lower()
    return LANGUAGE_MAP.get(ext, None)


def get_platform_suggestion(lang_info: Dict[str, Any]) -> str:
    """Get platform-specific suggestions for unsupported languages."""
    lang_name = lang_info.get("name", "Unknown")
    if lang_name == "Bash" and PlatformInfo.IS_WINDOWS:
        return "Use: Git Bash, WSL, or PowerShell (.ps1)"
    return f"{lang_name} not available on {PlatformInfo.SYSTEM}"


def get_installation_hint(language_name: str) -> str:
    """Get OS-specific installation hints."""
    hints = {
        "Python": {
            "Windows": "python.org or choco install python",
            "Linux": "sudo apt-get install python3",
            "Darwin": "brew install python3",
        },
        "Node.js": {
            "Windows": "nodejs.org or choco install nodejs",
            "Linux": "sudo apt-get install nodejs npm",
            "Darwin": "brew install node",
        },
        "Go": {
            "Windows": "golang.org or choco install golang",
            "Linux": "sudo apt-get install golang-go",
            "Darwin": "brew install go",
        },
        "Rust": {
            "Windows": "rustup.rs",
            "Linux": "curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh",
            "Darwin": "brew install rust",
        },
    }
    
    if language_name in hints:
        hint = hints[language_name].get(PlatformInfo.SYSTEM, "")
        if hint:
            return hint
    return f"Install {language_name}"


def check_available_tools() -> Dict[str, bool]:
    """Check which interpreters/compilers are available."""
    tools = {
        "python": bool(PlatformInfo.which("python3") or PlatformInfo.which("python")),
        "node": bool(PlatformInfo.which("node")),
        "ruby": bool(PlatformInfo.which("ruby")),
        "php": bool(PlatformInfo.which("php")),
        "perl": bool(PlatformInfo.which("perl")),
        "go": bool(PlatformInfo.which("go")),
        "rust": bool(PlatformInfo.which("rustc")),
        "gcc": bool(PlatformInfo.which("gcc")),
        "java": bool(PlatformInfo.which("javac")),
        "bash": bool(PlatformInfo.which("bash")),
        "powershell": bool(PlatformInfo.which("powershell")),
    }
    return {k: v for k, v in tools.items() if v}
