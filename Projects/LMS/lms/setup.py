import subprocess
import sys
import venv
from pathlib import Path

def create_virtual_environment(venv_path: Path) -> None:
    """
    Creates a virtual environment if one doesn't exist.
    """
    if not venv_path.exists():
        print(f"Creating virtual environment at {venv_path}")
        venv.create(venv_path, with_pip=True)
    else:
        print(f"Virtual environment already exists at {venv_path}")

def install_dependencies(venv_path: Path, requirements_path: Path) -> None:
    """
    Installs dependencies from the requirements.txt file into the virtual environment.
    """
    pip_executable = venv_path / "bin" / "pip" if sys.platform != "win32" else venv_path / "Scripts" / "pip.exe"

    if not pip_executable.exists():
        print(f"Error: pip executable not found at {pip_executable}")
        sys.exit(1)

    if not requirements_path.exists():
        print(f"Error: requirements.txt not found at {requirements_path}")
        sys.exit(1)

    print(f"Installing dependencies from {requirements_path} into {venv_path}")
    try:
        subprocess.check_call(
            [str(pip_executable), "install", "-r", str(requirements_path)],
            stdout=sys.stdout,
            stderr=sys.stderr,
        )
    except subprocess.CalledProcessError as e:
        print(f"Error installing dependencies: {e}")
        sys.exit(1)

def main() -> None:
    """
    Main function to set up the virtual environment and install dependencies.
    """
    project_root = Path(__file__).parent
    venv_path = project_root / ".venv"
    requirements_path = project_root / "requirements.txt"

    create_virtual_environment(venv_path)
    install_dependencies(venv_path, requirements_path)

if __name__ == "__main__":
    main()