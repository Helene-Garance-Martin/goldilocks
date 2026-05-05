# ============================================================
# 🐻 GOLDILOCKS — Pipeline Fetcher Tests
# ============================================================
# Tests for goldilocks_pipeline_fetcher.py
#
# Uses pytest + unittest.mock so tests never need
# real credentials or a real SnapLogic connection.
#
# Run with:
#   pytest test_pipeline_fetcher.py -v
# ============================================================

import pytest
import zipfile
import io
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

# ------------------------------------------------------------
# Import the lambdas and function we want to test
# ------------------------------------------------------------
# We test each lambda individually — small functions,
# small tests. One thing at a time!

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from pipeline_fetcher import (
    is_success,
    is_zip,
    decode_file,
    fetch_and_save,
)


# ============================================================
# LAMBDA TESTS
# ============================================================
# Lambdas are so small that each test is just one assertion.
# Think of it as: "given this input, I expect this output"

class TestIsSuccess:
    """Tests for the is_success lambda — checks status code 200"""

    def test_200_is_success(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        assert is_success(mock_response) is True

    def test_401_is_not_success(self):
        mock_response = MagicMock()
        mock_response.status_code = 401
        assert is_success(mock_response) is False

    def test_404_is_not_success(self):
        mock_response = MagicMock()
        mock_response.status_code = 404
        assert is_success(mock_response) is False

    def test_500_is_not_success(self):
        mock_response = MagicMock()
        mock_response.status_code = 500
        assert is_success(mock_response) is False


class TestIsZip:
    """Tests for the is_zip lambda — checks Content-Type header"""

    def test_application_zip_is_zip(self):
        mock_response = MagicMock()
        mock_response.headers = {"Content-Type": "application/zip"}
        assert is_zip(mock_response) is True

    def test_json_is_not_zip(self):
        mock_response = MagicMock()
        mock_response.headers = {"Content-Type": "application/json"}
        assert is_zip(mock_response) is False

    def test_missing_content_type_is_not_zip(self):
        mock_response = MagicMock()
        mock_response.headers = {}
        assert is_zip(mock_response) is False


class TestDecodeFile:
    """Tests for the decode_file lambda — reads and decodes a file from a zip"""

    def test_decodes_file_correctly(self):
        # Build a real in-memory zip with a test file inside
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as zf:
            zf.writestr("export.json", '{"pipeline": "test"}')
        buffer.seek(0)

        z = zipfile.ZipFile(buffer)
        result = decode_file(z, "export.json")
        assert result == '{"pipeline": "test"}'

    def test_decodes_multiple_files(self):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as zf:
            zf.writestr("export.json", '{"pipeline": "test"}')
            zf.writestr("accounts_template.json", '{"account": "template"}')
        buffer.seek(0)

        z = zipfile.ZipFile(buffer)
        assert decode_file(z, "export.json") == '{"pipeline": "test"}'
        assert decode_file(z, "accounts_template.json") == '{"account": "template"}'


# ============================================================
# INTEGRATION TEST — fetch_and_save()
# ============================================================
# Here we mock the entire requests.get call so no real
# HTTP request is ever made. We control exactly what
# the "API" returns and check our function handles it right.

def make_mock_zip(files: dict) -> bytes:
    """
    Helper — builds a fake zip in memory.
    files = {"filename": "content", ...}
    """
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as zf:
        for filename, content in files.items():
            zf.writestr(filename, content)
    return buffer.getvalue()


class TestFetchAndSave:
    """Integration tests for the full fetch_and_save() function"""

    @patch("pipeline_fetcher.requests.get")
    def test_saves_files_on_success(self, mock_get, tmp_path):
        """Happy path — API returns a valid zip, files get saved"""

        # Build a fake zip response
        fake_zip = make_mock_zip({
            "export.json": '{"pipeline": "DIESE-Business-Continuity"}',
            "accounts_template.json": '{"account": "template"}'
        })

        # Make requests.get return our fake response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/zip"}
        mock_response.content = fake_zip
        mock_get.return_value = mock_response

        # Run the function with fake credentials and tmp folder
        fetch_and_save(
            url="https://emea.snaplogic.com/api/1/rest/public/project/export/rbo-dev/DIESE",
            username="test_user",
            password="test_pass",
            output_dir=tmp_path
        )

        # Check files were actually saved
        assert (tmp_path / "export.json").exists()
        assert (tmp_path / "accounts_template.json").exists()

    @patch("pipeline_fetcher.requests.get")
    def test_saves_correct_content(self, mock_get, tmp_path):
        """Check the file content is saved correctly, not just the filename"""

        fake_zip = make_mock_zip({
            "export.json": '{"pipeline": "DIESE-Business-Continuity"}'
        })

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/zip"}
        mock_response.content = fake_zip
        mock_get.return_value = mock_response

        fetch_and_save(
            url="https://emea.snaplogic.com/api/1/rest/public/project/export/rbo-dev/DIESE/DIESE-Business%20Continuity",
            username="test_user",
            password="test_pass",
            output_dir=tmp_path

        )

        saved = (tmp_path / "export.json").read_text()
        assert '"pipeline"' in saved
        assert "DIESE-Business-Continuity" in saved

    @patch("pipeline_fetcher.requests.get")
    def test_handles_401_gracefully(self, mock_get, tmp_path):
        """Bad credentials — should not save any files"""

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.text = "Unauthorized"
        mock_get.return_value = mock_response

        fetch_and_save(
            url="https://emea.snaplogic.com/api/1/rest/public/project/export/rbo-dev/DIESE/DIESE-Business%20Continuity",
            username="test_user",
            password="test_pass",
            output_dir=tmp_path

        )

        # No files should have been saved
        assert list(tmp_path.iterdir()) == []

    @patch("pipeline_fetcher.requests.get")
    def test_handles_non_zip_response(self, mock_get, tmp_path):
        """API returns JSON instead of zip — should not save any files"""

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.content = b'{"error": "unexpected format"}'
        mock_get.return_value = mock_response

        fetch_and_save(
            url="https://emea.snaplogic.com/api/1/rest/public/project/export/rbo-dev/DIESE/DIESE-Business%20Continuity",
            username="test_user",
            password="test_pass",
            output_dir=tmp_path

        )

        assert list(tmp_path.iterdir()) == []
