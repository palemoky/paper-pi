from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("paper-pi")
except PackageNotFoundError:
    __version__ = "unknown"
