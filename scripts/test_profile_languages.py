"""Run: python3 -B -m unittest discover -s scripts -p 'test_profile_languages.py'."""
import copy
from pathlib import Path
import tempfile
import unittest

import profile_languages as checker


def fixture():
    sections = []
    for i in range(1, 8):
        content = []
        if i == 1:
            content = ['- [tool](https://videoweb.ai/text-to-video/)',
                       '- [tool](https://videoweb.ai/image-to-video/)',
                       '- [tool](https://videoweb.ai/text-to-video/)',
                       '- [tool](https://videoweb.ai/image-to-video/)']
        elif i == 2:
            for j in range(3):
                content.append(f'#### Free generator {j}\n\nUse it for a scene.\n\nConditions: free.')
            content += ['### Auxiliary tools', '| Tool | Result |', '| --- | --- |',
                        '| [tool](https://videoweb.ai/text-to-video/) | 480p |',
                        '| [tool](https://videoweb.ai/image-to-video/) | Image |',
                        '', 'New users: 40 credits.']
        elif i == 3:
            for j, route in enumerate(checker.MODEL_ROUTES):
                if j in (0, 5, 8):
                    content.append(f'### Category {j}')
                content.append(f'#### [Model {j}](https://videoweb.ai{route}) — capability')
                content.extend(['Goal: a scene.', 'Verify the mode: 480p.'])
            content = ['\n\n'.join(content)]
        elif i == 4:
            content = ['```text\nA blue cup.\n```']
        elif i == 5:
            for j in range(4):
                content.append(f'### Project {j}\n\nCover\n\nDescription\n\nBest for: creators.')
        elif i == 6:
            content = ['| Eligible order | Commission |', '| --- | --- |',
                       '| First | 20% |', '| Later | 10% |', '', 'Payout: 100 USD.']
        sections.append(f'## Section {i}\n\n' + '\n'.join(content))
    source = '\n\n'.join(sections)
    translated = source.replace('https://videoweb.ai/', 'https://videoweb.ai/cn/')
    manifest = {'checked_at': '2026-09-22', 'routes': {}}
    for route in ('/text-to-video/', '/image-to-video/', *checker.MODEL_ROUTES):
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
            self.validate(self.text.replace('#### [Model 8]', '### [Model 8]'))

    def test_heading_links_are_checked(self):
        changed = self.text.replace('/cn/model/seedance-2-5/', '/TEMP/').replace(
            '/cn/model/minimax-h3/', '/cn/model/seedance-2-5/').replace('/TEMP/', '/cn/model/minimax-h3/')
        with self.assertRaisesRegex(ValueError, r's3/h3-1/h4-1/heading: link destinations/order'):
            self.validate(changed)

    def test_h4_paragraphs_have_separate_addresses(self):
        items = checker.semantic_items(self.text)
        self.assertIn('s3/h3-1/h4-1/p1', items)
        self.assertIn('s3/h3-1/h4-1/p2', items)
        self.assertIn('s3/h3-1/h4-2/p1', items)
        self.assertIn('s3/h3-1/h4-2/p2', items)

    def test_canonical_model_order_even_when_english_also_wrong(self):
        changed = self.source.replace('/model/seedance-2-5/', '/TEMP/').replace(
            '/model/minimax-h3/', '/model/seedance-2-5/').replace('/TEMP/', '/model/minimax-h3/')
        with self.assertRaisesRegex(ValueError, 'canonical route order'):
            checker.validate_document(changed, changed, 'en', self.manifest, 'English')

    def test_missing_h4_even_when_english_also_wrong(self):
        changed = self.source.replace('#### [Model 8]', '**Model** [Model 8]')
        with self.assertRaisesRegex(ValueError, '9 model H4'):
            checker.validate_document(changed, changed, 'en', self.manifest, 'English')

    def test_tables_must_remain_in_designated_sections(self):
        changed = self.source.replace('## Section 6', '## Section 7', 1)
        # Swap physical H2 sections: titles cannot determine semantic addresses.
        parts = changed.split('## Section ')
        parts[5], parts[6] = parts[6], parts[5]
        changed = '## Section '.join(parts)
        with self.assertRaisesRegex(ValueError, 'only auxiliary-tools table'):
            checker.validate_document(changed, changed, 'en', self.manifest, 'English')

    def test_navigation_is_one_paragraph_with_all_languages(self):
        for _, _, filename in checker.LANGUAGES:
            nav = checker.navigation(filename)
            body = nav.splitlines()[1:-1]
            self.assertEqual(len(body), 1)
            self.assertEqual(body[0].count('](' + checker.BASE), 15)
            self.assertNotIn('\n\n', nav)

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
