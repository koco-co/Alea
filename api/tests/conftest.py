"""Safe test-only deployment defaults for modules that intentionally fail closed."""

import os


os.environ.setdefault("SUPABASE_URL", "https://test-project.supabase.co")
os.environ.setdefault("SUPABASE_JWT_ISSUER", "https://test-project.supabase.co/auth/v1")
os.environ.setdefault("ALEA_TERMS_VERSION", "terms-test-v1")
os.environ.setdefault("ALEA_PRIVACY_VERSION", "privacy-test-v1")
os.environ.setdefault("ALEA_RISK_VERSION", "risk-test-v1")
