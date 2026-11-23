"""Text splitting in localtts/supertonic_backend.py.

Supertonic's vector estimator attends over a limited number of latent frames per
chunk; feed it more and the tail of the audio comes out garbled or missing (checked
by synthesizing 129 characters of unpunctuated Japanese and transcribing the result).
These tests cover the splitting only -- they load no model, so they are fast.
"""
import unittest

from localtts.supertonic_backend import MAX_CHUNK_CHARS as LIMIT
from localtts.supertonic_backend import _chunks


class Chunks(unittest.TestCase):

    def assert_within_limit(self, text):
        """Every chunk fits, nothing is empty, and the text is preserved."""
        chunks = _chunks(text)
        for c in chunks:
            self.assertLessEqual(len(c), LIMIT, f'chunk over the limit: {c!r}')
            self.assertTrue(c, 'empty chunk')
        self.assertEqual(''.join(chunks).replace(' ', ''), text.replace(' ', ''))
        return chunks

    def test_short_text_stays_one_chunk(self):
        self.assertEqual(_chunks('짧은 글'), ['짧은 글'])
        self.assertEqual(_chunks('a'), ['a'])

    def test_empty_text(self):
        self.assertEqual(_chunks(''), [])

    def test_splits_at_spaces(self):
        chunks = self.assert_within_limit(' '.join(['가나다라마'] * 30))
        self.assertGreater(len(chunks), 1)
        for c in chunks:
            self.assertNotIn('  ', c)
            self.assertEqual(c, c.strip())

    def test_boundary_at_the_limit(self):
        word = 'a' * (LIMIT - 2)
        self.assertEqual(_chunks(f'{word} b'), [f'{word} b'])       # exactly the limit, one chunk
        self.assertEqual(_chunks(f'{word}x b'), [f'{word}x', 'b'])  # one over, split
        self.assertEqual(_chunks('a' * LIMIT), ['a' * LIMIT])       # a word exactly at the limit

    def test_long_unspaced_text_is_split_by_characters(self):
        """Japanese and Chinese have no spaces, so without this the whole text went to
        the model as a single chunk and its tail was lost."""
        ja = ('きょうはとてもいいてんきなのでこうえんまであるいていってそこでおべんとうをたべてからほんをよんで'
              'ゆっくりすごすつもりですがもしあめがふったらとしょかんにいってしりょうをしらべるつもりでいます'
              'そのあとはかいものをしてゆうはんのざいりょうをかってかえるよていです')
        chunks = self.assert_within_limit(ja)
        self.assertEqual([len(c) for c in chunks], [LIMIT, len(ja) - LIMIT])   # 129 characters
        self.assertEqual(''.join(chunks), ja)   # no space is inserted into unspaced text

    def test_one_long_word_among_short_ones(self):
        chunks = self.assert_within_limit(f"짧다 {'나' * (LIMIT * 2 + 5)} 또 짧다")
        self.assertEqual(chunks[0], '짧다')     # the short head is flushed first, in order
        self.assertEqual(chunks[1], '나' * LIMIT)
        self.assertEqual(chunks[-1], '나' * 5 + ' 또 짧다')   # the remainder keeps filling up

    def test_lengths_of_a_mixed_text(self):
        for text in ['x' * 100,
                     'x' * 100 + ' y',
                     ' '.join(['word'] * 50),
                     '안녕하세요 ' * 40,
                     'あ' * 500]:
            with self.subTest(text=text[:20]):
                self.assert_within_limit(text)


if __name__ == '__main__':
    unittest.main()
