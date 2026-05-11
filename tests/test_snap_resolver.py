# ============================================================
# 🫧 GOLDILOCKS — Snap Resolver Tests
# ============================================================
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest
from snap_resolver import resolve_snap_type, get_icon, SNAP_ICONS

# ------------------------------------------------------------
# resolve_snap_type tests
# ------------------------------------------------------------

class TestResolveSnapType:
    """Tests for snap type classification from class_id"""

    def test_httpclient(self):
        assert resolve_snap_type("com-snaplogic-snaps-apisuite-httpclient") == "httpclient"

    def test_script(self):
        assert resolve_snap_type("com-snaplogic-snaps-script-script") == "script"

    def test_pipeexec(self):
        assert resolve_snap_type("com-snaplogic-snaps-flow-pipeexec") == "pipeexec"

    def test_sftp_get_directorybrowser(self):
        assert resolve_snap_type("com-snaplogic-snaps-binary-directorybrowser") == "sftp_get"

    def test_sftp_get_simpleread(self):
        assert resolve_snap_type("com-snaplogic-snaps-binary-simpleread") == "sftp_get"

    def test_mapper_binarytodocument(self):
        assert resolve_snap_type("com-snaplogic-snaps-transform-binarytodocument") == "mapper"

    def test_mapper(self):
        assert resolve_snap_type("com-snaplogic-snaps-transform-mapper") == "mapper"

    def test_filter(self):
        assert resolve_snap_type("com-snaplogic-snaps-flow-filter") == "filter"

    def test_unknown_defaults(self):
        assert resolve_snap_type("com-snaplogic-snaps-unknown-whatever") == "default"

    def test_case_insensitive(self):
        assert resolve_snap_type("COM-SNAPLOGIC-SNAPS-APISUITE-HTTPCLIENT") == "httpclient"


# ------------------------------------------------------------
# get_icon tests
# ------------------------------------------------------------

class TestGetIcon:
    """Tests for snap type icon labels"""

class TestGetIcon:
    """Tests for snap type icon labels"""

    def test_httpclient_icon(self):
        assert get_icon("httpclient") == "🌐"

    def test_script_icon(self):
        assert get_icon("script") == "📜"

    def test_mapper_icon(self):
        assert get_icon("mapper") == "🗺️"

    def test_unknown_gets_default_icon(self):
        assert get_icon("unknown_type") == "⚙️"
    
    def test_dynamodb(self):
        assert resolve_snap_type("com-snaplogic-snaps-dynamodb-scan") == "dynamodb"

    def test_router(self):
        assert resolve_snap_type("com-snaplogic-snaps-flow-router") == "router"

    def test_union(self):
        assert resolve_snap_type("com-snaplogic-snaps-flow-union") == "union"

    def test_copy(self):
        assert resolve_snap_type("com-snaplogic-snaps-flow-copy") == "copy"

    def test_jsonsplitter(self):
        assert resolve_snap_type("com-snaplogic-snaps-transform-jsonsplitter") == "jsonsplitter"

    def test_datatransform(self):
        assert resolve_snap_type("com-snaplogic-snaps-transform-datatransform") == "datatransform"