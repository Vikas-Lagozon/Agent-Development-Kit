import os
import fnmatch

IGNORE_NAMES = [".*", "_*", "__*", "venv", ".ipynb", "*.json", "log"]

def should_ignore(name):
    """Check if a file or directory should be ignored based on IGNORE_NAMES patterns."""
    for pattern in IGNORE_NAMES:
        if fnmatch.fnmatch(name, pattern):
            return True
    return False

def explain_directory(path, indent=""):
    if not os.path.exists(path):
        print(f"Path '{path}' does not exist.")
        return
    
    if not os.path.isdir(path):
        print(f"Path '{path}' is not a directory.")
        return

    entries = os.listdir(path)
    entries = [e for e in entries if not should_ignore(e)]  # filter ignored files

    for i, entry in enumerate(entries):
        entry_path = os.path.join(path, entry)
        is_last = i == len(entries) - 1
        prefix = "└── " if is_last else "├── "

        if os.path.isdir(entry_path):
            # It's a subdirectory
            print(f"{indent}{prefix}[DIR] {entry}")
            explain_directory(entry_path, indent + ("    " if is_last else "│   "))
        else:
            # It's a file
            size = os.path.getsize(entry_path)
            print(f"{indent}{prefix}[FILE] {entry} ({size} bytes)")

if __name__ == "__main__":
    dir_path = r"D:\Agent-Development-Kit\adk33-Gemini_Live_API_Toolkit\Agents"
    print(f"Directory tree for: {dir_path}\n")
    explain_directory(dir_path)

