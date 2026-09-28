import pytest

from hatua_ml.data.files import DataFileNotFoundError, require_file


def test_existing_file_returns_path(tmp_path):
    f = tmp_path / "x.dta"
    f.write_bytes(b"")
    assert require_file(str(f), "test file") == f


def test_missing_file_names_dataset_and_path(tmp_path):
    missing = tmp_path / "nope.dta"
    with pytest.raises(DataFileNotFoundError) as exc:
        require_file(missing, "Test survey")
    assert "Test survey not found" in str(exc.value)
    assert str(missing) in str(exc.value)


def test_is_still_a_file_not_found_error(tmp_path):
    with pytest.raises(FileNotFoundError):
        require_file(tmp_path / "nope.dta", "x")


def test_directory_is_rejected(tmp_path):
    with pytest.raises(DataFileNotFoundError):
        require_file(tmp_path, "x")