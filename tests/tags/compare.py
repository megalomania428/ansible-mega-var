# ruff: noqa: INP001
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

# pylint: disable=import-error
import yaml  # type: ignore[reportMissingModuleSource]

# cspell:ignore keepends prefill

MEVA_TAGS_DIR = Path(__file__).resolve().parent
MEVA_TAGS_MODULE = re.compile(r'Query (meva-tags-[a-z-]+) getent entry')
MEVA_TAGS_PREFILL = 'meva-tags-prefill'
MEVA_TAGS_RESET = 'meva-tags-absent'
MEVA_TAGS_SINGLE = ('Hit the reference task', 'Save the result into')
MEVA_TAGS_ARGC = 3


def excess(left: list[str], right: list[str]) -> list[str]:
  return sorted((Counter(left) - Counter(right)).elements())


class MevaTagsMatrix:
  def __init__(self) -> None:
    with (MEVA_TAGS_DIR / 'vars.yaml').open(encoding='utf-8') as stream:
      matrix = yaml.safe_load(stream)
    with (MEVA_TAGS_DIR / 'play.yaml').open(encoding='utf-8') as stream:
      plays = yaml.safe_load(stream)
    self.forms: list[str] = sorted(i['meva_key'] for i in matrix['meva_getent'])
    self.prefill: list[str] = [i['meva_key'] for i in matrix['meva_getent_results']]
    self.places: list[str] = matrix['meva_tags_places']
    self.selectors: list[list[str]] = matrix['meva_tags_selectors']
    self.place_of_play: dict[str, str] = {
      p['name']: p['hosts']
      for p in plays
    }
    known = sorted(self.place_of_play.values())
    if len(self.place_of_play) != len(plays) or known != sorted(self.places):
      sys.exit('plays of play.yaml do not match meva_tags_places of vars.yaml')

  def write_selectors(self, path: Path) -> None:
    lines = ['\t'.join([str(n), *s]) + '\n' for n, s in enumerate(self.selectors)]
    path.write_text(''.join(lines), encoding='utf-8')


class MevaTagsPlace:
  def __init__(self) -> None:
    self.module: list[str] = []
    self.hits: list[str] = []
    self.final: list[str] | None = None


class MevaTagsRun:
  def __init__(self, matrix: MevaTagsMatrix, out: Path, number: int) -> None:
    self.matrix = matrix
    self.selector = matrix.selectors[number]
    self.places: dict[str, MevaTagsPlace] = {}
    self.errors: list[str] = []
    path = out / f'{number}.json'
    label = f"selector '{' '.join(self.selector)}'"
    if not path.is_file():
      self.errors.append(f'{label}: no output file {path}')
      return
    lines = path.read_text(encoding='utf-8').splitlines(keepends=True)
    start = next((n for n, line in enumerate(lines) if line.rstrip() == '{'), None)
    if start is None:
      self.errors.append(f'{label}: no JSON document in {path}')
      return
    try:
      for play in json.loads(''.join(lines[start:]))['plays']:
        self.add_play(play, label)
    except (KeyError, TypeError, ValueError) as error:
      self.errors.append(f'{label}: unexpected JSON in {path}: {error!r}')
      return
    for place in self.matrix.places:
      if place not in self.places:
        self.errors.append(f'{label}: no play of place {place} in {path}')

  def add_play(self, play: dict[str, Any], label: str) -> None:
    name = play['play']['name']
    place = self.matrix.place_of_play.get(name)
    if place is None or place in self.places:
      self.errors.append(f'{label}: unexpected or repeated play {name!r}')
      return
    data = self.places[place] = MevaTagsPlace()
    for task in play['tasks']:
      hosts: dict[str, Any] = task['hosts']
      task_name: str = task['task']['name']
      # callback prefixes the name with the role name or path and ' : '
      bare = task_name.rpartition(' : ')[2]
      strangers = sorted(set(hosts) - {place})
      if bare.startswith(MEVA_TAGS_SINGLE) and list(hosts) != [place]:
        got = f'results of hosts {sorted(hosts)} instead of exactly {place}'
        self.errors.append(f'place {place}, {label}: task {task_name!r} has {got}')
      elif strangers:
        got = f'results of other hosts {strangers}'
        self.errors.append(f'place {place}, {label}: task {task_name!r} has {got}')
      found = MEVA_TAGS_MODULE.fullmatch(bare)
      if found:
        data.module.append(found.group(1))
      result = hosts.get(place)
      if not result:
        continue
      facts = result.get('ansible_facts') or {}
      if 'meva_getent_results' in facts:
        data.final = [r['meva_key'] for r in facts['meva_getent_results']]
      msg = result.get('msg')
      skipped = result.get('skipped') is True
      is_hit = isinstance(msg, str) and msg.startswith('HIT ')
      if bare.startswith(MEVA_TAGS_SINGLE[0]) and not skipped and is_hit:
        data.hits.append(msg.removeprefix('HIT '))

  def compare(self) -> list[str]:
    problems: list[str] = []
    for place in self.matrix.places:
      data = self.places[place]
      label = f"place {place}, selector '{' '.join(self.selector)}', form"
      hits = sorted(data.hits)
      final = self.matrix.prefill if data.final is None else data.final
      records = sorted(k for k in final if k != MEVA_TAGS_PREFILL)
      reset = MEVA_TAGS_PREFILL not in final
      checks = [
        ('module task without reference', excess(data.module, hits)),
        ('reference without module task', excess(hits, data.module)),
        ('record without reference', excess(records, hits)),
        ('reference without record', excess(hits, records)),
      ]
      if not self.selector:
        missed = excess(self.matrix.forms, hits)
        beyond = excess(hits, self.matrix.forms)
        checks.extend([
          ('reference missed without selector', missed),
          ('reference beyond items without selector', beyond),
        ])
      for check, forms in checks:
        problems.extend(f'{label} {form}: {check}' for form in forms)
      if reset != (MEVA_TAGS_RESET in hits):
        got = f'reset {reset}, reference of reset {MEVA_TAGS_RESET in hits}'
        problems.append(f'{label} {MEVA_TAGS_RESET}: {got}')
    return problems


def check(out: Path) -> int:
  matrix = MevaTagsMatrix()
  problems: list[str] = []
  for number in range(len(matrix.selectors)):
    run = MevaTagsRun(matrix, out, number)
    problems.extend(run.errors or run.compare())
  pairs = len(matrix.places) * len(matrix.selectors)
  for problem in problems:
    sys.stderr.write(f'{problem}\n')
  if problems:
    sys.stderr.write(f'{len(problems)} problems in the tags matrix of {pairs} pairs\n')
    return 1
  sys.stdout.write(f'{pairs} pairs of the tags matrix match the reference\n')
  return 0


def main() -> int:
  if len(sys.argv) == MEVA_TAGS_ARGC and sys.argv[1] == 'selectors':
    MevaTagsMatrix().write_selectors(Path(sys.argv[2]))
    return 0
  if len(sys.argv) == MEVA_TAGS_ARGC and sys.argv[1] == 'check':
    return check(Path(sys.argv[2]))
  sys.stderr.write(f'usage: {sys.argv[0]} selectors <file> | check <directory>\n')
  return 2


if __name__ == '__main__':
  sys.exit(main())
