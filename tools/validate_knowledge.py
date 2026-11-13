from pathlib import Path
from knowledge import validate_catalog
if __name__ == '__main__': print(validate_catalog(Path(__file__).resolve().parents[1]))
