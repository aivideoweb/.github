#!/usr/bin/env python3
"""Refresh the profile language switcher and check cross-language structure."""
from pathlib import Path
from urllib.parse import quote
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
LANGUAGES = [
    ('en', 'English', 'README.md'), ('ja', '日本語', 'README_ja.md'),
    ('pt', 'Português', 'README_pt.md'), ('es', 'Español', 'README_es.md'),
    ('de', 'Deutsch', 'README_de.md'), ('ru', 'Русский', 'README_ru.md'),
    ('fr', 'Français', 'README_fr.md'), ('cn', '简体中文', 'README_zh.md'),
    ('tw', '繁體中文', 'README_tw.md'), ('ko', '한국어', 'README_ko.md'),
    ('th', 'ไทย', 'README_th.md'), ('vi', 'Tiếng Việt', 'README_vi.md'),
    ('ar', 'العربية', 'README_ar.md'), ('id', 'Bahasa Indonesia', 'README_id.md'),
    ('it', 'Italiano', 'README_it.md'),
]
BASE = 'https://github.com/aivideoweb/.github/blob/main/profile/'
START, END = '<!-- LANGUAGE_NAV_START -->', '<!-- LANGUAGE_NAV_END -->'

def navigation(current):
    rows = []
    for _, label, filename in LANGUAGES:
        color = '647A30' if filename == current else '59636E'
        badge = 'https://img.shields.io/badge/' + quote(label, safe='') + '-' + color + '?style=flat-square'
        rows.append(f'[![{label}]({badge})]({BASE}{filename})')
    return START + '\n' + '\n\n'.join(' '.join(rows[i:i+5]) for i in range(0,15,5)) + '\n' + END

def refresh():
    for _, _, name in LANGUAGES:
        p = ROOT / 'profile' / name
        if not p.exists():
            continue
        s = p.read_text()
        nav = navigation(name)
        if START in s:
            s = re.sub(START + r'.*?' + END, lambda _: nav, s, flags=re.S)
        elif '<!-- LANGUAGE_NAV -->' in s:
            s = s.replace('<!-- LANGUAGE_NAV -->', nav)
        else:
            s, n = re.subn(r'^\[!\[English\].*$', lambda _: nav, s, count=1, flags=re.M)
            if not n:
                raise ValueError(f'{name}: language switcher marker missing')
        p.write_text(s)

def external_links(s):
    return {u for u in re.findall(r'https://[^\s)"<>]+',s)
            if 'img.shields.io/' not in u and '/.github/blob/main/profile/README' not in u}

def check():
    english = (ROOT/'profile/README.md').read_text()
    expected = external_links(english)
    for _, _, name in LANGUAGES:
        p = ROOT/'profile'/name
        assert p.is_file(), f'{name}: missing'
        s = p.read_text()
        assert navigation(name) in s, f'{name}: incomplete language navigation'
        assert len(re.findall(r'^## ',s,re.M)) == 7, f'{name}: missing section'
        assert len(re.findall(r'^\|\s*---',s,re.M)) == 7, f'{name}: missing table'
        assert s.count('```') == 2, f'{name}: missing prompt example'
        assert 'width="160" height="160"' in s, f'{name}: logo size changed'
        assert external_links(s) == expected, f'{name}: differing destinations {external_links(s)^expected}'
        normalized = re.sub(r'\s+', '', s)
        for claim in ['480p','2K','20%','10%','100','40','50']:
            assert claim in normalized, f'{name}: missing key value {claim}'
        assert s.count('raw.githubusercontent.com/aivideoweb/.github/main/profile/assets/') == 5, f'{name}: image mismatch'
        assert '<!-- LANGUAGE_NAV -->' not in s and '{{' not in s, f'{name}: leftover placeholder'
        if name not in ('README.md', 'README_zh.md'):
            for key in ('free-tools', 'models', 'start', 'projects', 'partners'):
                assert f'<a id="{key}"></a>' in s and f'](#user-content-{key})' in s, f'{name}: broken section link {key}'
        print(f'PASS {name}')
    print('PASS 15 languages: navigation, sections, tables, image paths, destinations, key values')

if __name__ == '__main__':
    if '--write' in sys.argv:
        refresh()
    else:
        check()
