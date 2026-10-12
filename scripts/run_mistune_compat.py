#!/usr/bin/env python3
"""Compare exact sdiff signatures between the Mistune 0.8.4 oracle and target."""

import argparse
from contextlib import contextmanager
import difflib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

if __package__:
    from .mistune_compat_cases import SEED, expand_cases
    from .mistune_compat_signatures import canonical_hash
else:
    from mistune_compat_cases import SEED, expand_cases
    from mistune_compat_signatures import canonical_hash


ORACLE_DIR = Path('/tmp/html-structure-diff-mistune-084-oracle')
ORACLE_MISTUNE_VERSION = '0.8.4'
ORACLE_SDIFF_VERSION = '1.0.0'


def _run_report(python: Path, reporter: Path, repo: Path, cases: Path):
    completed = subprocess.run(
        [str(python), str(reporter), '--repo', str(repo), '--cases', str(cases)],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def _git_revision(repo):
    completed = subprocess.run(
        ['git', 'rev-parse', 'HEAD'],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _resolve_revision(repo, revision):
    completed = subprocess.run(
        ['git', 'rev-parse', '--verify', f'{revision}^{{commit}}'],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _git_status(repo):
    completed = subprocess.run(
        ['git', 'status', '--porcelain'],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _python_version(python):
    completed = subprocess.run(
        [str(python), '-c', 'import platform; print(platform.python_version())'],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _resolve_python(executable):
    candidate = Path(executable).expanduser()
    if candidate.is_absolute() or candidate.parent != Path('.'):
        resolved = candidate.absolute()
    else:
        discovered = shutil.which(executable)
        if discovered is None:
            raise RuntimeError(f'Bootstrap Python does not exist: {executable}')
        resolved = Path(discovered).absolute()
    if not resolved.is_file():
        raise RuntimeError(f'Bootstrap Python does not exist: {resolved}')
    return resolved


def _validate_oracle(oracle, revision, expected_python):
    python = oracle / 'venv/bin/python'
    if not python.is_file():
        raise RuntimeError(f'Temporary oracle has no Python executable: {python}')
    actual_revision = _git_revision(oracle)
    if actual_revision != revision:
        raise RuntimeError(
            f'Temporary oracle is at {actual_revision}, expected {revision}'
        )
    if _git_status(oracle):
        raise RuntimeError(f'Oracle worktree must be clean: {oracle}')
    actual_python = _python_version(python)
    if actual_python != expected_python:
        raise RuntimeError(
            f'Temporary oracle uses Python {actual_python}, expected {expected_python}'
        )


def _validate_report_environments(oracle_report, target_report, expected_python):
    expected_oracle = {
        'mistune': ORACLE_MISTUNE_VERSION,
        'python': expected_python,
        'sdiff': ORACLE_SDIFF_VERSION,
    }
    actual_oracle = oracle_report['environment']
    for key, expected in expected_oracle.items():
        actual = actual_oracle.get(key)
        if actual != expected:
            raise RuntimeError(
                f'Oracle environment {key} must be {expected}; found {actual}'
            )

    actual_target_python = target_report['environment'].get('python')
    if actual_target_python != expected_python:
        raise RuntimeError(
            f'Target environment must use Python {expected_python}; '
            f'found {actual_target_python}'
        )


def _remove_oracle(target):
    subprocess.run(
        ['git', 'worktree', 'remove', '--force', str(ORACLE_DIR)],
        cwd=target,
        check=False,
        capture_output=True,
        text=True,
    )
    if ORACLE_DIR.is_symlink() or ORACLE_DIR.is_file():
        ORACLE_DIR.unlink()
    elif ORACLE_DIR.is_dir():
        shutil.rmtree(ORACLE_DIR)
    subprocess.run(['git', 'worktree', 'prune'], cwd=target, check=True)


def _create_oracle_environment(oracle, bootstrap_python):
    subprocess.run(
        [str(bootstrap_python), '-m', 'venv', str(oracle / 'venv')],
        check=True,
    )
    oracle_python = oracle / 'venv/bin/python'
    subprocess.run(
        [
            str(oracle_python),
            '-m',
            'pip',
            'install',
            f'mistune=={ORACLE_MISTUNE_VERSION}',
        ],
        cwd=oracle,
        check=True,
    )
    subprocess.run(
        [str(oracle_python), '-m', 'pip', 'install', '--no-deps', '-e', '.'],
        cwd=oracle,
        check=True,
    )


@contextmanager
def _prepared_oracle(target, revision, bootstrap_python, expected_python):
    _remove_oracle(target)
    print(f'Creating fresh Mistune oracle at {ORACLE_DIR}', flush=True)
    try:
        subprocess.run(
            ['git', 'worktree', 'add', '--detach', str(ORACLE_DIR), revision],
            cwd=target,
            check=True,
        )
        _create_oracle_environment(ORACLE_DIR, bootstrap_python)
        _validate_oracle(ORACLE_DIR, revision, expected_python)
        yield ORACLE_DIR
    finally:
        _remove_oracle(target)
        print(f'Removed temporary Mistune oracle {ORACLE_DIR}', flush=True)


def _write_golden_fixtures(path, oracle_report, oracle_revision, cases, corpus):
    if oracle_report['environment']['mistune'] != ORACLE_MISTUNE_VERSION:
        raise ValueError(
            f'Golden fixtures may only be generated from Mistune '
            f'{ORACLE_MISTUNE_VERSION}'
        )
    oracle_environment = dict(oracle_report['environment'])
    oracle_environment['revision'] = oracle_revision
    manifest = {
        'schema_version': 1,
        'oracle': oracle_environment,
        'case_count': len(cases),
        'fuzz_seed': corpus.get('fuzz_seed', SEED),
        'expanded_cases_sha256': canonical_hash(cases),
        'cases': {
            name: canonical_hash(signature)
            for name, signature in sorted(oracle_report['cases'].items())
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def _format_diff(name, oracle_case, target_case):
    oracle = json.dumps(oracle_case, ensure_ascii=False, indent=2, sort_keys=True).splitlines()
    target = json.dumps(target_case, ensure_ascii=False, indent=2, sort_keys=True).splitlines()
    lines = difflib.unified_diff(
        oracle,
        target,
        fromfile=f'oracle/{name}.json',
        tofile=f'target/{name}.json',
        lineterm='',
    )
    return '\n'.join(lines)


def main():
    default_target = Path(__file__).resolve().parents[1]
    argument_parser = argparse.ArgumentParser()
    argument_parser.add_argument('--oracle-revision', required=True)
    argument_parser.add_argument('--bootstrap-python', default='python3.11')
    argument_parser.add_argument('--expected-python', required=True)
    argument_parser.add_argument('--target', type=Path, default=default_target)
    argument_parser.add_argument(
        '--corpus',
        type=Path,
        default=default_target / 'tests/fixtures/compatibility/mistune_cases.json',
    )
    argument_parser.add_argument('--report', type=Path)
    argument_parser.add_argument('--write-golden-fixtures', type=Path)
    args = argument_parser.parse_args()

    target = args.target.resolve()
    resolved_oracle_revision = _resolve_revision(target, args.oracle_revision)
    bootstrap_python = _resolve_python(args.bootstrap_python)
    bootstrap_version = _python_version(bootstrap_python)
    if bootstrap_version != args.expected_python:
        raise RuntimeError(
            f'Bootstrap Python is {bootstrap_version}, expected {args.expected_python}: '
            f'{bootstrap_python}'
        )
    reporter = target / 'scripts/mistune_compat_reporter.py'
    corpus = json.loads(args.corpus.read_text(encoding='utf-8'))
    cases = expand_cases(args.corpus, target)

    with _prepared_oracle(
        target,
        resolved_oracle_revision,
        bootstrap_python,
        args.expected_python,
    ) as prepared_oracle:
        with tempfile.TemporaryDirectory(prefix='sdiff-mistune-compat-') as temp_dir:
            expanded_cases = Path(temp_dir) / 'cases.json'
            expanded_cases.write_text(json.dumps(cases, ensure_ascii=False), encoding='utf-8')
            oracle_report = _run_report(
                prepared_oracle / 'venv/bin/python',
                reporter,
                prepared_oracle,
                expanded_cases,
            )
            target_report = _run_report(target / 'venv/bin/python', reporter, target, expanded_cases)

        _validate_oracle(
            prepared_oracle,
            resolved_oracle_revision,
            args.expected_python,
        )
        _validate_report_environments(
            oracle_report,
            target_report,
            args.expected_python,
        )

        if args.write_golden_fixtures:
            _write_golden_fixtures(
                args.write_golden_fixtures,
                oracle_report,
                resolved_oracle_revision,
                cases,
                corpus,
            )

    mismatches = []
    for name, oracle_case in oracle_report['cases'].items():
        target_case = target_report['cases'].get(name)
        if oracle_case != target_case:
            mismatches.append({
                'name': name,
                'diff': _format_diff(name, oracle_case, target_case),
            })

    result = {
        'oracle_environment': oracle_report['environment'],
        'target_environment': target_report['environment'],
        'fuzz_seed': corpus.get('fuzz_seed', SEED),
        'case_count': len(cases),
        'mismatch_count': len(mismatches),
        'mismatches': mismatches,
    }
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    print(
        f"Mistune {oracle_report['environment']['mistune']} oracle vs "
        f"{target_report['environment']['mistune']} target: "
        f"{len(cases)} cases, {len(mismatches)} mismatches"
    )
    for mismatch in mismatches[:10]:
        print(f"\n{mismatch['diff']}")
    if len(mismatches) > 10:
        print(f'\n{len(mismatches) - 10} additional mismatches omitted from stdout')
    return 1 if mismatches else 0


if __name__ == '__main__':
    sys.exit(main())
