from pathlib import Path
from jupiter.config import load_config

root = Path("C:/Dev_VSCode/Jupiter-project")
config = load_config(root)

print(f"Security Config: {config.security}")
print(f"Tokens: {config.security.tokens}")
print(f"Has tokens? {bool(config.security.tokens)}")
