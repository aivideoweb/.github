"""Run: python3 -B -m unittest discover -s scripts -p 'test_profile_languages.py'."""
import copy
from pathlib import Path
import tempfile
import unittest

import profile_languages as checker


def fixture():
    sections = []
    for i in range(1, 8):
        count = 9 if i == 3 else 1
        rows = ['| task | where | verify |', '| --- | --- | --- |']
        for j in range(count):
            route = '/text-to-video/' if j == 0 else '/image-to-video/'
            rows.append(f'| task {j} | [tool](https://videoweb.ai{route}) | 480p |')
        sections.append(f'## Section {i}\n\n' + '\n'.join(rows))
    source = '\n\n'.join(sections)
    source += '\n\nNew users: 40 credits.\n\nPayout: 100 USD.\n\n```text\nA blue cup.\n```\n'
    translated = source.replace('https://videoweb.ai/', 'https://videoweb.ai/cn/')
    manifest = {'checked_at': '2026-09-22', 'routes': {}}
    for route in ('/text-to-video/', '/image-to-video/'):
        manifest['routes'][route] = {
            'en': {'url': 'https://videoweb.ai' + route, 'status': 200, 'lang': 'en'},
            'cn': {'url': 'https://videoweb.ai/cn' + route, 'status': 200, 'lang': 'zh-CN'},
        }
    return source, translated, manifest


class SemanticRegressionTests(unittest.TestCase):
    def setUp(self):
        self.source, self.text, self.manifest = fixture()

    def validate(self, text=None):
        checker.validate_document(self.text if text is None else text, self.source,
                                  'cn', self.manifest, 'README_zh.md')

    def test_valid_localized_document(self):
        self.validate()

    def test_swapped_links_rejected_even_with_identical_set(self):
        changed = self.text.replace('/cn/text-to-video/', '/TEMP/').replace(
            '/cn/image-to-video/', '/cn/text-to-video/').replace('/TEMP/', '/cn/image-to-video/')
        with self.assertRaisesRegex(ValueError, 'link destinations/order'):
            self.validate(changed)

    def test_complete_numeric_values(self):
        for before, after in [('40 credits', '400 credits'), ('100 USD', '1000 USD')]:
            with self.subTest(after=after), self.assertRaisesRegex(ValueError, 'numeric values'):
                self.validate(self.text.replace(before, after))

    def test_swapped_values_between_paragraphs_rejected(self):
        with self.assertRaisesRegex(ValueError, 'numeric values'):
            self.validate(self.text.replace('40 credits', '100 credits').replace('100 USD', '40 USD'))

    def test_empty_prompt_rejected(self):
        with self.assertRaisesRegex(ValueError, 'prompt must be nonempty'):
            self.validate(self.text.replace('A blue cup.', '  \n  '))

    def test_missing_duplicate_link_rejected(self):
        with self.assertRaisesRegex(ValueError, 'link destinations/order'):
            self.validate(self.text.replace('[tool](https://videoweb.ai/cn/text-to-video/)', 'tool', 1))

    def test_wrong_locale_even_if_manifest_url_matches(self):
        self.manifest['routes']['/text-to-video/']['cn']['url'] = 'https://videoweb.ai/text-to-video/'
        with self.assertRaisesRegex(ValueError, 'wrong locale'):
            self.validate(self.text.replace('/cn/text-to-video/', '/text-to-video/'))

    def test_explicit_fallback(self):
        rec = self.manifest['routes']['/text-to-video/']['cn']
        rec.update(url='https://videoweb.ai/text-to-video/', lang='en',
                   exception={'approved': True, 'reason': 'Verified localized route unavailable'})
        self.validate(self.text.replace('/cn/text-to-video/', '/text-to-video/'))
        rec['exception']['reason'] = ''
        with self.assertRaisesRegex(ValueError, 'wrong locale'):
            self.validate(self.text.replace('/cn/text-to-video/', '/text-to-video/'))

    def test_manifest_verification_required(self):
        for key, value in [('status', 404), ('lang', 'ja')]:
            manifest = copy.deepcopy(self.manifest)
            manifest['routes']['/text-to-video/']['cn'][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                checker.validate_document(self.text, self.source, 'cn', manifest, 'test')

    def test_resource_deep_link_preserved(self):
        url = 'https://github.com/aivideoweb/example/blob/main/README_ja.md#start'
        self.source += '\n[Resource](' + url + ')\n'
        self.text += '\n[Resource](' + url + ')\n'
        self.validate()
        with self.assertRaisesRegex(ValueError, 'link destinations/order'):
            self.validate(self.text.replace('#start', '#wrong'))

    def test_translated_anchor_is_not_a_paragraph(self):
        self.validate(self.text.replace('## Section 3', '<a id="models"></a>\n\n## Section 3'))

    def test_numbers_next_to_cjk_text(self):
        self.assertEqual(checker.numbers('新用户40积分，480p'), checker.numbers('40 credits, 480p'))
        self.assertNotEqual(checker.numbers('新用户400积分'), checker.numbers('40 credits'))

    def test_unverified_route(self):
        del self.manifest['routes']['/text-to-video/']['cn']
        with self.assertRaisesRegex(ValueError, 'missing manifest verification'):
            self.validate()

    def test_english_prefix_rejected(self):
        rec = self.manifest['routes']['/text-to-video/']['en']
        rec['url'] = 'https://videoweb.ai/en/text-to-video/'
        with self.assertRaisesRegex(ValueError, 'wrong locale'):
            checker.normalize_url(rec['url'], 'en', self.manifest)

    def test_percentage_spacing_and_cjk(self):
        self.assertEqual(checker.numbers('20 %'), checker.numbers('20%'))
        self.assertEqual(checker.numbers('20\u00a0%'), checker.numbers('20%'))
        self.assertEqual(checker.numbers('5초'), checker.numbers('5秒'))
        self.assertEqual(checker.commercial_values('20%', '20 %'), (['20%'], ['20%']))
        self.assertNotEqual(*checker.commercial_values('20%', '200 %'))

    def test_ordinary_prose_and_prompt_numbers_may_be_spelled_out(self):
        self.source += '\nA five-second scene.\n'
        self.text += '\n一段5秒的场景。\n'
        self.validate(self.text.replace('A blue cup.', '一段5秒的镜头。'))

    def test_model_numeric_wording_not_a_commercial_claim(self):
        self.validate(self.text.replace('480p', 'an image'))

    def test_allowance_values_keep_semantic_order(self):
        expected, actual = checker.commercial_values(
            '40 new-user credits, 20 daily check-in credits, 50 daily free-tool uses',
            '新用户20积分，每日签到40积分，每天50次')
        self.assertNotEqual(expected, actual)

    def test_actual_and_standard_chinese_html_languages(self):
        route = '/text-to-video/'
        for locale, accepted in {
            'cn': ('cn', 'zh-CN', 'zh-Hans', 'zh-Hans-CN'),
            'tw': ('tw', 'zh-TW', 'zh-Hant', 'zh-Hant-TW'),
        }.items():
            for lang in accepted:
                with self.subTest(locale=locale, lang=lang):
                    url = f'https://videoweb.ai/{locale}{route}'
                    self.manifest['routes'][route][locale] = {'url': url, 'status': 200, 'lang': lang}
                    self.assertEqual(checker.normalize_url(url, locale, self.manifest), route)
            self.manifest['routes'][route][locale]['lang'] = 'tw' if locale == 'cn' else 'cn'
            with self.assertRaisesRegex(ValueError, 'wrong locale'):
                checker.normalize_url(url, locale, self.manifest)

    def test_model_shape(self):
        with self.assertRaises(ValueError):
            self.validate(self.text.replace('| task 8 |', '| task 8 | extra |'))

    def test_asset_exists_and_logo_extension_not_fixed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            assets = root / 'profile/assets'
            assets.mkdir(parents=True)
            for extension in ('svg', 'png'):
                logo = assets / ('new-logo.' + extension)
                logo.write_text('fixture')
                html = ('<img src="https://raw.githubusercontent.com/aivideoweb/.github/main/profile/assets/'
                        + logo.name + '" width="160" height="160">')
                checker.validate_assets(html, root, 'test')
                logo.unlink()
                with self.assertRaisesRegex(ValueError, 'missing/invalid local asset'):
                    checker.validate_assets(html, root, 'test')


if __name__ == '__main__':
    unittest.main()
