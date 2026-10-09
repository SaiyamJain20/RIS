"""Check declared positive/negative schema verdicts without executing providers."""
import argparse
import json
from pathlib import Path

from jsonschema import ValidationError

from evaluation.schema import validate


def check(paths):
    result = {'scope': 'schema fixtures only; no provider execution', 'files': [], 'mismatches': []}
    for path in paths:
        document = json.loads(Path(path).read_text()); cases = document['cases']
        positive = sum(case['valid'] is True for case in cases)
        negative = sum(case['valid'] is False for case in cases)
        if not positive or not negative or positive + negative != len(cases):
            raise ValueError('Each fixture pack needs positive and negative boolean verdicts')
        for i, case in enumerate(cases):
            try: validate(case['schema'], case['input']); actual = True
            except (ValueError, ValidationError): actual = False
            if actual != case['valid']:
                result['mismatches'].append({'file': str(path), 'index': i, 'schema': case['schema'],
                                             'label': case.get('label'), 'expected': case['valid'], 'actual': actual})
        result['files'].append({'path': str(path), 'cases': len(cases), 'valid': positive, 'invalid': negative})
    result['ok'] = bool(result['files']) and not result['mismatches']
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('fixtures', type=Path, nargs='+'); parser.add_argument('--output', type=Path)
    args = parser.parse_args(); result = check(args.fixtures); rendered = json.dumps(result, indent=2) + '\n'
    if args.output: args.output.write_text(rendered)
    print(rendered, end=''); return 0 if result['ok'] else 1


if __name__ == '__main__': raise SystemExit(main())
