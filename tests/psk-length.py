#!/usr/bin/env python3
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PskLengthTest(unittest.TestCase):
    def test_profile_length_does_not_leak_into_next_profile(self):
        with tempfile.TemporaryDirectory() as directory:
            tmp = Path(directory)
            profiles = tmp / 'profiles'
            profiles.mkdir()
            for name, setting in [('first', 'psk_length=8\n'), ('second', '')]:
                (profiles / (name + '.env')).write_text(
                    f'name={name}\nsite=default\nwlan_name=guest\napi_key=test\nrotate=true\n' + setting)
            wrapper = (ROOT / 'lib/server-unifios/server-unifios-rotate-psk').read_text()
            wrapper = wrapper.replace('/etc/iserv/server-unifios/psk-profiles.d', str(profiles))
            wrapper = wrapper.replace('/var/lib/iserv/server-unifios', str(tmp))
            wrapper = wrapper.replace('/usr/lib/iserv/server-unifios', str(tmp))
            (tmp / 'rotate_wlan_psk').write_text('#!/bin/sh\nprintf "%s" "$PSK_LENGTH" > "$PSK_STATE_FILE"\n')
            (tmp / 'rotate_wlan_psk').chmod(0o755)
            (tmp / 'psk-state').mkdir()
            result = subprocess.run(['sh', '-c', wrapper], capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((tmp / 'psk-state/first').read_text(), '8')
            self.assertEqual((tmp / 'psk-state/second').read_text(), '58')

    def rotate(self, length):
        with tempfile.TemporaryDirectory() as directory:
            tmp = Path(directory)
            shutil.copy(ROOT / 'lib/server-unifios/rotate_wlan_psk', tmp / 'rotate')
            for name, content in {
                'pwgen': '#!/usr/bin/env python3\nimport sys\nprint("a" * int(sys.argv[1]))\n',
                'set-psk': '#!/bin/sh\nprintf "%s" "$1" > "$SENT"\n',
                'render_wlan_psk': '#!/bin/sh\nexit 0\n',
            }.items():
                path = tmp / name
                path.write_text(content)
                path.chmod(0o755)
            env = {**os.environ, 'PATH': directory + ':' + os.environ['PATH'],
                   'SET_PSK_COMMAND': str(tmp / 'set-psk'), 'PSK_STATE_FILE': str(tmp / 'state'),
                   'SENT': str(tmp / 'sent')}
            env.pop('NEWPSK', None)
            env.pop('PSK_LENGTH', None)
            if length is not None:
                env['PSK_LENGTH'] = length
            result = subprocess.run(['bash', str(tmp / 'rotate')], env=env, capture_output=True)
            state = (tmp / 'state').read_text().strip() if (tmp / 'state').exists() else None
            return result.returncode, state, (tmp / 'sent').exists()

    def test_default_and_configured_lengths(self):
        for value, size in [(None, 58), ('8', 8), ('24', 24), ('63', 63)]:
            with self.subTest(value=value):
                code, state, sent = self.rotate(value)
                self.assertEqual(code, 0)
                self.assertEqual(len(state), size)
                self.assertTrue(sent)

    def test_invalid_lengths_do_not_change_controller_or_state(self):
        for value in ['7', '64', 'text', '-1', '8.5', '99999999999999999999999']:
            with self.subTest(value=value):
                code, state, sent = self.rotate(value)
                self.assertNotEqual(code, 0)
                self.assertIsNone(state)
                self.assertFalse(sent)


if __name__ == '__main__':
    unittest.main()
