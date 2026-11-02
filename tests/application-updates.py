#!/usr/bin/env python3
"""Check the real schedule policy against a simulated Core API."""
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
CODE = (ROOT / 'lib/server-unifios/server-unifios-application-updates').read_text().split("<<'PY'\n", 1)[1].rsplit('\nPY', 1)[0]

HARNESS = '''
import json
from urllib import request as urllib_request
apps = [
    {'name': 'network', 'isInstalled': True, 'updateSchedule': {'frequency': 'weekly', 'hour': 4, 'day': 1}},
    {'name': 'innerspace', 'isInstalled': True},
    {'name': 'protect', 'isInstalled': False},
]
class Response:
    def __init__(self, value): self.value = value
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def read(self): return json.dumps(self.value).encode() if self.value is not None else b''
def open_request(req, **kwargs):
    if req.full_url.endswith('/applications'):
        return Response(apps)
    if req.full_url == 'https://127.0.0.1/api/system':
        return Response({'firmware': {'autoUpdate': {'includeApplications': False}}})
    if req.full_url.endswith('/users'):
        return Response([{'role': 'admin', 'id': 'other'}, {'role': 'owner', 'id': 'owner'}])
    if req.full_url.endswith('/authToken'):
        assert json.loads(req.data) == {'userId': 'owner', 'expiresInSec': 60}
        return Response({'tokenCookieName': 'TOKEN', 'token': 'private', 'csrfToken': 'csrf'})
    assert req.full_url == 'https://127.0.0.1/api/system/updates/schedules'
    assert req.method == 'PATCH'
    assert req.get_header('Cookie') == 'TOKEN=private'
    assert req.get_header('X-csrf-token') == 'csrf'
    payload = json.loads(req.data)
    assert payload == {
        'useApplicationSchedules': True,
        'schedules': {'network': {'frequency': 'daily', 'hour': 4},
                      'innerspace': {'frequency': 'daily', 'hour': 2}},
    }, payload
    if VERIFY:
        for app in apps:
            if app['name'] in payload['schedules']:
                app['updateSchedule'] = payload['schedules'][app['name']]
    return Response(None)
urllib_request.urlopen = open_request
'''


class ApplicationUpdatesTest(unittest.TestCase):
    def test_installed_apps_receive_verified_daily_schedule_without_changing_hour(self):
        result = subprocess.run([sys.executable, '-c', 'VERIFY=True\n' + HARNESS + '\n' + CODE, '--repair'], capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(b'innerspace, network', result.stdout)
        self.assertNotIn(b'private', result.stdout + result.stderr)

    def test_check_reports_drift_without_changing_settings(self):
        harness = HARNESS.replace("    assert req.method == 'PATCH'", "    raise AssertionError('check must not change schedules')")
        result = subprocess.run([sys.executable, '-c', 'VERIFY=True\n' + harness + '\n' + CODE], capture_output=True)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertNotIn(b'check must not change schedules', result.stderr)

    def test_check_accepts_daily_schedules_without_changing_settings(self):
        setup = "\nfor app in apps:\n    if app.get('isInstalled'):\n        app['updateSchedule'] = {'frequency': 'daily', 'hour': 2}\n"
        harness = HARNESS.replace("    assert req.method == 'PATCH'", "    raise AssertionError('check must not change schedules')")
        result = subprocess.run([sys.executable, '-c', 'VERIFY=True\n' + harness + setup + '\n' + CODE], capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_check_rejects_schedules_overridden_by_firmware_updates(self):
        setup = "\nfor app in apps:\n    if app.get('isInstalled'):\n        app['updateSchedule'] = {'frequency': 'daily', 'hour': 2}\n"
        harness = HARNESS.replace("'includeApplications': False", "'includeApplications': True")
        harness = harness.replace("    assert req.method == 'PATCH'", "    raise AssertionError('check must not change schedules')")
        result = subprocess.run([sys.executable, '-c', 'VERIFY=True\n' + harness + setup + '\n' + CODE], capture_output=True)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertNotIn(b'check must not change schedules', result.stderr)

    def test_failed_verification_is_reported(self):
        result = subprocess.run([sys.executable, '-c', 'VERIFY=False\n' + HARNESS + '\n' + CODE, '--repair'], capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b'verification failed', result.stderr)


if __name__ == '__main__':
    unittest.main()
