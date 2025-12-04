"""Font management utility.

Handles on-demand font downloading to reduce Docker image size.
Fonts are stored in the root fonts/ directory and downloaded from GitHub when needed.
"""

import logging
import shutil
from pathlib import Path

import requests

from ..config import BASE_DIR

logger = logging.getLogger(__name__)


class FontManager:
    """Manages font files and downloads them on demand."""

    # GitHub repository info
    GITHUB_REPO = "palemoky/paper-pi"
    GITHUB_BRANCH = "main"

    # Font URLs - using GitHub raw URLs
    LXGW_WENKAI_URL = f"https://raw.githubusercontent.com/{GITHUB_REPO}/{GITHUB_BRANCH}/fonts/LXGWWenKai-Regular.ttf"
    WANGHANZONG_LISHU_URL = f"https://raw.githubusercontent.com/{GITHUB_REPO}/{GITHUB_BRANCH}/fonts/WangHanZong-Lishu.ttf"
    WAVESHARE_URL = (
        f"https://raw.githubusercontent.com/{GITHUB_REPO}/{GITHUB_BRANCH}/fonts/WaveShare.ttc"
    )

    # Fonts directory at project root
    FONTS_DIR = BASE_DIR / "fonts"

    @classmethod
    def get_font_path(cls, font_name: str, url: str | None = None, download: bool = True) -> str:
        """Get path to a font file, downloading it if necessary.

        Args:
            font_name: Name of the font file (e.g., "LXGWWenKai-Regular.ttf")
            url: URL to download the font from if missing. If None, no download is attempted.
            download: Whether to attempt downloading if font is missing. Default True.

        Returns:
            Absolute path to the font file.
        """
        cls.FONTS_DIR.mkdir(parents=True, exist_ok=True)
        font_path = cls.FONTS_DIR / font_name

        if font_path.exists():
            logger.debug(f"Font {font_name} found at {font_path}")
            return str(font_path)

        if download and url:
            logger.info(f"Font {font_name} not found. Downloading from {url}...")
            try:
                cls._download_file(url, font_path)
                logger.info(f"✅ Successfully downloaded {font_name}")
                return str(font_path)
            except Exception as e:
                logger.error(f"❌ Failed to download font {font_name}: {e}")
                # If download fails, return the path anyway (let caller handle missing file)
                pass
        else:
            logger.debug(f"Font {font_name} not found and download disabled")

        return str(font_path)

    @staticmethod
    def _download_file(url: str, target_path: Path):
        """Download a file from a URL to a target path."""
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()

        # Download to a temporary file first
        temp_path = target_path.with_suffix(".tmp")
        try:
            with open(temp_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            # Rename temp file to target file
            shutil.move(temp_path, target_path)
        except Exception:
            if temp_path.exists():
                temp_path.unlink()
            raise
