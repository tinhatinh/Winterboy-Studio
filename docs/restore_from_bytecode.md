# Khôi phục mã nguồn từ bytecode

Repo này sinh ra bằng cách chạy **Decompyle++** trên `.pyc` của app đã phát hành.
Nó KHÔNG phải mã nguồn gốc, và hỏng theo hai kiểu:

1. **Hỏng ồn ào** — file không parse được (`SrtCue = <NODE:12>()`, `None =` trong
   `except`, `getattr(...) = ...`, `from __future__` nằm sau `__doc__ = ...`).
2. **Hỏng im lặng** — file parse và import bình thường nhưng chạy sai. Ví dụ thật
   đã gặp: `if not text: text` rồi `text = ''.replace('\r','')` (làm rỗng chuỗi),
   `raw = None.read_text(...)` (nổ `AttributeError`), `def f(): pass` thay cho thân
   hàm bị mất, `return 0` trong khi bản gốc trả `0.0`.

Bản đúng là bytecode trong `_internal` của app đã cài:
`C:\Users\Administrator\MumuStudioPro\{app}\_internal` (CPython 3.12 — trùng phiên bản
đã biên dịch nên chữ ký và hằng số lấy được chính xác 100%).

## Quy trình bắt buộc cho mỗi module

```bash
python tools/dump_pyc.py app.services.<module>       # chữ ký thật, dataclass, docstring, hằng số
#   --body <fn>  : dis một hàm
#   --consts     : mọi chuỗi trong bytecode (đọc tên header, key, thông điệp lỗi)
# đọc file .py hiện tại, giữ lại phần còn đúng
# dò hành vi thật bằng cách GỌI bản .pyc (không đoán)
python tools/check_source.py --only app/services/<module>.py --damaged
python tests/run_tests.py <module>
```

### Dò hành vi

```bash
cd "C:\Users\Administrator\MumuStudioPro\{app}\_internal"
set PYTHONUTF8=1 && set PYTHONIOENCODING=utf-8   # không có là vỡ cp1252 khi in tiếng Việt
python -c "from app.services import x; print(x.f(...))"
```

### Test đối chiếu (`tests/_parity.py`)

```python
from _parity import same_result, ref_module, repo_module
bad = same_result('app.services.x', 'ten_ham', [(('đầu vào',), {}), ((None,), {'n': 2})])
assert not bad, bad
```

- `same_result` nạp module **hai lần theo đường dẫn file** (bỏ qua `app/services/__init__.py`,
  vì file đó import cả loạt module đang hỏng).
- Hai bên phải khớp cả giá trị trả về **lẫn kiểu exception**.
- `block=('pysrt',)` giả vờ thiếu module để cả hai cùng chạy một nhánh code.
- pytest **không** được cài; chạy bằng `python tests/run_tests.py`.

## Luật cứng

- **Không được đoán.** Không có bằng chứng từ bytecode hoặc từ việc gọi bản gốc →
  viết `raise NotImplementedError('chưa khôi phục từ bytecode: <module>.<fn>')` kèm
  comment nói vì sao. Một exception ầm thầm là ổn; một hàm chạy sai trong im lặng là
  tai nạn.
- **Không gọi mạng**, không chạy ffmpeg/demucs/model nặng khi dò. Hàm nào chạm mạng
  thì khôi phục mã theo dis, nhưng để nguyên không thực thi trong test.
- **Không commit, không push.** Không đổi `requirements.txt`, không cài thư viện.
- Chỉ sửa đúng file được giao + thêm `tests/test_<module>.py`.
- Giữ văn phong repo: indent 4 space, comment/docstring tiếng Việt, `'trích dẫn đơn'`.
- File nào khôi phục xong thì xoá dòng `# Source Generated with Decompyle++` ở đầu.
- Windows: đường dẫn phải bọc nháy, file tạm để trong `output/`, **không dùng `/tmp`**
  (MSYS và Python nhìn đường dẫn khác nhau).

## Kiểm chuẩn đã đạt

`app/services/srt_utils.py` + `tests/test_srt_utils.py` là mẫu chuẩn: mọi hàm đều có
bảng đầu vào (kèm biên: rỗng, `None`, unicode, chuỗi lạ) và khớp bản đã phát hành.
`main.py` + `tests/test_main_entry.py` là mẫu cho phần phải chạy ở tiến trình con
(vì nó đụng stdio toàn cục / mutex Win32).

## Cổng kiểm cuối

```bash
python tools/check_source.py --damaged --parity   # exit 0 = repo sạch
python tests/run_tests.py                          # 0 fail
```

`check_source.py` dùng `compile()` chứ không `ast.parse()`: `ast.parse` cho qua lỗi
`from __future__` đặt sai chỗ, nên nó không đủ.
