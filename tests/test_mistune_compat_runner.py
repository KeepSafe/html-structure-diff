import json
import subprocess
import sys
import tempfile
from contextlib import nullcontext
from io import StringIO
from pathlib import Path
from unittest import TestCase
from unittest.mock import call, patch

from scripts import run_mistune_compat


REPO_ROOT = Path(__file__).resolve().parents[1]
MISTUNE_ORACLE_REVISION = '12e7782208e4b458c8c4242882fda2377d9cba6b'


class TestMistuneCompatibilityRunner(TestCase):
    @staticmethod
    def _create_git_repo(path):
        subprocess.run(['git', 'init', '--quiet', str(path)], check=True)
        (path / 'README').write_text('test repository\n', encoding='utf-8')
        subprocess.run(['git', '-C', str(path), 'add', 'README'], check=True)
        subprocess.run(
            [
                'git',
                '-C',
                str(path),
                '-c',
                'user.name=Compatibility Test',
                '-c',
                'user.email=compatibility@example.test',
                'commit',
                '--quiet',
                '-m',
                'test fixture',
            ],
            check=True,
        )

    def test_command_helpers_decode_subprocess_results(self):
        completed = type('Completed', (), {'stdout': '{"value": 1}\n'})()
        with patch.object(
            run_mistune_compat.subprocess,
            'run',
            return_value=completed,
        ) as run:
            report = run_mistune_compat._run_report(
                Path('/python'),
                Path('/reporter'),
                Path('/repo'),
                Path('/cases'),
            )
            revision = run_mistune_compat._git_revision(Path('/repo'))
            status = run_mistune_compat._git_status(Path('/repo'))
            version = run_mistune_compat._python_version(Path('/python'))

        self.assertEqual({'value': 1}, report)
        self.assertEqual('{"value": 1}', revision)
        self.assertEqual('{"value": 1}', status)
        self.assertEqual('{"value": 1}', version)
        self.assertEqual(4, run.call_count)

    def test_revision_resolver_expands_an_abbreviated_commit(self):
        with tempfile.TemporaryDirectory(prefix='sdiff-revision-test-') as temp_dir:
            repo = Path(temp_dir)
            self._create_git_repo(repo)
            revision = run_mistune_compat._git_revision(repo)
            resolved = run_mistune_compat._resolve_revision(repo, revision[:12])
        self.assertEqual(revision, resolved)

    def test_remove_oracle_replaces_stale_state_and_tolerates_missing_state(self):
        with tempfile.TemporaryDirectory(prefix='sdiff-oracle-cleanup-test-') as temp_dir:
            repo = Path(temp_dir) / 'repo'
            repo.mkdir()
            self._create_git_repo(repo)
            oracle = Path(temp_dir) / 'mistune-oracle'
            oracle.mkdir()
            (oracle / 'stale').write_text('not a usable worktree', encoding='utf-8')

            with patch.object(run_mistune_compat, 'ORACLE_DIR', oracle):
                run_mistune_compat._remove_oracle(repo)
                self.assertFalse(oracle.exists())
                oracle.write_text('stale file', encoding='utf-8')
                run_mistune_compat._remove_oracle(repo)
                self.assertFalse(oracle.exists())
                run_mistune_compat._remove_oracle(repo)
                self.assertFalse(oracle.exists())

    def test_python_resolution_accepts_paths_and_path_commands(self):
        target_python = Path(sys.executable).absolute()
        self.assertEqual(
            target_python,
            run_mistune_compat._resolve_python(str(target_python)),
        )
        with patch.object(
            run_mistune_compat.shutil,
            'which',
            return_value=str(target_python),
        ):
            self.assertEqual(
                target_python,
                run_mistune_compat._resolve_python('python-for-test'),
            )
        with patch.object(run_mistune_compat.shutil, 'which', return_value=None):
            with self.assertRaisesRegex(RuntimeError, 'does not exist'):
                run_mistune_compat._resolve_python('missing-python-for-test')
        with self.assertRaisesRegex(RuntimeError, 'does not exist'):
            run_mistune_compat._resolve_python('/missing/python-for-test')

    def test_oracle_validation_rejects_each_invalid_state(self):
        with tempfile.TemporaryDirectory(prefix='sdiff-oracle-validate-test-') as temp_dir:
            oracle = Path(temp_dir)
            python = oracle / 'venv/bin/python'

            with self.assertRaisesRegex(RuntimeError, 'no Python executable'):
                run_mistune_compat._validate_oracle(oracle, 'revision', '3.11.13')

            python.parent.mkdir(parents=True)
            python.symlink_to(sys.executable)
            with (
                patch.object(run_mistune_compat, '_git_revision', return_value='revision'),
                patch.object(run_mistune_compat, '_git_status', return_value=''),
                patch.object(run_mistune_compat, '_python_version', return_value='3.11.13'),
            ):
                run_mistune_compat._validate_oracle(oracle, 'revision', '3.11.13')

            invalid_states = (
                ('other-revision', '', '3.11.13', 'expected revision'),
                ('revision', 'dirty', '3.11.13', 'must be clean'),
                ('revision', '', '3.11.9', 'uses Python 3.11.9'),
            )
            for revision, status, version, message in invalid_states:
                with self.subTest(message=message):
                    with (
                        patch.object(
                            run_mistune_compat,
                            '_git_revision',
                            return_value=revision,
                        ),
                        patch.object(
                            run_mistune_compat,
                            '_git_status',
                            return_value=status,
                        ),
                        patch.object(
                            run_mistune_compat,
                            '_python_version',
                            return_value=version,
                        ),
                    ):
                        with self.assertRaisesRegex(RuntimeError, message):
                            run_mistune_compat._validate_oracle(
                                oracle,
                                'revision',
                                '3.11.13',
                            )

    def test_runner_owns_oracle_environment_installation(self):
        oracle = Path('/tmp/oracle-for-test')
        bootstrap_python = Path('/target/venv/bin/python')
        oracle_python = oracle / 'venv/bin/python'
        with patch.object(run_mistune_compat.subprocess, 'run') as run:
            run_mistune_compat._create_oracle_environment(
                oracle,
                bootstrap_python,
            )
        self.assertEqual(
            [
                call(
                    [str(bootstrap_python), '-m', 'venv', str(oracle / 'venv')],
                    check=True,
                ),
                call(
                    [
                        str(oracle_python),
                        '-m',
                        'pip',
                        'install',
                        'mistune==0.8.4',
                    ],
                    cwd=oracle,
                    check=True,
                ),
                call(
                    [
                        str(oracle_python),
                        '-m',
                        'pip',
                        'install',
                        '--no-deps',
                        '-e',
                        '.',
                    ],
                    cwd=oracle,
                    check=True,
                ),
            ],
            run.call_args_list,
        )

    def test_prepared_oracle_always_starts_and_finishes_with_cleanup(self):
        target = Path('/target')
        revision = 'revision'
        bootstrap_python = Path('/python')
        with (
            patch.object(run_mistune_compat, '_remove_oracle') as remove,
            patch.object(run_mistune_compat, '_create_oracle_environment') as create,
            patch.object(run_mistune_compat, '_validate_oracle') as validate,
            patch.object(run_mistune_compat.subprocess, 'run') as run,
        ):
            with run_mistune_compat._prepared_oracle(
                target,
                revision,
                bootstrap_python,
                '3.11.13',
            ) as oracle:
                self.assertEqual(run_mistune_compat.ORACLE_DIR, oracle)

        self.assertEqual([call(target), call(target)], remove.call_args_list)
        run.assert_called_once_with(
            [
                'git',
                'worktree',
                'add',
                '--detach',
                str(run_mistune_compat.ORACLE_DIR),
                revision,
            ],
            cwd=target,
            check=True,
        )
        create.assert_called_once_with(
            run_mistune_compat.ORACLE_DIR,
            bootstrap_python,
        )
        validate.assert_called_once_with(
            run_mistune_compat.ORACLE_DIR,
            revision,
            '3.11.13',
        )

    def test_report_validation_requires_exact_oracle_provenance(self):
        oracle = {
            'environment': {
                'mistune': '0.8.4',
                'python': '3.11.13',
                'sdiff': '1.0.0',
            },
        }
        target = {
            'environment': {
                'mistune': '3.3.4',
                'python': '3.11.13',
                'sdiff': '2.0.0',
            },
        }
        run_mistune_compat._validate_report_environments(
            oracle,
            target,
            '3.11.13',
        )

        mismatches = (
            ('oracle', 'mistune', '3.3.4', 'mistune must be 0.8.4'),
            ('oracle', 'python', '3.11.9', 'python must be 3.11.13'),
            ('oracle', 'sdiff', '2.0.0', 'sdiff must be 1.0.0'),
            ('target', 'python', '3.11.9', 'must use Python 3.11.13'),
        )
        for report_name, field, value, message in mismatches:
            with self.subTest(report=report_name, field=field):
                invalid_oracle = json.loads(json.dumps(oracle))
                invalid_target = json.loads(json.dumps(target))
                report = invalid_oracle if report_name == 'oracle' else invalid_target
                report['environment'][field] = value
                with self.assertRaisesRegex(RuntimeError, message):
                    run_mistune_compat._validate_report_environments(
                        invalid_oracle,
                        invalid_target,
                        '3.11.13',
                    )

    def test_golden_fixture_writer_records_verified_oracle_metadata(self):
        report = {
            'environment': {
                'mistune': '0.8.4',
                'python': '3.11.13',
                'sdiff': '1.0.0',
            },
            'cases': {'case': {'value': 1}},
        }
        cases = [{'name': 'case'}]
        with tempfile.TemporaryDirectory(prefix='sdiff-golden-writer-test-') as temp_dir:
            fixture = Path(temp_dir) / 'nested/golden.json'
            run_mistune_compat._write_golden_fixtures(
                fixture,
                report,
                MISTUNE_ORACLE_REVISION,
                cases,
                {},
            )
            written = json.loads(fixture.read_text(encoding='utf-8'))

        self.assertEqual(MISTUNE_ORACLE_REVISION, written['oracle']['revision'])
        self.assertEqual(run_mistune_compat.SEED, written['fuzz_seed'])
        self.assertEqual(1, written['case_count'])
        self.assertEqual(
            run_mistune_compat.canonical_hash(report['cases']['case']),
            written['cases']['case'],
        )

        invalid_report = json.loads(json.dumps(report))
        invalid_report['environment']['mistune'] = '3.3.4'
        with self.assertRaisesRegex(ValueError, 'Mistune 0.8.4'):
            run_mistune_compat._write_golden_fixtures(
                Path('/unused'),
                invalid_report,
                MISTUNE_ORACLE_REVISION,
                cases,
                {},
            )

    def test_result_diff_is_labeled_and_readable(self):
        difference = run_mistune_compat._format_diff(
            'sample',
            {'value': 1},
            {'value': 2},
        )
        self.assertIn('--- oracle/sample.json', difference)
        self.assertIn('+++ target/sample.json', difference)
        self.assertIn('-  "value": 1', difference)
        self.assertIn('+  "value": 2', difference)

    def test_main_writes_report_and_returns_nonzero_for_mismatches(self):
        case_names = [f'case-{index}' for index in range(11)]
        cases = [{'name': name} for name in case_names]
        oracle_report = {
            'environment': {
                'mistune': '0.8.4',
                'python': '3.11.13',
                'sdiff': '1.0.0',
            },
            'cases': {name: {'value': 'oracle'} for name in case_names},
        }
        target_report = {
            'environment': {
                'mistune': '3.3.4',
                'python': '3.11.13',
                'sdiff': '2.0.0',
            },
            'cases': {name: {'value': 'target'} for name in case_names},
        }
        with tempfile.TemporaryDirectory(prefix='sdiff-runner-main-test-') as temp_dir:
            report_path = Path(temp_dir) / 'nested/report.json'
            fixture_path = Path(temp_dir) / 'golden.json'
            arguments = [
                'run_mistune_compat.py',
                '--oracle-revision',
                MISTUNE_ORACLE_REVISION,
                '--bootstrap-python',
                sys.executable,
                '--expected-python',
                '3.11.13',
                '--target',
                str(REPO_ROOT),
                '--corpus',
                str(REPO_ROOT / 'tests/fixtures/compatibility/mistune_cases.json'),
                '--report',
                str(report_path),
                '--write-golden-fixtures',
                str(fixture_path),
            ]
            with (
                patch.object(run_mistune_compat.sys, 'argv', arguments),
                patch.object(
                    run_mistune_compat,
                    '_resolve_revision',
                    return_value=MISTUNE_ORACLE_REVISION,
                ),
                patch.object(
                    run_mistune_compat,
                    '_resolve_python',
                    return_value=Path(sys.executable),
                ),
                patch.object(
                    run_mistune_compat,
                    '_python_version',
                    return_value='3.11.13',
                ),
                patch.object(run_mistune_compat, 'expand_cases', return_value=cases),
                patch.object(
                    run_mistune_compat,
                    '_prepared_oracle',
                    return_value=nullcontext(Path('/oracle')),
                ),
                patch.object(
                    run_mistune_compat,
                    '_run_report',
                    side_effect=[oracle_report, target_report],
                ),
                patch.object(run_mistune_compat, '_validate_oracle'),
                patch.object(run_mistune_compat, '_validate_report_environments'),
                patch.object(run_mistune_compat, '_write_golden_fixtures') as write,
                patch('sys.stdout', new_callable=StringIO) as stdout,
            ):
                result = run_mistune_compat.main()

            written_report = json.loads(report_path.read_text(encoding='utf-8'))

        self.assertEqual(1, result)
        self.assertEqual(11, written_report['mismatch_count'])
        self.assertEqual(11, len(written_report['mismatches']))
        self.assertIn('1 additional mismatches omitted', stdout.getvalue())
        write.assert_called_once()

    def test_main_rejects_wrong_bootstrap_python_version(self):
        arguments = [
            'run_mistune_compat.py',
            '--oracle-revision',
            MISTUNE_ORACLE_REVISION,
            '--bootstrap-python',
            sys.executable,
            '--expected-python',
            '3.11.13',
        ]
        with (
            patch.object(run_mistune_compat.sys, 'argv', arguments),
            patch.object(
                run_mistune_compat,
                '_resolve_revision',
                return_value=MISTUNE_ORACLE_REVISION,
            ),
            patch.object(
                run_mistune_compat,
                '_resolve_python',
                return_value=Path(sys.executable),
            ),
            patch.object(
                run_mistune_compat,
                '_python_version',
                return_value='3.11.9',
            ),
        ):
            with self.assertRaisesRegex(RuntimeError, '3.11.9, expected 3.11.13'):
                run_mistune_compat.main()
