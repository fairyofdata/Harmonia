"""Rules of harmonia/jp2hangul.py, the one part of Harmonia with an exact expected output.

    python -m unittest discover -s tests

Expectations here are the conventions written in jp2hangul's docstring. When a rule
is deliberately changed, change the case that pins it and leave the rest alone --
that is what this file is for.
"""
import re
import unittest

from harmonia.jp2hangul import (DEFAULT_STYLE, SMALL_V, SMALL_Y, SYLLABLE, ja_to_hangul,
                                kana_to_hangul)

KANA = re.compile(r'[ぁ-ゖァ-ヺー]')   # hiragana, katakana, 'ー'
HANGUL_OR_SPACE = re.compile(r'^[가-힣 ]*$')

# every combination of the four documented knobs (3 x 2 x 2 x 2)
ALL_STYLES = [{'tsu': tsu, 'initial': initial, 'long_vowel': long_vowel, 'n_assim': n_assim}
              for tsu in ('ㅊ', 'ㅅ', 'ㅉ')
              for initial in ('aspirated', 'plain')
              for long_vowel in ('drop', 'keep')
              for n_assim in (False, True)]


class AlwaysApplied(unittest.TestCase):
    """Rules that hold under every style."""

    def check(self, cases, style=None):
        for kana, expected in cases:
            with self.subTest(kana=kana):
                self.assertEqual(kana_to_hangul(kana, style), expected)

    def test_sokuon_becomes_final_s(self):
        self.check([('マッテル', '맛테루'),
                    ('イッショ', '잇쇼')])

    def test_leading_sokuon_is_dropped(self):
        self.assertEqual(kana_to_hangul('ッカ'), '카')   # nothing to attach the final to

    def test_n_becomes_final_n(self):
        self.check([('センセイ', '센세이'),
                    ('コンニチハ', '콘니치하')])

    def test_bare_n_gets_its_own_syllable(self):
        self.check([('ン', '은'),
                    ('ンン', '은은')])

    def test_su_zu_use_eu(self):
        self.check([('スズキ', '스즈키'),
                    ('ス', '스')])

    def test_fu_row(self):
        self.check([('フフ', '후후'),
                    ('ファイト', '파이토'),
                    ('フィフェフォ', '피페포')])

    def test_small_y_rows(self):
        self.check([('キャキュキョ', '캬큐쿄'),
                    ('シャシュショ', '샤슈쇼'),
                    ('チャチュチョ', '차추초'),
                    ('ジャジュジョ', '자주조')])

    def test_w_glide(self):
        self.check([('ウィウェウォ', '위웨워')])

    def test_small_vowel_replaces_the_vowel(self):
        self.check([('ティディトゥ', '티디투'),
                    ('ジェ', '제'),
                    ('チェ', '체')])

    def test_rare_kana(self):
        self.check([('ヂヅ', '지즈'),
                    ('ヴ', '부'),
                    ('ヰヱ', '이에'),
                    ('ヲ', '오')])

    def test_punctuation_becomes_a_space(self):
        self.assertEqual(kana_to_hangul('コンニチハ、ゲンキ？'), '콘니치하 겐키')

    def test_hiragana_reads_the_same_as_katakana(self):
        self.assertEqual(kana_to_hangul('ありがとー'), kana_to_hangul('アリガトー'))

    def test_word_starts_insert_a_space(self):
        self.assertEqual(kana_to_hangul('トーキョータワー', None, (0, 5)), '토쿄 타와')

    def test_empty_input(self):
        self.assertEqual(kana_to_hangul(''), '')
        self.assertEqual(ja_to_hangul(''), '')


class StyleOptions(unittest.TestCase):
    """The four knobs of translit_style, each pinned at both ends."""

    def test_tsu(self):
        self.assertEqual(kana_to_hangul('カツ'), '카츠')                    # default
        self.assertEqual(kana_to_hangul('カツ', {'tsu': 'ㅊ'}), '카츠')
        self.assertEqual(kana_to_hangul('カツ', {'tsu': 'ㅅ'}), '카쓰')
        self.assertEqual(kana_to_hangul('カツ', {'tsu': 'ㅉ'}), '카쯔')

    def test_initial_plain_affects_word_start_only(self):
        plain = {'initial': 'plain'}
        self.assertEqual(kana_to_hangul('カタカナ'), '카타카나')
        self.assertEqual(kana_to_hangul('カタカナ', plain), '가타카나')
        self.assertEqual(kana_to_hangul('タカラ', plain), '다카라')
        self.assertEqual(kana_to_hangul('チカ', plain), '지카')
        self.assertEqual(kana_to_hangul('ツ', plain), '즈')

    def test_long_vowel(self):
        keep, drop = {'long_vowel': 'keep'}, {'long_vowel': 'drop'}
        for kana, dropped, kept in [('トー', '토', '토오'),
                                    ('シュー', '슈', '슈우'),
                                    ('キャー', '캬', '캬아'),
                                    ('スー', '스', '스우')]:
            with self.subTest(kana=kana):
                self.assertEqual(kana_to_hangul(kana), dropped)      # drop is the default
                self.assertEqual(kana_to_hangul(kana, drop), dropped)
                self.assertEqual(kana_to_hangul(kana, keep), kept)

    def test_n_assim_only_before_labials(self):
        on = {'n_assim': True}
        self.assertEqual(kana_to_hangul('センパイ'), '센파이')
        self.assertEqual(kana_to_hangul('センパイ', on), '셈파이')
        self.assertEqual(kana_to_hangul('コンバン'), '콘반')
        self.assertEqual(kana_to_hangul('コンバン', on), '콤반')
        self.assertEqual(kana_to_hangul('センセイ', on), '센세이')   # not a labial, unchanged


class Invariants(unittest.TestCase):
    """What must hold for every kana under every style, so that a rule change cannot
    silently leave kana unread."""

    CORPUS = ['コンニチハ、ゲンキデスカ',
              'トーキョータワーデマッテル',
              'シャツヲカウ',
              ''.join(SYLLABLE), ''.join(SMALL_Y), ''.join(SMALL_V)]

    def test_default_style_keys(self):
        self.assertEqual(set(DEFAULT_STYLE), {'tsu', 'initial', 'long_vowel', 'n_assim'})

    def test_every_kana_maps_to_one_hangul_syllable(self):
        for kana in SYLLABLE:
            with self.subTest(kana=kana):
                out = kana_to_hangul(kana)
                self.assertEqual(len(out), 1)
                self.assertRegex(out, HANGUL_OR_SPACE)

    def test_no_kana_survives_any_style(self):
        for style in ALL_STYLES:
            for text in self.CORPUS:
                with self.subTest(style=style, text=text[:12]):
                    out = kana_to_hangul(text, style)
                    self.assertIsNone(KANA.search(out), f'kana left in {out!r}')
                    self.assertRegex(out, HANGUL_OR_SPACE)

    def test_no_leading_trailing_or_double_space(self):
        for style in ALL_STYLES:
            for text in self.CORPUS:
                with self.subTest(style=style, text=text[:12]):
                    out = kana_to_hangul(text, style)
                    self.assertEqual(out, out.strip())
                    self.assertNotIn('  ', out)


class JaToHangul(unittest.TestCase):
    """The whole pipeline: UniDic reading -> Hangul. These also pin which reading
    UniDic gives, so a dictionary change shows up here."""

    def test_sentences(self):
        for text, expected in [('ありがとう', '아리가토'),
                               ('待って', '맛테'),
                               ('先輩', '센파이'),
                               ('東京タワーで待ってる', '토쿄 타와데 맛테루'),
                               ('こんにちは、元気？', '콘니치와 겐키'),
                               ('ハローワールド', '하로 와루도')]:
            with self.subTest(text=text):
                self.assertEqual(ja_to_hangul(text), expected)

    def test_style_reaches_the_pipeline(self):
        self.assertEqual(ja_to_hangul('ありがとう', {'long_vowel': 'keep'}), '아리가토오')

    def test_latin_runs_pass_through(self):
        self.assertEqual(ja_to_hangul('Tokyo タワー'), 'Tokyo 타와')
        self.assertEqual(ja_to_hangul("rock'n roll"), "rock'n roll")

    def test_no_kana_survives_any_style(self):
        text = '明日は晴れるといいね、シャツをかつこう'
        for style in ALL_STYLES:
            with self.subTest(style=style):
                self.assertIsNone(KANA.search(ja_to_hangul(text, style)))


if __name__ == '__main__':
    unittest.main()
