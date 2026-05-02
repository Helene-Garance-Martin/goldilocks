# ============================================================
# 🐻 GOLDILOCKS — Configuration Template
# ============================================================
# Copy this file to config_real.py and fill in your real values.
#
# ⚠️  config_real.py is gitignored — NEVER commit it!
# ✅  config_example.py is safe to commit — no real values here.
# ============================================================


# ------------------------------------------------------------
# SnapLogic API
# ------------------------------------------------------------
# Found in your SnapLogic Designer URL:
# https://emea.snaplogic.com/sl/designer/YOUR-ORG/YOUR-PROJECT

SNAPLOGIC_BASE_URL = "https://emea.snaplogic.com/api/1/rest/public/project/export"
SNAPLOGIC_ORG      = "your-org-name"
SNAPLOGIC_PROJECT  = "your-project/your-pipeline-name"
SNAPLOGIC_USERNAME = "your.email@yourorg.com"


# ------------------------------------------------------------
# Sensitive organisation names to anonymise
# ------------------------------------------------------------
# Add any org-specific names that appear in your pipeline exports

SENSITIVE_ORGS = [
    "YOUR_ORG_NAME",
    "YOUR_ORG_ALIAS",
    "your-org-slug",
]


# ------------------------------------------------------------
# Sensitive URL patterns to anonymise
# ------------------------------------------------------------

SENSITIVE_URL_PATTERNS = [
    r"https?://[a-zA-Z0-9._-]+\.snaplogic\.com[^\s\"']*",
    r"https?://[a-zA-Z0-9._-]+\.sharepoint\.com[^\s\"']*",
    r"https?://[a-zA-Z0-9._-]+\.azure[^\s\"']*",
    # Add any other internal URL patterns here
]


# ------------------------------------------------------------
# Credential field names to anonymise
# ------------------------------------------------------------

CREDENTIAL_KEYS = [
    "password", "token", "secret", "api_key", "apikey",
    "client_secret", "client_id", "bearer", "Authorization",
    "access_token", "refresh_token", "private_key",
    # Add any org-specific credential field names here
]


# ------------------------------------------------------------
# Neo4j Aura
# ------------------------------------------------------------
# Found in your Neo4j Aura console

NEO4J_URI      = "neo4j+s://xxxxxxxx.databases.neo4j.io"
NEO4J_USER     = "neo4j"
NEO4J_PASSWORD = "your-neo4j-password-here"


