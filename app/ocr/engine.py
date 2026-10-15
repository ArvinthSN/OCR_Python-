from abc import ABC, abstractmethod
from typing import Optional, Any
import numpy as np
from app.models.ocr import OCRResult

class OCREngine(ABC):
    @abstractmethod
    def recognize(self,
                  image: np.ndarray,
                  profile: str = "default",
                  allowlist: Optional[str] = None,
                  blocklist: Optional[str] = None,
                  **kwargs: Any) -> OCRResult:
        """
        Executes OCR on an image and returns a structured OCRResult.
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Returns True if the engine models and dependencies are loaded."""
        pass
