import configparser
import importlib
import site
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import Final

PLUGIN_NAME: Final = "AcATaMa"
PLUGIN_REPOSITORY: Final = "https://github.com/SMByC/AcATaMa"
PLUGIN_DIR: Final = Path(__file__).resolve().parent.parent
METADATA_FILE: Final = "metadata.txt"
DEVELOPMENT_VERSION: Final = "dev"
EXTLIBS_ARCHIVE: Final = "extlibs.zip"


class ExtlibsError(Exception):
    pass


class MetadataError(ExtlibsError):
    pass


class DevelopmentVersionError(ExtlibsError):
    pass


class DownloadError(ExtlibsError):
    pass


class UnsafeArchiveError(ExtlibsError):
    pass


class ArchiveError(ExtlibsError):
    pass


class DependencyUnavailableError(ExtlibsError):
    pass


def metadata_version(plugin_dir: Path = PLUGIN_DIR) -> str:
    parser = configparser.ConfigParser()
    metadata_path = plugin_dir / METADATA_FILE
    read_files = parser.read(metadata_path, encoding="utf-8")
    if not read_files:
        raise MetadataError(f"Cannot read AcATaMa metadata file: {metadata_path}")
    if not parser.has_option("general", "version"):
        raise MetadataError(f"AcATaMa metadata has no version: {metadata_path}")
    return parser.get("general", "version").strip()


def release_download_url(plugin_dir: Path = PLUGIN_DIR) -> str:
    version = metadata_version(plugin_dir)
    if version == DEVELOPMENT_VERSION:
        raise DevelopmentVersionError("AcATaMa development metadata cannot target a GitHub release asset")
    return f"{PLUGIN_REPOSITORY}/releases/download/{version}/{EXTLIBS_ARCHIVE}"


def qgis_settings_dir() -> Path:
    from qgis.core import QgsApplication

    return Path(QgsApplication.qgisSettingsDirPath())


def profile_extlibs_path(settings_dir: Path | None = None) -> Path:
    profile_dir = qgis_settings_dir() if settings_dir is None else settings_dir
    return profile_dir / "python" / "plugins" / PLUGIN_NAME / "extlibs"


def local_extlibs_path(plugin_dir: Path = PLUGIN_DIR) -> Path:
    return plugin_dir / "extlibs"


def existing_extlibs_paths(plugin_dir: Path = PLUGIN_DIR, settings_dir: Path | None = None) -> tuple[Path, ...]:
    candidates = (local_extlibs_path(plugin_dir), profile_extlibs_path(settings_dir))
    existing_paths: list[Path] = []
    for path in candidates:
        if path.is_dir() and path not in existing_paths:
            existing_paths.append(path)
    return tuple(existing_paths)


def add_existing_extlibs_paths(plugin_dir: Path = PLUGIN_DIR, settings_dir: Path | None = None) -> None:
    for path in existing_extlibs_paths(plugin_dir, settings_dir):
        site.addsitedir(str(path))


def dask_dependencies_available() -> bool:
    try:
        dask = importlib.import_module("dask")
    except ImportError:
        return False
    return hasattr(dask, "compute") and hasattr(dask, "delayed")


def safe_extract(archive_path: Path, destination: Path) -> None:
    try:
        destination.mkdir(parents=True, exist_ok=True)
        destination_root = destination.resolve()
        with zipfile.ZipFile(archive_path) as archive:
            for member in archive.infolist():
                target_path = (destination / member.filename).resolve()
                try:
                    target_path.relative_to(destination_root)
                except ValueError as error:
                    raise UnsafeArchiveError(f"Unsafe path in {EXTLIBS_ARCHIVE}: {member.filename}") from error
            archive.extractall(destination)
    except zipfile.BadZipFile as error:
        raise ArchiveError(f"Invalid AcATaMa external libraries archive: {archive_path}") from error
    except OSError as error:
        raise ArchiveError(f"Cannot extract AcATaMa external libraries into {destination}") from error


def download_extlibs(url: str, archive_path: Path) -> None:
    try:
        urllib.request.urlretrieve(url, archive_path)
    except (urllib.error.ContentTooShortError, urllib.error.URLError, OSError) as error:
        raise DownloadError(f"Cannot download AcATaMa external libraries from {url}") from error


def show_install_progress():
    from qgis.PyQt.QtCore import Qt
    from qgis.PyQt.QtWidgets import QApplication, QProgressDialog

    progress = QProgressDialog("Downloading AcATaMa external libraries...", None, 0, 0)
    progress.setWindowTitle("AcATaMa - External libraries")
    progress.setWindowModality(Qt.WindowModality.WindowModal)
    progress.setCancelButton(None)
    progress.setMinimumDuration(0)
    progress.show()
    QApplication.processEvents()
    return progress


def set_install_progress_message(progress, message: str) -> None:
    from qgis.PyQt.QtWidgets import QApplication

    progress.setLabelText(message)
    QApplication.processEvents()


def close_install_progress(progress) -> None:
    from qgis.PyQt.QtWidgets import QApplication

    progress.close()
    QApplication.processEvents()


def install(plugin_dir: Path = PLUGIN_DIR, settings_dir: Path | None = None) -> Path:
    destination = profile_extlibs_path(settings_dir)
    url = release_download_url(plugin_dir)
    progress = show_install_progress()
    try:
        with tempfile.TemporaryDirectory(prefix="acatama-extlibs-") as temp_dir:
            archive_path = Path(temp_dir) / EXTLIBS_ARCHIVE
            set_install_progress_message(progress, "Downloading AcATaMa external libraries...")
            download_extlibs(url, archive_path)
            set_install_progress_message(progress, "Extracting AcATaMa external libraries...")
            safe_extract(archive_path, destination)
    finally:
        close_install_progress(progress)
    site.addsitedir(str(destination))
    return destination


def ensure_extlibs(plugin_dir: Path = PLUGIN_DIR, settings_dir: Path | None = None) -> None:
    add_existing_extlibs_paths(plugin_dir, settings_dir)
    if dask_dependencies_available():
        return
    install(plugin_dir, settings_dir)
    if not dask_dependencies_available():
        raise DependencyUnavailableError("AcATaMa external libraries were installed but Dask is still unavailable")


def show_install_error(error: ExtlibsError) -> None:
    from qgis.PyQt.QtWidgets import QMessageBox

    QMessageBox.warning(
        None,
        "AcATaMa - External libraries",
        "AcATaMa could not install its recommended external Python libraries automatically. "
        "Dask-based parallel raster pixel counting will be unavailable, but AcATaMa can continue "
        "using native or sequential counting methods. Install extlibs.zip manually to enable the faster "
        "parallel method.\n\n"
        f"Details: {error}",
    )
