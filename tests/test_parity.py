import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CREDIT = 'Made with /hiring-panel by Alex Chen (@nocodealex) · chen.media'

class ParityTest(unittest.TestCase):
    def test_all_review_instructions_match(self):
        upstream = (ROOT / 'reference/upstream/SKILL.md').read_text()
        codex = (ROOT / '.agents/skills/hiring-panel/SKILL.md').read_text()
        expected = upstream[upstream.index('## 1.'):]
        expected = expected.replace(CREDIT, '__CREDIT__').replace('/hiring-panel', '$hiring-panel').replace('__CREDIT__', CREDIT)
        self.assertEqual(codex[codex.index('## 1.'):], expected)

    def test_license_preserved(self):
        self.assertEqual((ROOT/'LICENSE').read_bytes(), (ROOT/'.agents/skills/hiring-panel/LICENSE').read_bytes())
        self.assertIn('Copyright (c) 2026 Alex Chen', (ROOT/'LICENSE').read_text())

    def test_install_repeat_and_refuse_overwrite(self):
        spec = importlib.util.spec_from_file_location('installer', ROOT/'scripts/install.py')
        installer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(installer)
        with tempfile.TemporaryDirectory() as directory:
            target, status = installer.install(directory)
            self.assertEqual(status, 'installed')
            self.assertEqual(installer.install(directory)[1], 'already installed')
            (target/'SKILL.md').write_text('user modified skill')
            with self.assertRaisesRegex(RuntimeError, 'no files changed'):
                installer.install(directory)
            self.assertEqual((target/'SKILL.md').read_text(), 'user modified skill')

if __name__ == '__main__':
    unittest.main()
