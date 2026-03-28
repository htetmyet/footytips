import os
from pathlib import Path


def load_dotenv(path: str = '.env') -> None:
    env_path = Path(path)
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding='utf-8').splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#'):
            continue
        if '=' not in line:
            continue

        key, value = line.split('=', 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        if key and key not in os.environ:
            os.environ[key] = value


def get_required_env(name: str) -> str:
    value = os.getenv(name)
    if value:
        return value
    raise RuntimeError(
        f'Missing required environment variable: {name}. '
        f'Set it in your shell or in a local .env file (not committed).'
    )
