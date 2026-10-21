"""Japanese -> Hangul transliteration, approximating how a Korean speaker reads Japanese.

    >>> ja_to_hangul('ありがとう')
    '아리가토'
    >>> ja_to_hangul('ありがとう', {'long_vowel': 'keep'})
    '아리가토오'

Readings come from UniDic (fugashi + unidic-lite), so kanji are read the way
UniDic reads them (unusual lyric readings may differ). Rules are phonetic
approximations; `style` picks among conventions Korean fans actually use:

- tsu:        'ㅊ' (츠, default) | 'ㅅ' (쓰) | 'ㅉ' (쯔)
- initial:    'aspirated' (카/타 everywhere, default) | 'plain' (word-initial 가/다,
              as in the official 외래어 표기법)
- long_vowel: 'drop' (default, 토) | 'keep' (토오)
- n_assim:    False (ン is always ㄴ, default) | True (ン before ㅁ/ㅂ/ㅍ becomes ㅁ)

Always: ッ -> ㅅ final, ス/ズ -> 스/즈, フ -> 후, ファ行 -> ㅍ. Latin-script runs
are kept as written (Korean speakers say them in English).
"""
import re

# initial consonant indices (Unicode Hangul composition order)
G, KK, N, D, TT, R, M, B, PP, S, SS, NG, J, JJ, CH, K, T, P, H = range(19)
# vowel indices
A, AE, YA, YAE, EO, E, YEO, YE, O, WA, WAE, OE, YO, U, WO, WE, WI, YU, EU, UI, I = range(21)
FINAL_N, FINAL_M, FINAL_S = 4, 16, 19

FIVE = (A, I, U, E, O)
ROWS = {
    'アイウエオ': (NG, FIVE), 'カキクケコ': (K, FIVE), 'ガギグゲゴ': (G, FIVE),
    'サシスセソ': (S, (A, I, EU, E, O)), 'ザジズゼゾ': (J, (A, I, EU, E, O)),
    'タテト': (T, (A, E, O)), 'ダデド': (D, (A, E, O)),
    'ナニヌネノ': (N, FIVE), 'ハヒフヘホ': (H, FIVE), 'バビブベボ': (B, FIVE),
    'パピプペポ': (P, FIVE), 'マミムメモ': (M, FIVE), 'ヤユヨ': (NG, (YA, YU, YO)),
    'ラリルレロ': (R, FIVE), 'ワヲ': (NG, (WA, O)),
}
SYLLABLE = {}
for kana, (initial, vowels) in ROWS.items():
    for ch, v in zip(kana, vowels):
        SYLLABLE[ch] = (initial, v)
SYLLABLE.update({'チ': (CH, I), 'ツ': (CH, EU), 'ヂ': (J, I), 'ヅ': (J, EU), 'ヴ': (B, U), 'ヰ': (NG, I), 'ヱ': (NG, E)})

SMALL_Y = {'ャ': (YA, A), 'ュ': (YU, U), 'ョ': (YO, O)}   # (after most consonants, after ㅈ/ㅊ)
SMALL_V = {'ァ': A, 'ィ': I, 'ゥ': U, 'ェ': E, 'ォ': O}
W_GLIDE = {I: WI, E: WE, O: WO, A: WA}
TSU = {'ㅊ': CH, 'ㅅ': SS, 'ㅉ': JJ}
PLAIN = {K: G, T: D, CH: J}
LABIALS = {M, B, P, PP}
PUNCT = re.compile(r'[、。！？!?,.・「」『』（）()…〜~]')

DEFAULT_STYLE = {'tsu': 'ㅊ', 'initial': 'aspirated', 'long_vowel': 'drop', 'n_assim': False}


def _compose(initial, vowel, final=0):
    return chr(0xAC00 + (initial * 21 + vowel) * 28 + final)


def kana_to_hangul(kana, style=None, word_starts=()):
    """Katakana (or hiragana) pronunciation -> Hangul. word_starts: indices in `kana`
    where a word begins (for the 'plain' word-initial convention)."""
    st = {**DEFAULT_STYLE, **(style or {})}
    kana = ''.join(chr(ord(c) + 0x60) if 'ぁ' <= c <= 'ゖ' else c for c in kana)
    starts = set(word_starts) | {0}
    sylls = []  # [initial, vowel, final] or a plain string for passthrough
    for pos, ch in enumerate(kana):
        prev = sylls[-1] if sylls and isinstance(sylls[-1], list) else None
        if pos in starts and pos and sylls and sylls[-1] != ' ':
            sylls.append(' ')  # space between words, as Hangul lyric readings are written
            prev = None
        if ch in SYLLABLE:
            initial, vowel = SYLLABLE[ch]
            if ch == 'ツ':
                initial = TSU[st['tsu']]
            if st['initial'] == 'plain' and pos in starts:
                initial = PLAIN.get(initial, initial)
            if st['n_assim'] and prev and prev[2] == FINAL_N and initial in LABIALS:
                prev[2] = FINAL_M
            sylls.append([initial, vowel, 0])
        elif ch in SMALL_Y and prev:
            prev[1] = SMALL_Y[ch][1] if prev[0] in (J, CH, JJ) else SMALL_Y[ch][0]
        elif ch in SMALL_V and prev:
            v = SMALL_V[ch]
            if prev[0] == NG and prev[1] == U:      # ウィ ウェ ウォ
                prev[1] = W_GLIDE.get(v, v)
            elif prev[0] == H and prev[1] == U:     # ファ フィ フェ フォ
                prev[0], prev[1] = P, v
            else:                                   # ティ ディ シェ チェ トゥ ...
                prev[1] = v
        elif ch in 'ンッ':
            final = FINAL_N if ch == 'ン' else FINAL_S
            if prev and prev[2] == 0:
                prev[2] = final
            elif ch == 'ン':
                sylls.append([NG, EU, FINAL_N])
        elif ch == 'ー':
            if st['long_vowel'] == 'keep' and prev and prev[2] == 0:
                v = {YA: A, YU: U, YO: O, WA: A, WI: I, WE: E, WO: O, EU: U}.get(prev[1], prev[1])
                sylls.append([NG, v, 0])
        elif ch in SMALL_V or ch in SMALL_Y:
            continue
        else:
            sylls.append(' ' if not ch.strip() or PUNCT.match(ch) else ch)
    out = ''.join(_compose(*s) if isinstance(s, list) else s for s in sylls)
    return re.sub(r'\s+', ' ', out).strip()


_tagger = None
FUNCTION_POS = {'助詞', '助動詞', '接尾辞'}


def _reading(text):
    """(katakana pronunciation, indices where content words start)."""
    global _tagger
    if _tagger is None:
        import fugashi
        _tagger = fugashi.Tagger()
    parts, starts, length = [], [], 0
    for word in _tagger(text):
        if word.white_space:  # fugashi: whitespace *before* the token
            parts.append(' ')
            length += 1
        pron = getattr(word.feature, 'pron', None)
        piece = pron if pron and pron != '*' else word.surface
        if getattr(word.feature, 'pos1', '') not in FUNCTION_POS:
            starts.append(length)
        parts.append(piece)
        length += len(piece)
    return ''.join(parts), starts


def ja_to_hangul(text, style=None):
    """Japanese text -> Hangul reading. Latin-script runs pass through unchanged."""
    out = []
    for run in re.split(r'([A-Za-z][A-Za-z\'’\- ]*[A-Za-z]|[A-Za-z])', text):
        if not run:
            continue
        if re.match(r'[A-Za-z]', run):
            out.append(' ' + run + ' ')
        else:
            kana, starts = _reading(run)
            out.append(kana_to_hangul(kana, style, starts))
    return re.sub(r'\s+', ' ', ''.join(out)).strip()
