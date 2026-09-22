"""Phase 1 benchmarkとfixtureの宣言を検証する。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]


def load_yaml(path: Path) -> dict:
    with path.open(encoding='utf-8') as stream:
        value = yaml.safe_load(stream)
    if not isinstance(value, dict):
        raise ValueError('YAMLの最上位はobjectである必要があります')
    return value


def validator(filename: str) -> Draft202012Validator:
    with (ROOT / 'schemas' / filename).open(encoding='utf-8') as stream:
        return Draft202012Validator(json.load(stream))


def messages(schema: Draft202012Validator, data: dict, path: Path) -> list[str]:
    return [f'{path.relative_to(ROOT)}: {error.message}' for error in schema.iter_errors(data)]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--check-fixtures', action='store_true')
    args = parser.parse_args()
    benchmark_schema = validator('benchmark.schema.json')
    fixture_schema = validator('fixture-manifest.schema.json')
    errors: list[str] = []
    checked_benchmarks = 0
    checked_fixtures: set[Path] = set()

    for family in ('generic', 'coding'):
        for path in sorted((ROOT / 'benchmarks' / family).glob('*.yaml')):
            if path.name == 'index.yaml':
                continue
            try:
                benchmark = load_yaml(path)
            except Exception as error:
                errors.append(f'{path.relative_to(ROOT)}: 読み込み失敗: {error}')
                continue
            errors.extend(messages(benchmark_schema, benchmark, path))
            checked_benchmarks += 1
            fixture_ref = benchmark.get('fixture', '')
            fixture_path = ROOT / 'fixtures' / fixture_ref / 'fixture.yaml'
            if not fixture_path.is_file():
                errors.append(f'{path.relative_to(ROOT)}: fixtureが見つかりません: {fixture_ref}')
                continue
            if args.check_fixtures and fixture_path not in checked_fixtures:
                checked_fixtures.add(fixture_path)
                try:
                    fixture = load_yaml(fixture_path)
                    errors.extend(messages(fixture_schema, fixture, fixture_path))
                    if fixture.get('id') != fixture_ref.rsplit('/', 1)[-1]:
                        errors.append(f'{fixture_path.relative_to(ROOT)}: fixture IDと参照名が一致しません')
                    if family == 'coding':
                        for name in ('workspace', 'verify'):
                            if not (fixture_path.parent / name).is_dir():
                                errors.append(f'{fixture_path.relative_to(ROOT)}: {name}/ がありません')
                except Exception as error:
                    errors.append(f'{fixture_path.relative_to(ROOT)}: 読み込み失敗: {error}')

    if errors:
        print('VALIDATION FAILED')
        print('\n'.join(f'- {error}' for error in errors))
        return 1
    print(f'VALIDATION OK: {checked_benchmarks} benchmarks, {len(checked_fixtures)} fixtures')
    return 0


if __name__ == '__main__':
    sys.exit(main())
