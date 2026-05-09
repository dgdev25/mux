from mux.providers.local_executor import _parse_files_from_output


def test_parse_rejects_markdown_mode():
    raw = """# app.py
```python
print("hello")
```"""
    files, commands, summary, mode = _parse_files_from_output(raw)
    assert files == []
    assert commands == []
    assert summary == ""
    assert mode == "none"


def test_parse_rejects_absolute_path_in_json():
    raw = '{"files":[{"path":"/tmp/x.py","content":"print(1)"}],"commands":[],"summary":"x"}'
    files, commands, summary, mode = _parse_files_from_output(raw)
    assert files == []
    assert commands == []
    assert summary == ""
    assert mode.startswith("invalid_schema:")


def test_parse_accepts_valid_json_schema():
    raw = '{"files":[{"path":"pkg/main.py","content":"print(1)"}],"commands":["python3 -m pytest -q"],"summary":"ok"}'
    files, commands, summary, mode = _parse_files_from_output(raw)
    assert len(files) == 1
    assert commands == ["python3 -m pytest -q"]
    assert summary == "ok"
    assert mode == "json"
