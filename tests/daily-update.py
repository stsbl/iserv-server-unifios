#!/usr/bin/env python3
"""Exercise the daily updater without touching Docker or systemd."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class DailyUpdateTest(unittest.TestCase):
    def run_update(self, image="old", fail=""):
        with tempfile.TemporaryDirectory() as directory:
            tmp = Path(directory)
            stub = tmp / "command"
            stub.write_text('''#!/bin/sh
printf '%s\\n' "$*" >> "$LOG"
case "$*" in
  'compose pull --quiet') [ "$FAIL" != pull ] ;;
  'inspect --format {{.Image}} unifi-os-server')
    [ "$FAIL" != inspect ] || exit 1
    echo old ;;
  'inspect --format {{.Config.Image}} unifi-os-server') echo example:latest ;;
  'image inspect --format {{.Id}} example:latest') echo "$IMAGE" ;;
esac
''')
            stub.chmod(0o755)
            script = (ROOT / "cron/daily.d/server-unifios-update").read_text()
            script = script.replace("cd /usr/share/iserv/server-unifios/docker/unifi-os-server", "cd " + directory)
            script = script.replace(". /var/lib/iserv/server-unifios/docker-compose.env", ":")
            for command in ("/usr/bin/docker", "/bin/systemctl", "/usr/lib/iserv/server-unifios/server-unifios-rotate-psk"):
                script = script.replace(command, str(stub) + (" rotate-psk" if command.endswith("rotate-psk") else ""))
            result = subprocess.run(["sh", "-c", script], env={**os.environ, "LOG": str(tmp / "log"), "IMAGE": image, "FAIL": fail}, capture_output=True)
            return result.returncode, (tmp / "log").read_text().splitlines()

    def test_unchanged_image_preserves_container(self):
        code, calls = self.run_update()
        self.assertEqual(code, 0)
        self.assertNotIn("restart iserv-server-unifios.service", calls)
        self.assertIn("rotate-psk", calls)

    def test_changed_image_restarts_service(self):
        code, calls = self.run_update(image="new")
        self.assertEqual(code, 0)
        self.assertEqual(calls.count("restart iserv-server-unifios.service"), 1)
        self.assertIn("rotate-psk", calls)

    def test_failed_pull_or_inspection_leaves_service_alone(self):
        for failure in ("pull", "inspect"):
            with self.subTest(failure=failure):
                code, calls = self.run_update(fail=failure)
                self.assertNotEqual(code, 0)
                self.assertNotIn("restart iserv-server-unifios.service", calls)


if __name__ == "__main__":
    unittest.main()
