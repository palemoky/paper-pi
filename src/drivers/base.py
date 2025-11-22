from typing import Protocol, runtime_checkable
from PIL import Image

@runtime_checkable
class EPDDriver(Protocol):
    width: int
    height: int

    def init(self) -> None:
        """Initialize the display"""
        ...

    def clear(self) -> None:
        """Clear the display"""
        ...

    def sleep(self) -> None:
        """Put the display to sleep"""
        ...

    def display(self, image: Image.Image) -> None:
        """Display a PIL Image"""
        ...
