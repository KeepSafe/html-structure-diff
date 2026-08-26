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


def _git_status(repo):
    completed = subprocess.run(
        ['git', 'status', '--porcelain'],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _validate_oracle(oracle, revision):
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


@contextmanager
def _prepared_oracle(target, revision, bootstrap_python):
    _remove_oracle(target)
    print(f'Creating fresh Mistune oracle at {ORACLE_DIR}', flush=True)
    try:
        subprocess.run(
            ['git', 'worktree', 'add', '--detach', str(ORACLE_DIR), revision],
            cwd=target,
            check=True,
        )
        subprocess.run(
            ['make', '-C', str(ORACLE_DIR), 'env', f'BOOTSTRAP_PYTHON={bootstrap_python}'],
            check=True,
        )
        _validate_oracle(ORACLE_DIR, revision)
        yield ORACLE_DIR
    finally:
        _remove_oracle(target)
        print(f'Removed temporary Mistune oracle {ORACLE_DIR}', flush=True)


def _write_golden_fixtures(path, oracle_report, oracle_revision, cases, corpus):
    if oracle_report['environment']['mistune'] != '0.8.4':
        raise ValueError('Golden fixtures may only be generated from Mistune 0.8.4')
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
    reporter = target / 'scripts/mistune_compat_reporter.py'
    corpus = json.loads(args.corpus.read_text(encoding='utf-8'))
    cases = expand_cases(args.corpus, target)

    with _prepared_oracle(
        target,
        args.oracle_revision,
        args.bootstrap_python,
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

        if oracle_report['environment']['mistune'] != '0.8.4':
            raise RuntimeError(
                'Oracle environment must use Mistune 0.8.4; found '
                f'{oracle_report["environment"]["mistune"]}'
            )

        if args.write_golden_fixtures:
            _write_golden_fixtures(
                args.write_golden_fixtures,
                oracle_report,
                _git_revision(prepared_oracle),
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
