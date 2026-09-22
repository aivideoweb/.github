#!/usr/bin/env python3
"""Refresh the profile language switcher and check cross-language structure."""
from pathlib import Path
from urllib.parse import quote, urlsplit, unquote
import re
import sys
import json
from datetime import date

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
        if filename in ('README_ar.md', 'README_th.md'):
            code = 'ar' if filename == 'README_ar.md' else 'th'
            state = 'active' if filename == current else 'idle'
            badge = f'https://raw.githubusercontent.com/aivideoweb/.github/main/profile/assets/badges/nav-{code}-{state}.svg'
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

# Manifest contract: routes[canonical_route][locale] = {url, status, lang}.
# A verified fallback additionally needs exception={approved: true, reason: "..."}.
# Only commercial claims require digits: account allowances, commissions, payout.
# Other prose and prompts may spell numbers out. Row/cell and paragraph order
# define semantic correspondence; allowance values retain their source order.
HTML_LANG = {
    'en': 'en', 'cn': 'zh-CN', 'tw': 'zh-TW', 'ja': 'ja', 'pt': 'pt',
    'es': 'es', 'de': 'de', 'ru': 'ru', 'fr': 'fr', 'ko': 'ko',
    'th': 'th', 'vi': 'vi', 'ar': 'ar', 'id': 'id', 'it': 'it',
}
URL_RE = re.compile(r'https://[^\s)"<>]+')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def product_route(url):
    parsed = urlsplit(url)
    require(parsed.scheme == 'https' and parsed.netloc == 'videoweb.ai',
            f'not an official product URL: {url}')
    parts = parsed.path.split('/')
    if len(parts) > 1 and parts[1] in HTML_LANG:
        parts.pop(1)
    return '/'.join(parts) or '/'


def normalize_url(url, locale, manifest):
    parsed = urlsplit(url)
    if parsed.netloc != 'videoweb.ai':
        return url  # Resource deep links must match, including fragments.
    route = product_route(url)
    record = manifest.get('routes', {}).get(route, {}).get(locale)
    require(isinstance(record, dict), f'{locale} {route}: missing manifest verification')
    require(record.get('status') == 200 and record.get('url') == url,
            f'{locale} {route}: URL/status differs from verified manifest: {url}')
    exception = record.get('exception', {})
    approved = (isinstance(exception, dict) and exception.get('approved') is True
                and isinstance(exception.get('reason'), str)
                and bool(exception['reason'].strip()))
    expected_path = route if locale == 'en' else '/' + locale + route
    require(isinstance(record.get('lang'), str) and bool(record['lang'].strip()),
            f'{locale} {route}: missing verified HTML language')
    expected_lang = HTML_LANG[locale].lower()
    actual_lang = record['lang'].lower()
    chinese_languages = {
        'cn': {'cn', 'zh-cn', 'zh-hans', 'zh-hans-cn'},
        'tw': {'tw', 'zh-tw', 'zh-hant', 'zh-hant-tw'},
    }
    language_ok = (actual_lang in chinese_languages[locale] if locale in chinese_languages
                   else actual_lang == expected_lang or actual_lang.startswith(expected_lang + '-'))
    require(approved or (parsed.path == expected_path and language_ok),
            f'{locale} {route}: wrong locale prefix/HTML language; explicit exception required')
    return route + ('?' + parsed.query if parsed.query else '') + ('#' + parsed.fragment if parsed.fragment else '')


def links(text, locale, manifest):
    return [normalize_url(u, locale, manifest) for u in URL_RE.findall(text)
            if not any(x in u for x in ('img.shields.io/', 'raw.githubusercontent.com/aivideoweb/.github/main/profile/assets/',
                                        '/.github/blob/main/profile/README'))]


def numbers(text):
    # Strip URL paths (versions/assets are not prose claims) before tokenizing.
    text = URL_RE.sub('', text)
    text = re.sub(r'(?<=\d)\s+(?=%)', '', text)
    return re.findall(r'(?<![\d.])\d+(?:[.,]\d+)*(?:%|[pPKk])?(?!\d)', text)


def commercial_values(source, actual):
    """Select rules using English context, never translated wording or URL digits."""
    plain = URL_RE.sub('', source).lower()
    if re.search(r'new[- ]users?', plain) and 'credits' in plain:
        return numbers(source), numbers(actual)  # ordered new-user/check-in/daily allowances
    if 'payout' in plain and re.search(r'us\$|usd|dollars', plain):
        return numbers(source), numbers(actual)
    if re.fullmatch(r'\s*\d+(?:[.,]\d+)?\s*%\s*', plain.replace('**', '')):
        return numbers(source), numbers(actual)  # each commission table cell independently
    return None


def semantic_items(text):
    """Stable section/table/row/cell or section/paragraph addresses, not URL sets."""
    text = re.sub(START + r'.*?' + END, '', text, flags=re.S)
    text = re.sub(r'```[^\n]*\n.*?```', '', text, flags=re.S)
    items, section, table, row, paragraph = {}, 0, 0, 0, 0
    pending = []
    in_table = False

    def flush():
        nonlocal paragraph
        if pending:
            paragraph += 1
            items[f's{section}/p{paragraph}'] = ' '.join(pending)
            pending.clear()

    for line in text.splitlines():
        if line.startswith('## '):
            flush()
            section += 1
            table = row = paragraph = 0
            in_table = False
        elif line.startswith('#') or re.fullmatch(r'\s*(?:<[^>]+>\s*)+', line):
            flush()
        elif line.startswith('|'):
            flush()
            if not in_table:
                table += 1
                row = 0
            in_table = True
            if re.match(r'^\|\s*:?-', line):
                continue
            for column, cell in enumerate(line.strip().strip('|').split('|')):
                items[f's{section}/t{table}/r{row}/c{column}'] = cell.strip()
            row += 1
        elif not line.strip():
            flush()
            in_table = False
        elif re.match(r'^\s*(?:\d+\.|-)\s+', line):
            flush()
            pending.append(line)
            flush()
        else:
            pending.append(line)
    flush()
    return items


def validate_assets(text, root, name):
    tags = re.findall(r'<img\b[^>]*>', text)
    require(any(re.search(r'width=[\"\']160[\"\']', t) and
                re.search(r'height=[\"\']160[\"\']', t) for t in tags),
            f'{name}: missing 160x160 logo')
    prefix = 'https://raw.githubusercontent.com/aivideoweb/.github/main/profile/'
    assets = [u for u in URL_RE.findall(text) if u.startswith(prefix)]
    require(bool(assets), f'{name}: missing profile assets')
    for url in assets:
        path = (root / 'profile' / unquote(urlsplit(url).path.split('/profile/', 1)[1])).resolve()
        require(path.is_relative_to((root / 'profile').resolve()) and path.is_file(),
                f'{name}: missing/invalid local asset {url}')
    for tag in tags:
        if '160' in tag:
            src = re.search(r'src=[\"\']([^\"\']+)', tag)
            require(src is not None and src[1] in assets,
                    f'{name}: logo must reference an existing profile asset')


def validate_document(text, english, locale, manifest, name):
    require(len(re.findall(r'^## ', text, re.M)) == 7, f'{name}: expected 7 H2 sections')
    require(len(re.findall(r'^\|\s*---', text, re.M)) == 7, f'{name}: expected 7 tables')
    prompts = re.findall(r'^```[^\n]*\n(.*?)^```\s*$', text, re.M | re.S)
    require(len(prompts) == 1 and bool(prompts[0].strip()), f'{name}: prompt must be nonempty')
    source, translated = semantic_items(english), semantic_items(text)
    require(source.keys() == translated.keys(), f'{name}: semantic structure differs from English')
    for key, expected in source.items():
        actual = translated[key]
        require(links(expected, 'en', manifest) == links(actual, locale, manifest),
                f'{name} {key}: link destinations/order differ')
        commercial = commercial_values(expected, actual)
        if commercial is not None:
            require(commercial[0] == commercial[1],
                    f'{name} {key}: complete commercial numeric values differ: '
                    f'{commercial[0]} != {commercial[1]}')
    model_cells = [k for k in translated if k.startswith('s3/t1/')]
    expected_model_cells = [f's3/t1/r{row}/c{column}'
                            for row in range(10) for column in range(3)]
    require(model_cells == expected_model_cells,
            f'{name}: model table requires 3 columns and 9 data rows')


def check(root=ROOT):
    manifest = json.loads((root / 'docs/product-locales.json').read_text())
    date.fromisoformat(manifest['checked_at'])
    english = (root / 'profile/README.md').read_text()
    for locale, _, name in LANGUAGES:
        p = root / 'profile' / name
        require(p.is_file(), f'{name}: missing')
        s = p.read_text()
        require(navigation(name) in s, f'{name}: incomplete language navigation')
        require('<!-- LANGUAGE_NAV -->' not in s and '{{' not in s, f'{name}: leftover placeholder')
        validate_document(s, english, locale, manifest, name)
        validate_assets(s, root, name)
        if name not in ('README.md', 'README_zh.md'):
            for key in ('free-tools', 'models', 'start', 'projects', 'partners'):
                require(f'<a id="{key}"></a>' in s and f'](#user-content-{key})' in s,
                        f'{name}: broken section link {key}')
        print(f'PASS {name}')
    print('PASS 15 languages: semantic links, verified locales, numeric values, prompts, assets')


if __name__ == '__main__':
    if '--write' in sys.argv:
        refresh()
    else:
        try:
            check()
        except (ValueError, KeyError, FileNotFoundError) as error:
            sys.exit(f'FAIL {error}')
