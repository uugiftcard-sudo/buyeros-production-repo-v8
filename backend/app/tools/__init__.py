"""BuyerOS tools package.

This subpackage contains simple tool functions that perform specific
actions such as issuing refunds or running OCR.  Tools are registered
via the ``ToolRegistry`` and can be invoked by agents.
"""

from .refund import process_refund  # noqa: F401
from .ocr import extract_text  # noqa: F401
