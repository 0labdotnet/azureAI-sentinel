"""Enable execution via `python -m src`.

Routes to configuration validation as the primary entry point.
"""

from src.config import validate_and_display

validate_and_display()
