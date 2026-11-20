"""Repository wrapper for the portable catalog CLI."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/blender-python-modeling/scripts'))
from knowledge_catalog import main, validate_catalog, load_catalog, search
if __name__ == '__main__': main()
