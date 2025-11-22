import os
import logging
from .base import EPDDriver
from .mock import MockEPDDriver
from .waveshare import WaveshareEPDDriver

logger = logging.getLogger(__name__)

def get_driver() -> EPDDriver:
    """
    根据环境变量获取 EPD 驱动实例
    
    环境变量:
    - MOCK_EPD: 如果为 "true"，强制使用 Mock 驱动
    - EPD_MODEL: Waveshare 驱动型号，默认为 "epd7in5_V2"
    """
    # 1. 检查是否强制使用 Mock
    is_mock = os.getenv("MOCK_EPD", "false").lower() == "true"
    if is_mock:
        logger.info("MOCK_EPD is true, using MockEPDDriver")
        return MockEPDDriver()

    # 2. 尝试加载 Waveshare 驱动
    epd_model = os.getenv("EPD_MODEL", "epd7in5_V2")
    try:
        logger.info(f"Attempting to load Waveshare driver: {epd_model}")
        return WaveshareEPDDriver(epd_model)
    except Exception as e:
        # 捕获所有异常（包括 ImportError, OSError, RuntimeError），因为在非 Pi 环境下 GPIO 初始化会失败
        logger.warning(f"Failed to load Waveshare driver '{epd_model}': {e}")
        logger.warning("Falling back to MockEPDDriver")
        return MockEPDDriver()
