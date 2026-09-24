# -*- coding: utf-8 -*-
'''Đối chiếu app.services.translation_projects với bản đã phát hành.

Module quét JOBS_ROOT, nên mỗi test trỏ JOBS_ROOT của CẢ HAI bản vào những thư mục
tạm dựng y hệt nhau rồi so kết quả. Đường dẫn tuyệt đối của 2 cây khác nhau nên mọi
so sánh đều chuẩn hoá về đường dẫn tương đối.
'''
from __future__ import annotations

import json
import sys
import tempfile
import types
from pathlib import Path

from _parity import ref_module, repo_module

DOTTED = 'app.services.translation_projects'

SRT_BODY = '1\n00:00:01,000 --> 00:00:02,000\nA\n'


def _stub_dependencies():
    '''job_workspace vẫn còn hỏng cú pháp -> tạm cung cấp JOBS_ROOT để nạp được module.

    Giá trị stub không ảnh hưởng test: mọi case đều gán lại JOBS_ROOT cho cả hai bản.
    '''
    try:
        import app.services.job_workspace                                    # noqa: F401
    except Exception:
        holder = types.ModuleType('app.services.job_workspace')
        holder.JOBS_ROOT = Path(tempfile.gettempdir()) / 'mumu_stub_jobs'
        sys.modules['app.services.job_workspace'] = holder


_stub_dependencies()


def _pair():
    return ref_module(DOTTED), repo_module(DOTTED)


def _payload(**over):
    base = {
        'output_srt': 'video.srt', 'source_srt': 'video.srt', 'remaining_cues': 3,
        'total_cues': 10, 'last_source_cue': 7, 'status': 'running', 'engine': 'gemini',
        'model': 'gemini-2.5-flash', 'updated_at': '2026-01-02 03:04:05', 'note': 'ghi chu'}
    base.update(over)
    return base


def _j(payload):
    return json.dumps(payload, ensure_ascii=False)


def _make_jobs(specs):
    '''specs: {đường_rel_job: {tên_progress: nội dung thô | None (bỏ qua file)}}'''
    root = Path(tempfile.mkdtemp())
    for job_name, files in specs.items():
        job = root / job_name
        job.mkdir(parents=True)
        (job / 'video.srt').write_text(SRT_BODY, encoding='utf-8')
        (job / 'source.srt').write_text(' nguon ', encoding='utf-8')
        for progress_name, raw in files.items():
            if raw is None:
                continue
            (job / progress_name).write_text(raw, encoding='utf-8')
            sidecar = progress_name.removesuffix('.progress.json') + '.translation.jsonl'
            (job / sidecar).write_text('12345', encoding='utf-8')
    return root


def _rel(root, value):
    '''Path -> đường dẫn tương đối so với root; giá trị khác giữ nguyên biểu diễn.'''
    if isinstance(value, Path):
        try:
            return str(value.relative_to(root)).replace('\\', '/')
        except ValueError:
            return '<ngoai-root:' + value.name + '>'
    return str(value)


def _row(project, root):
    return sorted(f'{k}={_rel(root, v)}' for k, v in vars(project).items())


def _scan_both(specs, **kw):
    '''Dựng 2 cây giống hệt nhau, quét bằng 2 bản, trả về {label: (dòng, root)}.'''
    ref, rep = _pair()
    out = {}
    for label, mod in (('repo', rep), ('ref', ref)):
        root = _make_jobs(specs)
        mod.JOBS_ROOT = root
        out[label] = (sorted([_row(p, root) for p in
                              mod.list_unfinished_translation_projects(**kw)]), root)
    return out


def test_dataclass_field_names_match():
    ref, rep = _pair()
    for cls in ('TranslationProject', 'TranslationLogCleanup'):
        a = [f.name for f in rep.__dict__[cls].__dataclass_fields__.values()]
        b = [f.name for f in ref.__dict__[cls].__dataclass_fields__.values()]
        assert a == b, (cls, a, b)
    a = rep.TranslationProject(rep.Path('C:/j/web/v.srt.progress.json'), rep.Path('x.srt'),
                               rep.Path('x.jsonl'), None, 's', 'e', 'm', 1, 2, 3, '2026', 'n')
    b = ref.TranslationProject(ref.Path('C:/j/web/v.srt.progress.json'), ref.Path('x.srt'),
                               ref.Path('x.jsonl'), None, 's', 'e', 'm', 1, 2, 3, '2026', 'n')
    assert repr(a) == repr(b), (repr(a), repr(b))
    assert vars(rep.TranslationLogCleanup(1, 2, 3, 4)) == vars(
        ref.TranslationLogCleanup(1, 2, 3, 4))


def test_label_property():
    '''label = tên thư mục "ông nội" của file progress; rỗng thì mới lấy SRT nguồn.'''
    ref, rep = _pair()
    cases = ['C:/jobs/jobA/sub/v.srt.progress.json', 'C:/jobs/jobA/v.srt.progress.json',
             'v.srt.progress.json', './sub/v.srt.progress.json']
    for progress in cases:
        for source in (None, 'C:/x/nguon.srt', 'C:/x/'):
            for srt in ('x.srt', 'khac.srt'):
                paths = (progress, srt, 'x.jsonl', source)
                a = rep.TranslationProject(*[rep.Path(x) if x else None for x in paths],
                                           status='s', engine='e', model='m', total_cues=1,
                                           remaining_cues=2, last_source_cue=3,
                                           updated_at='2026', note='n').label
                b = ref.TranslationProject(*[ref.Path(x) if x else None for x in paths],
                                           status='s', engine='e', model='m', total_cues=1,
                                           remaining_cues=2, last_source_cue=3,
                                           updated_at='2026', note='n').label
                assert a == b, (paths, a, b)
                assert isinstance(a, str) and len(a) <= 100, (paths, a)
    # nhánh "tên thư mục cha rỗng": source_path có tên -> lấy tên nó
    got = {}
    for label, mod in (('repo', rep), ('ref', ref)):
        got[label + ':src'] = mod.TranslationProject(
            mod.Path('v.srt.progress.json'), mod.Path('x.srt'), mod.Path('x.jsonl'),
            mod.Path('C:/x/nguon.srt'), 's', 'e', 'm', 1, 2, 3, '2026', 'n').label
        got[label + ':emptyname'] = mod.TranslationProject(
            mod.Path('v.srt.progress.json'), mod.Path('x.srt'), mod.Path('x.jsonl'),
            mod.Path('C:/'), 's', 'e', 'm', 1, 2, 3, '2026', 'n').label
    assert got['repo:src'] == got['ref:src'] == 'nguon.srt', got
    # source_path tên rỗng -> chuỗi rỗng[:100] vẫn falsy, quay lại lấy tên srt_path
    assert got['repo:emptyname'] == got['ref:emptyname'] == 'x.srt', got
    deep = f'''C:/jobs/{'d' * 200}/sub/v.srt.progress.json'''
    cut = {}
    for label, mod in (('repo', rep), ('ref', ref)):
        cut[label] = mod.TranslationProject(mod.Path(deep), mod.Path('x.srt'),
                                            mod.Path('x.jsonl'), None, 's', 'e', 'm',
                                            1, 2, 3, '2026', 'n').label
    assert cut['repo'] == cut['ref'] == 'd' * 100, cut


def test_list_missing_or_empty_root():
    ref, rep = _pair()
    for mod in (ref, rep):
        mod.JOBS_ROOT = Path(tempfile.mkdtemp()) / 'khong-ton-tai'
        assert mod.list_unfinished_translation_projects() == []
    for mod in (ref, rep):
        mod.JOBS_ROOT = _make_jobs({})
        assert mod.list_unfinished_translation_projects() == []


def test_list_filters_and_fields():
    p = _payload
    specs = {
        'ok': {'video.srt.progress.json': _j(p())},
        'done': {'video.srt.progress.json': _j(p(remaining_cues=0))},
        'negative': {'video.srt.progress.json': _j(p(remaining_cues=-2))},
        'zero-string': {'video.srt.progress.json': _j(p(remaining_cues='0'))},
        'fallback-name': {'video.srt.progress.json': _j(p(output_srt=''))},
        'srt-missing': {'video.srt.progress.json': _j(p(output_srt='khong-co.srt'))},
        'not-a-dict': {'video.srt.progress.json': '[]'},
        'broken-json': {'video.srt.progress.json': '{khong phai json'},
        'empty-payload': {'video.srt.progress.json': '{}'},
        'no-progress-file': {'video.srt.progress.json': None},
        'source-missing': {'video.srt.progress.json': _j(p(source_srt='khong-co.srt'))},
        'source-relative': {'video.srt.progress.json': _j(p(source_srt='source.srt'))},
        'weird-types': {'video.srt.progress.json': _j(p(
            status=None, engine=5, model=['m'], total_cues='4', last_source_cue=None,
            updated_at=7, note=False))},
        'nested/jobA/sub': {'video.srt.progress.json': _j(p())},
    }
    got = _scan_both(specs)
    rows = got['ref'][0]
    assert got['repo'][0] == rows, (got['repo'][0], rows)
    # 6 project thoả: remaining > 0 và file SRT đầu ra tồn tại
    assert len(rows) == 6, [r[0] for r in rows]
    flat = '\n'.join('\n'.join(r) for r in rows)
    assert 'source-relative/video.srt' in flat, flat
    assert 'done/' not in flat and 'negative/' not in flat and 'zero-string/' not in flat
    assert 'broken-json/' not in flat and 'not-a-dict/' not in flat
    assert "status=unknown" in flat, flat        # weird-types: payload.get('status') is None
    assert 'note=' in flat, flat                 # note=False -> str(False or '') = ''


def test_log_path_naming():
    '''log_path = tên progress cắt ".progress.json" rồi nối ".translation.jsonl".'''
    specs = {'j': {'a.srt.progress.json': _j(_payload()),
                   'b.c.srt.progress.json': _j(_payload())}}
    ref, rep = _pair()
    names = {}
    for label, mod in (('repo', rep), ('ref', ref)):
        root = _make_jobs(specs)
        mod.JOBS_ROOT = root
        names[label] = sorted(p.log_path.name
                              for p in mod.list_unfinished_translation_projects())
    assert names['repo'] == names['ref'], names
    assert names['ref'] == ['a.srt.translation.jsonl', 'b.c.srt.translation.jsonl'], names


def test_list_sort_order_and_limit():
    specs = {
        'bbb': {'video.srt.progress.json': _j(_payload(updated_at='2026-01-01 00:00:00'))},
        'aaa': {'video.srt.progress.json': _j(_payload(updated_at='2026-01-09 00:00:00'))},
        'ccc': {'video.srt.progress.json': _j(_payload(updated_at='2026-01-05 00:00:00'))}}
    ref, rep = _pair()
    for limit in (1, 2, 3, 0, -3, 100):
        rows = {}
        for label, mod in (('repo', rep), ('ref', ref)):
            root = _make_jobs(specs)
            mod.JOBS_ROOT = root
            rows[label] = [_row(p, root) for p in
                           mod.list_unfinished_translation_projects(limit=limit)]
        assert rows['repo'] == rows['ref'], (limit, rows)
        assert len(rows['ref']) == min(max(1, limit), 3), (limit, len(rows['ref']))
    root = _make_jobs(specs)
    ref.JOBS_ROOT = root
    order = [p.updated_at for p in ref.list_unfinished_translation_projects()]
    assert order == ['2026-01-09 00:00:00', '2026-01-05 00:00:00',
                     '2026-01-01 00:00:00'], order


def test_cleanup_keeps_newest_and_reports_reclaim():
    specs = {
        'a': {'v1.srt.progress.json': _j(_payload(updated_at='2026-01-01 00:00:00'))},
        'b': {'v1.srt.progress.json': _j(_payload(updated_at='2026-01-02 00:00:00'))},
        'c': {'v1.srt.progress.json': _j(_payload(updated_at='2026-01-03 00:00:00'))}}

    def run(mod, keep):
        root = _make_jobs(specs)
        mod.JOBS_ROOT = root
        res = mod.cleanup_old_translation_logs(keep=keep)
        left = sorted(str(p.relative_to(root)).replace('\\', '/')
                      for p in root.rglob('*') if p.is_file())
        return (res.kept, res.removed_projects, res.removed_files, res.reclaimed_bytes, left)

    ref, rep = _pair()
    for keep in (1, 2, 3, 9):
        a, b = run(rep, keep), run(ref, keep)
        assert a == b, (keep, a, b)
    kept = run(ref, 1)
    assert kept[0] == 1, kept                       # kept = min(keep, len(projects))
    assert kept[1] == 2, kept                       # xoá xong 2 project cũ nhất
    assert kept[2] == 4, kept                       # progress + jsonl của a và b
    assert kept[3] > 0, kept
    assert 'c/v1.srt.progress.json' in kept[4], kept[4]
    assert 'a/v1.srt.progress.json' not in kept[4], kept[4]
    assert 'a/video.srt' in kept[4], kept[4]        # SRT bán dịch không bao giờ bị xoá
    assert run(ref, 9)[:4] == (3, 0, 0, 0), run(ref, 9)


def test_cleanup_survives_missing_sidecars():
    '''jsonl bị xoá tay trước khi dọn -> vẫn xoá progress, không nổ, không đếm thừa.'''
    specs = {
        'a': {'v1.srt.progress.json': _j(_payload())},
        'b': {'v1.srt.progress.json': _j(_payload(updated_at='2026-01-05 00:00:00'))}}

    def run(mod):
        root = _make_jobs(specs)
        for name in ('a', 'b'):
            (root / name / 'v1.srt.translation.jsonl').unlink()
        mod.JOBS_ROOT = root
        res = mod.cleanup_old_translation_logs(keep=1)
        return (res.kept, res.removed_projects, res.removed_files, res.reclaimed_bytes,
                sorted(p.name for p in root.rglob('*') if p.is_file()))

    ref, rep = _pair()
    a, b = run(rep), run(ref)
    assert a == b, (a, b)
    assert a[:3] == (1, 1, 1), a                   # chỉ còn progress của project cũ nhất
    assert a[4].count('v1.srt.progress.json') == 1, a[4]


def test_cleanup_keep_coercion_matches_reference():
    ref, rep = _pair()
    for keep in (0, -5, 1, 2, 1.0, True):
        out = []
        for mod in (rep, ref):
            mod.JOBS_ROOT = _make_jobs({})
            r = mod.cleanup_old_translation_logs(keep=keep)
            out.append((r.kept, r.removed_projects, r.removed_files, r.reclaimed_bytes))
        assert out[0] == out[1], (keep, out)
    for keep in ('abc', None, [1]):
        errs = []
        for mod in (rep, ref):
            mod.JOBS_ROOT = _make_jobs({})
            try:
                mod.cleanup_old_translation_logs(keep=keep)
                errs.append('ok')
            except Exception as exc:
                errs.append(type(exc).__name__)
        assert errs[0] == errs[1], (keep, errs)
