# -*- coding: utf-8 -*-
'''Fuzzer đối chiếu parse_srt_string / wrap_subtitle_text với bản đã phát hành.

Test bảng đầu vào cố định bỏ sót những chỗ như "dòng trắng nằm giữa một cue".
Sinh ngẫu nhiên hàng trăm chuỗi theo đúng hình thái SRT (kèm biến thể hỏng) rồi so
kết quả hai bên là cách rẻ nhất để tìm ra chỗ dịch ngược lệch hành vi.
'''
from __future__ import annotations

import random

from _parity import repo_module, ref_module

DOTTED = 'app.services.srt_utils'
SEED = 20260924
ROUNDS = 400


def _ts(rng):
    h = rng.choice([0, 0, 0, 1, 7, 23])
    m = rng.choice([0, 5, 30, 59])
    s = rng.choice([0, 1, 12, 59])
    ms = rng.choice([0, 250, 500, 999])
    sep = rng.choice([',', '.', ','])
    return f'{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}'


def _text(rng):
    pool = ['Xin chào', 'một đoạn dài hơn', '', '   ', 'hai\ndòng', 'kế\ttiếp',
            'tiếng Việt ă â ê ô ư ợ', 'A' * 60, 'dấu | gạch', '# không phải comment',
            '   có khoảng trắng thừa   ', '— gạch ngang']
    n = rng.randint(0, 3)
    return [rng.choice(pool) for _ in range(n)]


def gen(rng):
    """Sinh một nội dung SRT ngẫu nhiên, có chủ đích bao gồm cả dữ liệu bẩn."""
    chunks = []
    for i in range(rng.randint(1, 4)):
        start, end = _ts(rng), _ts(rng)
        style = rng.random()
        if style < 0.08:
            chunks.append(f'{i + 1}\n{start} --> {end}\n')            # thiếu text
        elif style < 0.16:
            chunks.append(f'{start} --> {end}\nabc\n')                # thiếu số thứ tự
        elif style < 0.24:
            chunks.append('rác không phải srt')
        elif style < 0.30:
            chunks.append('hai dòng rác\nkhông có dòng thời gian')   # block >=2 dòng, không match
        elif style < 0.36:
            chunks.append(f'{start} --> {end}\ndòng 1\ndòng 2\ndòng 3')
        else:
            lines = _text(rng)
            body = '\n'.join(lines) if lines else ''
            chunks.append(f'{i + 1}\n{start} --> {end}\n{body}')
    joiner = rng.choice(['\n\n', '\n\n\n', '\n \n', '\n\n  \n'])
    return joiner.join(chunks)


def test_parse_srt_string_matches_on_random_corpus():
    rep, ref = repo_module(DOTTED), ref_module(DOTTED)
    rng = random.Random(SEED)
    diffs = []
    for _ in range(ROUNDS):
        raw = gen(rng)
        try:
            a = rep.parse_srt_string(raw)
        except Exception as exc:
            a = ('exc', type(exc).__name__)
        try:
            b = ref.parse_srt_string(raw)
        except Exception as exc:
            b = ('exc', type(exc).__name__)
        ta = [(c.index, round(c.start_s, 6), round(c.end_s, 6), c.text)
              if hasattr(c, 'index') else c for c in a]
        tb = [(c.index, round(c.start_s, 6), round(c.end_s, 6), c.text)
              if hasattr(c, 'index') else c for c in b]
        if ta != tb:
            diffs.append((raw, ta, tb))
    assert not diffs, (f'{len(diffs)}/{ROUNDS} chuỗi lệch; ví dụ: '
                       f'{diffs[0][0]!r}\n  repo={diffs[0][1]}\n  ref ={diffs[0][2]}')


def test_wrap_matches_on_random_corpus():
    rep, ref = repo_module(DOTTED), ref_module(DOTTED)
    rng = random.Random(SEED + 1)
    words = ['xin', 'chào', 'việt', 'nam', 'a' * 30, '', '   ', 'siêu', 'dài',
             'ă', 'word1 word2', 'tab\ttrong']
    diffs = []
    for _ in range(ROUNDS):
        text = ' '.join(rng.choice(words) for _ in range(rng.randint(0, 14)))
        mc = rng.choice([4, 8, 12, 22, 42])
        ml = rng.choice([1, 2, 3, 4])
        a = rep.wrap_subtitle_text(text, max_chars=mc, max_lines=ml)
        b = ref.wrap_subtitle_text(text, max_chars=mc, max_lines=ml)
        if a != b:
            diffs.append((text, mc, ml, a, b))
    assert not diffs, (f'{len(diffs)}/{ROUNDS} lệch; ví dụ: {diffs[0][0]!r} '
                       f'max_chars={diffs[0][1]} max_lines={diffs[0][2]}\n'
                       f'  repo={diffs[0][3]!r}\n  ref ={diffs[0][4]!r}')


def test_duration_s_rounds_like_reference():
    rep, ref = repo_module(DOTTED), ref_module(DOTTED)
    cases = [(0.0, 2.5), (1 / 3, 2 / 3), (0.1, 0.30000000000000004), (5.0, 5.0),
             (12.3456, 13.9999), (0.0, 0.0)]
    for s, e in cases:
        assert rep.SrtCue(0, s, e, 'x').duration_s == ref.SrtCue(0, s, e, 'x').duration_s, (s, e)
