#!/usr/bin/env python3
"""Emit deterministic sdiff behavior signatures for one Python environment."""

import argparse
import importlib.metadata
import json
import sys
from pathlib import Path

from mistune_compat_signatures import run_case


def _load_sdiff(repo: Path):
    sys.path.insert(0, str(repo))
    import mistune
    import sdiff
    from sdiff import parser
    from sdiff.renderer import HtmlRenderer, TextRenderer

    return mistune, sdiff, parser, HtmlRenderer, TextRenderer


def _run_isolated_cases(cases, sdiff, parser, HtmlRenderer, TextRenderer):
    """Keep the Mistune 0.8 Zendesk class-rule leak outside corpus cases.

    The target intentionally fixes that process-global mutation and covers it
    with a target-only regression.  Resetting the oracle class list here makes
    every differential corpus case represent an independent public API call.
    """
    default_rules = list(sdiff.MdParser.default_rules)
    results = {}
    for case in cases:
        sdiff.MdParser.default_rules[:] = default_rules
        try:
            results[case['name']] = run_case(
                case,
                sdiff,
                parser,
                HtmlRenderer,
                TextRenderer,
            )
        finally:
            sdiff.MdParser.default_rules[:] = default_rules
    return results


def main():
    argument_parser = argparse.ArgumentParser()
    argument_parser.add_argument('--repo', type=Path, required=True)
    argument_parser.add_argument('--cases', type=Path, required=True)
    args = argument_parser.parse_args()

    repo = args.repo.resolve()
    mistune, sdiff, parser, HtmlRenderer, TextRenderer = _load_sdiff(repo)
    cases = json.loads(args.cases.read_text(encoding='utf-8'))
    results = _run_isolated_cases(cases, sdiff, parser, HtmlRenderer, TextRenderer)
    report = {
        'environment': {
            'python': '.'.join(map(str, sys.version_info[:3])),
            'sdiff': importlib.metadata.version('sdiff'),
            'mistune': importlib.metadata.version('mistune'),
        },
        'cases': results,
    }
    json.dump(report, sys.stdout, ensure_ascii=False, indent=2, sort_keys=True)
    sys.stdout.write('\n')


if __name__ == '__main__':
    main()
