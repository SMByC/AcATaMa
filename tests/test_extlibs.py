import zipfile
from pathlib import Path

import pytest

from AcATaMa.utils import extlibs


def write_metadata(plugin_dir: Path, version: str) -> None:
    plugin_dir.mkdir(parents=True, exist_ok=True)
    plugin_dir.joinpath("metadata.txt").write_text(f"[general]\nversion={version}\n", encoding="utf-8")


def test_release_download_url_when_metadata_has_release_version(tmp_path):
    # Given: a plugin metadata file with a release tag
    plugin_dir = tmp_path / "AcATaMa"
    write_metadata(plugin_dir, "26.6")

    # When: the extlibs release URL is built
    url = extlibs.release_download_url(plugin_dir)

    # Then: the URL points to the matching GitHub release asset
    assert url == "https://github.com/SMByC/AcATaMa/releases/download/26.6/extlibs.zip"


def test_release_download_url_when_metadata_has_dev_version(tmp_path):
    # Given: a source checkout metadata file
    plugin_dir = tmp_path / "AcATaMa"
    write_metadata(plugin_dir, "dev")

    # When / Then: no GitHub release URL is built for the development version
    with pytest.raises(extlibs.DevelopmentVersionError):
        extlibs.release_download_url(plugin_dir)


def test_extlibs_paths_when_local_and_profile_paths_exist(tmp_path):
    # Given: local and QGIS-profile extlibs directories
    plugin_dir = tmp_path / "source" / "AcATaMa"
    settings_dir = tmp_path / "profile"
    local_extlibs = plugin_dir / "extlibs"
    profile_extlibs = settings_dir / "python" / "plugins" / "AcATaMa" / "extlibs"
    local_extlibs.mkdir(parents=True)
    profile_extlibs.mkdir(parents=True)

    # When: existing extlibs paths are resolved
    paths = extlibs.existing_extlibs_paths(plugin_dir, settings_dir)

    # Then: both supported dependency locations are returned
    assert paths == (local_extlibs, profile_extlibs)


def test_safe_extract_when_zip_contains_path_traversal(tmp_path):
    # Given: an extlibs archive with a member that escapes the install directory
    archive_path = tmp_path / "extlibs.zip"
    destination = tmp_path / "extlibs"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("../escape.py", "bad")

    # When / Then: extraction is rejected before any file can escape
    with pytest.raises(extlibs.UnsafeArchiveError):
        extlibs.safe_extract(archive_path, destination)

    assert not tmp_path.joinpath("escape.py").exists()


def test_safe_extract_when_zip_contains_flat_dependency(tmp_path):
    # Given: an extlibs archive with package directories at archive root
    archive_path = tmp_path / "extlibs.zip"
    destination = tmp_path / "extlibs"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("dask/__init__.py", "def delayed(func): return func\n")

    # When: the archive is extracted
    extlibs.safe_extract(archive_path, destination)

    # Then: package files land directly inside the extlibs install directory
    assert destination.joinpath("dask", "__init__.py").is_file()


def test_safe_extract_when_archive_is_invalid(tmp_path):
    # Given: a corrupt extlibs archive
    archive_path = tmp_path / "extlibs.zip"
    destination = tmp_path / "extlibs"
    archive_path.write_bytes(b"not a zip")

    # When / Then: extraction fails as a handled extlibs archive error
    with pytest.raises(extlibs.ArchiveError):
        extlibs.safe_extract(archive_path, destination)


def test_ensure_extlibs_when_install_makes_dask_available(monkeypatch, tmp_path):
    # Given: Dask is initially unavailable and becomes available after install
    plugin_dir = tmp_path / "AcATaMa"
    settings_dir = tmp_path / "profile"
    install_calls = []
    availability = [False, True]
    monkeypatch.setattr(extlibs, "add_existing_extlibs_paths", lambda _plugin_dir, _settings_dir: None)
    monkeypatch.setattr(extlibs, "dask_dependencies_available", lambda: availability.pop(0))

    def install_extlibs(installed_plugin_dir, installed_settings_dir):
        install_calls.append((installed_plugin_dir, installed_settings_dir))
        return tmp_path / "installed"

    monkeypatch.setattr(extlibs, "install", install_extlibs)

    # When: extlibs are ensured
    extlibs.ensure_extlibs(plugin_dir, settings_dir)

    # Then: the installer runs once for the requested plugin/profile pair
    assert install_calls == [(plugin_dir, settings_dir)]


def test_ensure_extlibs_when_install_does_not_make_dask_available(monkeypatch, tmp_path):
    # Given: Dask remains unavailable after install
    plugin_dir = tmp_path / "AcATaMa"
    settings_dir = tmp_path / "profile"
    monkeypatch.setattr(extlibs, "add_existing_extlibs_paths", lambda _plugin_dir, _settings_dir: None)
    monkeypatch.setattr(extlibs, "dask_dependencies_available", lambda: False)
    monkeypatch.setattr(extlibs, "install", lambda _plugin_dir, _settings_dir: tmp_path / "installed")

    # When / Then: the failure is reported as a handled dependency error
    with pytest.raises(extlibs.DependencyUnavailableError):
        extlibs.ensure_extlibs(plugin_dir, settings_dir)


def test_install_shows_progress_while_downloading_and_extracting(monkeypatch, tmp_path):
    # Given: a release install with dialog helpers replaced by recorders
    plugin_dir = tmp_path / "AcATaMa"
    settings_dir = tmp_path / "profile"
    write_metadata(plugin_dir, "26.6")
    events = []
    monkeypatch.setattr(extlibs, "show_install_progress", lambda: "dialog")
    monkeypatch.setattr(
        extlibs,
        "set_install_progress_message",
        lambda dialog, message: events.append((dialog, message)),
    )
    monkeypatch.setattr(extlibs, "close_install_progress", lambda dialog: events.append((dialog, "closed")))
    monkeypatch.setattr(extlibs, "download_extlibs", lambda url, archive_path: archive_path.write_bytes(b"zip"))
    monkeypatch.setattr(extlibs, "safe_extract", lambda archive_path, destination: destination.mkdir(parents=True))

    # When: the external libraries are installed
    extlibs.install(plugin_dir, settings_dir)

    # Then: the user sees both long-running phases and the dialog closes
    assert events == [
        ("dialog", "Downloading AcATaMa external libraries..."),
        ("dialog", "Extracting AcATaMa external libraries..."),
        ("dialog", "closed"),
    ]
