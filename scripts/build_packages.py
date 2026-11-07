#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Create the editor archive and optionally package the verified patched EXE."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
GAME_SHA256 = 'e5fd63f6efe57d13e00603ce994718ca49d38e83c94633ecfd4f7e46b524131c'
GAME_SIZE = 3825725
EDITOR_NAME = 'Evil_Islands_MP_Editor_Python.zip'
EXE_NAME = 'Evil_Islands_PvP_kody.zip'


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_zip(path: Path, entries: dict[str, bytes]) -> None:
    with zipfile.ZipFile(path, 'w') as archive:
        for name, data in sorted(entries.items()):
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    with zipfile.ZipFile(path) as archive:
        if archive.testzip() is not None:
            raise ValueError('ZIP verification failed: ' + str(path))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game-exe', type=Path, help='Already patched GAME.EXE with the documented SHA-256')
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'dist')
    args = parser.parse_args()
    game = None
    if args.game_exe is not None:
        game = args.game_exe.read_bytes()
        if len(game) != GAME_SIZE or sha256(game) != GAME_SHA256:
            parser.error('GAME.EXE does not match the verified patched build; no files were written.')

    files = [ROOT / name for name in (
        'editor.py', 'mp_core.py', 'Edytor_MP.pyw', 'URUCHOM.bat',
        'database.json', 'README.md', 'README.en.md', 'LICENSE.txt', 'NOTICE.md')]
    for directory in ('docs', 'examples', 'reference', 'tests', 'scripts'):
        files.extend(p for p in (ROOT / directory).rglob('*')
                     if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc', '.pyo'))
    entries = {'Evil_Islands_MP_Editor/' + p.relative_to(ROOT).as_posix(): p.read_bytes() for p in files}
    entries['Evil_Islands_MP_Editor/README_PL.txt'] = (
        'EVIL ISLANDS — EDYTOR POSTACI MP\n\n'
        '1. Zainstaluj Python 3.10+ z Tcl/Tk. Nie są potrzebne pakiety pip.\n'
        '2. Wypakuj cały folder i uruchom URUCHOM.bat lub Edytor_MP.pyw.\n'
        '3. Otwórz postać .mp i zapisuj zmiany jako nową kopię.\n\n'
        'Pełna obsługa: docs/EDITOR.md. Licencja kodu: LICENSE.txt.\n'
        'GAME.EXE jest osobną paczką do pobrania z repozytorium.\n'
    ).encode('utf-8-sig')

    args.output_dir.mkdir(parents=True, exist_ok=True)
    editor_zip = args.output_dir / EDITOR_NAME
    write_zip(editor_zip, entries)
    sums = [(sha256(editor_zip.read_bytes()), EDITOR_NAME)]
    if game is not None:
        exe_zip = args.output_dir / EXE_NAME
        write_zip(exe_zip, {
            'GAME.EXE': game,
            'Instrukcja.txt': (ROOT / 'docs/GAME_EXE_README.txt').read_bytes(),
            'SHA256_GAME.txt': (GAME_SHA256 + '  GAME.EXE\n').encode('ascii'),
        })
        sums.extend([(sha256(exe_zip.read_bytes()), EXE_NAME), (GAME_SHA256, 'GAME.EXE')])
    (args.output_dir / 'SHA256SUMS.txt').write_text(
        ''.join(digest + '  ' + name + '\n' for digest, name in sums), encoding='ascii')
    for digest, name in sums:
        print(digest, name)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
