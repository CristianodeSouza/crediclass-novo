import os
import re
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.config import get_settings
from backend.consortium_viability_engine import MOTOR_VERSION
from backend.main import health


class ReleaseIdentityTest(unittest.TestCase):
    def test_backend_motor_and_cached_assets_share_one_version(self):
        root = Path(__file__).resolve().parents[1]
        html = (root / "backend" / "static" / "index.html").read_text(encoding="utf-8")
        release_values = [
            re.search(r'<meta name="crediclass-build" content="([^"]+)"', html).group(1),
            re.search(r"/static/css/style\.css\?v=([^\"]+)", html).group(1),
            re.search(r"/static/js/api\.js\?v=([^\"]+)", html).group(1),
            re.search(r"/static/js/app\.js\?v=([^\"]+)", html).group(1),
            get_settings().version,
            MOTOR_VERSION,
        ]
        self.assertEqual(len(set(release_values)), 1, release_values)

    def test_health_exposes_render_commit_for_build_traceability(self):
        with patch.dict(os.environ, {"RENDER_GIT_COMMIT": "abcdef1234567890"}, clear=True):
            payload = health()
        self.assertEqual(payload["commit"], "abcdef1234567890")
        self.assertEqual(payload["version"], get_settings().version)

    def test_health_does_not_invent_commit_when_provider_does_not_supply_one(self):
        with patch.dict(os.environ, {}, clear=True):
            payload = health()
        self.assertIsNone(payload["commit"])


if __name__ == "__main__":
    unittest.main()
