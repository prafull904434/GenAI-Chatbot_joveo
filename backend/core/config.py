from pathlib import Path
from dotenv import load_dotenv


def load_environment():
    """Loads environment variables from .env file at project root."""
    base_dir = Path(__file__).resolve().parent.parent.parent
    load_dotenv(dotenv_path=base_dir / ".env", override=True)