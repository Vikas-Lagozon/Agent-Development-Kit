from pathlib import Path

def load_instructions_from_file(filename: str) -> str:
    """
    Load instruction text from a file located in the same package.
    """
    base_dir = Path(__file__).parent.resolve()
    file_path = base_dir / filename

    if not file_path.exists():
        raise FileNotFoundError(f"Instruction file not found: {file_path}")

    return file_path.read_text(encoding="utf-8")

