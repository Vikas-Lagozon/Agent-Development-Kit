import os

def explain_directory(path, indent=""):
    if not os.path.exists(path):
        print(f"Path '{path}' does not exist.")
        return
    
    if not os.path.isdir(path):
        print(f"Path '{path}' is not a directory.")
        return

    entries = os.listdir(path)
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
    # dir_path = input("Enter the directory path: ").strip()
    dir_path = r"D:\Agent-Development-Kit\adk27"
    print(f"Directory tree for: {dir_path}\n")
    explain_directory(dir_path)









# D:\Agent-Development-Kit\adk27>python dir.py
# Directory tree for: D:\Agent-Development-Kit\adk27

# ├── [FILE] .env (1160 bytes)
# ├── [FILE] app.py (16784 bytes)
# ├── [FILE] chatbot-stream.py (9924 bytes)
# ├── [FILE] chatbot.py (11124 bytes)
# ├── [FILE] config.py (2067 bytes)
# ├── [DIR] MCPServer
# │   ├── [FILE] expenses.db (12288 bytes)
# │   ├── [FILE] expense_tracker_mcp_server.py (7761 bytes)
# │   ├── [DIR] FileSystem
# │   │   ├── [FILE] directory_mcp.py (5930 bytes)
# │   │   ├── [FILE] file_mcp.py (6909 bytes)
# │   │   ├── [FILE] metadata_mcp.py (2785 bytes)
# │   │   ├── [FILE] utils.py (11299 bytes)
# │   │   ├── [FILE] __init__.py (0 bytes)
# │   ├── [FILE] file_system_mcp_server.py (38180 bytes)
# │   ├── [FILE] my_adk_mcp_server.py (3603 bytes)
# │   ├── [FILE] server.py (4342 bytes)
# │   ├── [FILE] todo.db (12288 bytes)
# │   ├── [FILE] to_do_mcp_server.py (7977 bytes)
# ├── [FILE] modified-alloy-483408-q0-09459f82078f.json (2406 bytes)
# ├── [FILE] README.md (671 bytes)
# ├── [FILE] requirements.txt (6709 bytes)
# ├── [FILE] research.py (2948 bytes)
# ├── [DIR] static
# │   ├── [FILE] script.js (27062 bytes)
# │   └── [FILE] style.css (21627 bytes)
# ├── [DIR] templates
# │   └── [FILE] index.html (5659 bytes)
