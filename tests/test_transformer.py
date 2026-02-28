from pathlib import Path

from ever2obsidian.cli import main


def run_cli(tmp_path: Path, input_files: dict[str, str], extra: list[str] | None = None) -> Path:
    in_dir = tmp_path / "in"
    out_dir = tmp_path / "out"
    in_dir.mkdir(parents=True)
    for rel, content in input_files.items():
        path = in_dir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    args = ["--input", str(in_dir), "--output", str(out_dir), "--stats"] + (extra or [])
    rc = main(args)
    assert rc == 0
    return out_dir


def test_frontmatter_conversion(tmp_path: Path):
    out = run_cli(
        tmp_path,
        {
            "note.md": """---
Created at: 2023-02-01T13:00:00
Last updated at: 2023-03-01T10:00:00
Source URL: https://example.org/article/1
---
# Note
Body
"""
        },
    )
    content = next(out.glob("**/*.md")).read_text(encoding="utf-8")
    assert "title: Note" in content
    assert "created: '2023-02-01'" in content
    assert "updated: '2023-03-01'" in content
    assert "source: 'https://example.org/article/1'" in content


def test_marker_extraction_tags_and_classification(tmp_path: Path):
    out = run_cli(
        tmp_path,
        {"p.md": "# Person\n// PERSON MK\ntext\n"},
    )
    pfile = next(out.glob("People/*.md"))
    c = pfile.read_text(encoding="utf-8")
    assert "- person" in c
    assert "- mk" in c
    assert "type: People" in c
    assert "// PERSON" not in c


def test_link_insertion_exclusions(tmp_path: Path):
    out = run_cli(
        tmp_path,
        {
            "alpha.md": "# Alpha\nBeta is related.\n`Beta`\n[Beta](https://x)\n```\nBeta\n```\n",
            "beta.md": "# Beta\nBody\n",
        },
        extra=["--link-min-confidence", "0.4"],
    )
    alpha = [p for p in out.glob("**/*.md") if "Alpha" in p.name][0].read_text(encoding="utf-8")
    assert "[[Beta]] is related." in alpha
    assert "`Beta`" in alpha
    assert "[Beta](https://x)" in alpha


def test_resource_rewriting(tmp_path: Path):
    out = run_cli(
        tmp_path,
        {
            "_resources/img.png": "PNGDATA",
            "n.md": "# N\n![](./_resources/img.png)\n",
        },
    )
    note = next(out.glob("**/N.md")).read_text(encoding="utf-8")
    assert "![[attachments/img.png]]" in note
    assert (out / "attachments" / "img.png").exists()


def test_idempotency(tmp_path: Path):
    first = run_cli(tmp_path / "t1", {"a.md": "# A\n// NOTE - hi\ntext\n"})
    second_root = tmp_path / "t2"
    out2 = run_cli(second_root, {p.name: p.read_text(encoding="utf-8") for p in first.glob("**/*.md") if "_logs" not in str(p)})
    files1 = sorted([p for p in first.glob("**/*.md") if "_logs" not in str(p)])
    files2 = sorted([p for p in out2.glob("**/*.md") if "_logs" not in str(p)])
    assert len(files1) == len(files2)
    assert [p.read_text(encoding="utf-8") for p in files1] == [p.read_text(encoding="utf-8") for p in files2]

def test_no_tagging_option(tmp_path: Path):
    out = run_cli(tmp_path, {"n.md": "# N\n// PERSON MK\n- [ ] todo\n"}, extra=["--no-tagging"])
    content = next(out.glob("**/N.md")).read_text(encoding="utf-8")
    assert "tags:" in content
    assert "- person" not in content
    assert "- task" not in content


def test_no_classify_option(tmp_path: Path):
    out = run_cli(tmp_path, {"p.md": "# P\n// PERSON MK\n"}, extra=["--no-classify"])
    assert (out / "Other" / "P.md").exists()
