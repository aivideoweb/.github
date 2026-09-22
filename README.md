# VideoWeb AI GitHub profile

[Live organization page](https://github.com/aivideoweb) · [English profile](profile/README.md) · [简体中文介绍](profile/README_zh.md)

GitHub displays `profile/README.md` on the organization overview. All 15 languages offered on the VideoWeb website have a complete profile edition:

[English](profile/README.md) · [日本語](profile/README_ja.md) · [Português](profile/README_pt.md) · [Español](profile/README_es.md) · [Deutsch](profile/README_de.md) · [Русский](profile/README_ru.md) · [Français](profile/README_fr.md) · [简体中文](profile/README_zh.md) · [繁體中文](profile/README_tw.md) · [한국어](profile/README_ko.md) · [ไทย](profile/README_th.md) · [Tiếng Việt](profile/README_vi.md) · [العربية](profile/README_ar.md) · [Bahasa Indonesia](profile/README_id.md) · [Italiano](profile/README_it.md)

For source pages, image credits, and the review record, see [editorial notes](docs/editorial-notes.md).

To refresh language navigation, run `python3 scripts/profile_languages.py --write`. To check language coverage and content structure, run `python3 scripts/profile_languages.py`.

The product-link check uses [verified language routes](docs/product-locales.json), including the final URL and page language. Refresh this evidence when product paths change; a successful HTTP response alone is not proof of a translated product page.

Run `python3 -m unittest discover -s scripts -p 'test_*.py'` for regression checks against swapped links, changed numeric claims, and empty examples. Content checks do not replace a review of translation meaning or the rendered page.
