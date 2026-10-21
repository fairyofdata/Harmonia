"""Stand-in for `mojimoji` (Cython, no Python 3.14 wheel), built on jaconv.

misaki[ja] only uses the zenkaku/hankaku conversions.
"""
import jaconv


def zen_to_han(text, ascii=True, digit=True, kana=True):
    return jaconv.z2h(text, ascii=ascii, digit=digit, kana=kana)


def han_to_zen(text, ascii=True, digit=True, kana=True):
    return jaconv.h2z(text, ascii=ascii, digit=digit, kana=kana)
