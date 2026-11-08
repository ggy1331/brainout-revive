"""Add the QSZ-92 strings to localization/input.json (idempotent).

make_data.py reads input.json in the Windows default code page, so every
non-ASCII character is written as a \\uXXXX escape (json.dumps default).
RU/UA/BE get the Russian text, every other language the English one.
"""
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[2]
FILE = ROOT / 'data/packages/base/localization/input.json'
LANGS = ['EN', 'CS', 'NL', 'DE', 'IT', 'KO', 'PL', 'RO', 'RU', 'ZH', 'ES', 'TR', 'UA', 'FR', 'LT', 'HR', 'BE', 'HU', 'LV', 'SL', 'EL', 'SR', 'PT']
CYRILLIC = {'RU', 'UA', 'BE'}
NAMES = {
    'ITEM_WEAP_QSZ92': ('QSZ-92', 'QSZ-92'),
}


def block(key, ru, en):
    lines = ',\n'.join('        %s: %s' % (json.dumps(lang), json.dumps(ru if lang in CYRILLIC else en)) for lang in LANGS)
    return '    %s: {\n%s\n    }' % (json.dumps(key), lines)


def main():
    text = FILE.read_text(encoding='utf-8')
    for key in NAMES:  # drop a previous run
        text = re.sub(r',\n    %s: \{\n.*?\n    \}' % re.escape(json.dumps(key)), '', text, flags=re.S)
    body = text.rstrip()
    assert body.endswith('}')
    extra = ',\n'.join(block(k, *v) for k, v in NAMES.items())
    text = body[:-1].rstrip() + ',\n' + extra + '\n}'
    json.loads(text)
    FILE.write_text(text, encoding='utf-8', newline='')
    print('added', len(NAMES), 'strings')


if __name__ == '__main__':
    main()
