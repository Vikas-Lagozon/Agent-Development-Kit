"""
Config Module
=============
Reads environment variables from the .env file using python-dotenv.
All other modules import from here — no direct .env access elsewhere.
"""

import os
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

# =============================================================================
# FileSystem MCP Settings
# =============================================================================

# Base directory for the FileSystem MCP sandbox.
# Must be set in .env as:  BASE_DIR=D:\Agent-Development-Kit\adk23\Vikas
BASE_DIR: str = os.getenv("BASE_DIR", "")

if not BASE_DIR:
    raise EnvironmentError(
        "BASE_DIR is not set. Please add BASE_DIR=<your_path> to your .env file."
    )

BASE_DIR = os.path.abspath(BASE_DIR)

