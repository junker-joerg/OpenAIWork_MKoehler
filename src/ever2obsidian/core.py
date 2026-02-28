from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

try:
    import yaml  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    yaml = None

DEFAULT_CONFIG = {
    "attachments_dir": "attachments",
    "resources_dir_name": "_resources",
    "prefer_wikilink_embeds": True,
    "keep_meta_section": False,
    "inline_tags": False,
    "classification_weights": {
        "person_marker": 0.7,
        "research_marker": 0.7,
        "task_checkbox": 0.6,
        "project_title": 0.6,
        "literature_source": 0.65,
        "story_keywords": 0.6,
        "fallback_inbox": 0.45,
    },
    "folder_map": {
        "People": "People",
        "Research": "Research",
        "Project": "Projects",
        "Task": "Tasks",
        "Literature": "Literature",
        "Story": "Story",
        "Inbox": "Inbox",
        "Other": "Other",
    },
    "stopwords": ["and", "the", "oder", "und", "ein", "eine", "der", "die", "das", "for", "mit"],
    "whitelist_titles": ["AI", "ML", "UX", "UI"],
    "tag_rules": {
        "regex_mappings": [
            {"pattern": r"\bpython\b", "tag": "python"},
            {"pattern": r"\bobsidian\b", "tag": "obsidian"},
        ]
    },
}

META_LINE_RE = re.compile(r"^//\s*([A-ZÄÖÜa-zäöüß]+)(?:\s+(.+))?$")
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
TRAILING_DECOR_RE = re.compile(r"\s*[🔽▼]+\s*$")
MARKDOWN_LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^\)]+)\)")


@dataclass
class Note:
    source_path: Path
    rel_path: Path
    original_filename: str
    title: str
    body: str
    metadata: dict[str, object] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    aliases: list[str] = field(default_factory=list)
    markers: list[tuple[str, str]] = field(default_factory=list)
    has_tasks: bool = False
    classification: str = "Other"
    confidence: float = 0.0
    output_path: Path | None = None
    links_inserted: int = 0
    attachments_moved: int = 0


class Transformer:
    def __init__(self, config: dict, args: argparse.Namespace):
        self.config = config
        self.args = args
        self.used_filenames: set[Path] = set()
        self.alias_index: dict[str, str] = {}
        self.link_report: dict[Path, list[str]] = defaultdict(list)

    def run(self, input_dir: Path, output_dir: Path) -> int:
        notes = self._collect_notes(input_dir)
        self._build_title_index(notes)
        log_entries: list[dict[str, object]] = []

        for note in notes:
            if not self.args.no_classify:
                self._classify(note)
            else:
                note.classification = "Other"
                note.confidence = 0.0

            if not self.args.no_linking:
                self._insert_links(note)

            target_folder = self.config["folder_map"].get(note.classification, "Other")
            file_title = self._next_safe_filename(Path(target_folder), note.title)
            note.output_path = output_dir / target_folder / f"{file_title}.md"

            text = self._compose(note)
            text, moved = self._rewrite_attachments(note, text, output_dir)
            note.attachments_moved = moved

            if not self.args.dry_run:
                note.output_path.parent.mkdir(parents=True, exist_ok=True)
                note.output_path.write_text(text, encoding="utf-8")

            log_entries.append(
                {
                    "original_path": str(note.source_path),
                    "output_path": str(note.output_path),
                    "extracted_metadata": note.metadata,
                    "classification": note.classification,
                    "confidence": round(note.confidence, 2),
                    "tags": note.tags,
                    "links_inserted_count": note.links_inserted,
                    "attachments_moved_count": note.attachments_moved,
                    "links_inserted": self.link_report[note.source_path],
                }
            )

        if not self.args.dry_run:
            self._write_log(output_dir, log_entries)

        if self.args.stats:
            print(json.dumps(self._stats(notes), ensure_ascii=False, indent=2))

        return 0

    def _collect_notes(self, input_dir: Path) -> list[Note]:
        includes = self.args.include or ["**/*.md"]
        excludes = self.args.exclude or []
        files: set[Path] = set()
        for pattern in includes:
            files.update(path for path in input_dir.glob(pattern) if path.is_file())
        for pattern in excludes:
            files = {path for path in files if not path.match(pattern)}

        notes: list[Note] = []
        for path in sorted(files):
            raw = path.read_text(encoding="utf-8", errors="replace")
            metadata, body = self._extract_meta(raw)
            title = self._extract_title(path, body, metadata)
            body = self._normalize_body(title, body)
            markers, body = self._extract_markers(body)

            has_tasks = bool(re.search(r"^- \[[ xX]\]", body, flags=re.MULTILINE))
            aliases = list(metadata.get("aliases", [])) if isinstance(metadata.get("aliases"), list) else []
            existing_tags = list(metadata.get("tags", [])) if isinstance(metadata.get("tags"), list) else []
            derived_tags = [] if self.args.no_tagging else self._derive_tags(markers, body, metadata, has_tasks)
            tags = self._merge_stable_tags(existing_tags, derived_tags)

            notes.append(
                Note(
                    source_path=path,
                    rel_path=path.relative_to(input_dir),
                    original_filename=str(metadata.get("original_filename", path.name)),
                    title=title,
                    body=body,
                    metadata=metadata,
                    tags=tags,
                    aliases=aliases,
                    markers=markers,
                    has_tasks=has_tasks,
                )
            )
        return notes

    def _extract_meta(self, text: str) -> tuple[dict[str, object], str]:
        lines = text.splitlines()
        meta: dict[str, object] = {}

        if len(lines) < 3 or lines[0].strip() != "---":
            return meta, text

        try:
            end = lines.index("---", 1)
        except ValueError:
            return meta, text

        block = "\n".join(lines[1:end])
        parsed = yaml_load(block) if block.strip() else {}

        if isinstance(parsed, dict):
            self._merge_frontmatter_meta(meta, parsed)

        tag_block = re.search(r"(?ms)^tags:\s*\n((?:\s*-\s*.*\n?)*)", block)
        if tag_block:
            parsed_tags = []
            for row in tag_block.group(1).splitlines():
                row = row.strip()
                if row.startswith("- "):
                    parsed_tags.append(row[2:].strip().strip("'").strip("\""))
            if parsed_tags:
                meta["tags"] = parsed_tags

        alias_block = re.search(r"(?ms)^aliases:\s*\n((?:\s*-\s*.*\n?)*)", block)
        if alias_block:
            parsed_aliases = []
            for row in alias_block.group(1).splitlines():
                row = row.strip()
                if row.startswith("- "):
                    parsed_aliases.append(row[2:].strip().strip("'").strip("\""))
            if parsed_aliases:
                meta["aliases"] = parsed_aliases

        # Evernote key mapping from raw lines always wins for those fields.
        for line in lines[1:end]:
            if ":" not in line:
                continue
            k, v = line.split(":", 1)
            key = k.strip().lower()
            val = v.strip().strip('"').strip("'")
            if key == "created at":
                meta["created"] = val[:10]
            elif key == "last updated at":
                meta["updated"] = val[:10]
            elif key == "source url":
                meta["source"] = val

        body = "\n".join(lines[end + 1 :]).lstrip("\n")
        return meta, body

    def _merge_frontmatter_meta(self, meta: dict[str, object], parsed: dict[str, object]) -> None:
        title = parsed.get("title")
        if isinstance(title, str) and title.strip():
            meta["title"] = title.strip()

        for key in ("created", "updated", "source"):
            value = parsed.get(key)
            if isinstance(value, str) and value.strip():
                meta[key] = value.strip()

        tags = parsed.get("tags")
        if isinstance(tags, list):
            meta["tags"] = [str(v).strip() for v in tags if str(v).strip()]

        aliases = parsed.get("aliases")
        if isinstance(aliases, list):
            meta["aliases"] = [str(v).strip() for v in aliases if str(v).strip()]

        evernote = parsed.get("evernote")
        if isinstance(evernote, dict) and isinstance(evernote.get("original_filename"), str):
            meta["original_filename"] = evernote["original_filename"].strip()

    def _extract_title(self, path: Path, body: str, meta: dict[str, object]) -> str:
        stored = meta.get("title")
        if isinstance(stored, str) and stored.strip():
            return stored.strip()
        for line in body.splitlines():
            if line.startswith("# "):
                return line[2:].strip()
        return path.stem

    def _normalize_body(self, title: str, body: str) -> str:
        cleaned = HTML_COMMENT_RE.sub("", body)
        output: list[str] = []
        removed_h1 = False

        for line in cleaned.splitlines():
            line = TRAILING_DECOR_RE.sub("", line).rstrip()
            if not removed_h1 and line.strip() == f"# {title}":
                removed_h1 = True
                continue
            output.append(line)

        return "\n".join(output).strip() + "\n"

    def _extract_markers(self, body: str) -> tuple[list[tuple[str, str]], str]:
        markers: list[tuple[str, str]] = []
        kept_lines: list[str] = []

        for line in body.splitlines():
            match = META_LINE_RE.match(line.strip())
            if not match:
                kept_lines.append(line)
                continue

            key = match.group(1).lower()
            value = (match.group(2) or "").strip()
            if key in {"anchor", "fixme", "note", "person", "forschung", "technologie", "research"}:
                markers.append((key, value))
                if self.config.get("keep_meta_section"):
                    kept_lines.append(line)
            else:
                kept_lines.append(line)

        return markers, "\n".join(kept_lines).strip() + "\n"

    def _derive_tags(self, markers: list[tuple[str, str]], body: str, meta: dict[str, object], has_tasks: bool) -> list[str]:
        tags: list[str] = []

        for key, value in markers:
            tags.append(self._norm_tag(key))
            for token in value.split():
                tags.append(self._norm_tag(token))

        if has_tasks:
            tags.append("task")

        source = meta.get("source")
        if isinstance(source, str) and source:
            tags.append("source")

        for rule in self.config.get("tag_rules", {}).get("regex_mappings", []):
            pattern = rule.get("pattern")
            tag = rule.get("tag")
            if isinstance(pattern, str) and isinstance(tag, str) and re.search(pattern, body, flags=re.IGNORECASE):
                tags.append(self._norm_tag(tag))

        out: list[str] = []
        seen: set[str] = set()
        for t in tags:
            if t and t not in seen:
                out.append(t)
                seen.add(t)
        return out

    @staticmethod
    def _merge_stable_tags(existing: list[str], derived: list[str]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for value in existing + derived:
            normalized = str(value).strip()
            if normalized and normalized not in seen:
                result.append(normalized)
                seen.add(normalized)
        return result

    def _classify(self, note: Note) -> None:
        weights = self.config["classification_weights"]
        scores: Counter[str] = Counter()
        marker_keys = {key for key, _ in note.markers}

        if "person" in marker_keys:
            scores["People"] += weights["person_marker"]
        if {"forschung", "technologie", "research"} & marker_keys:
            scores["Research"] += weights["research_marker"]
        if note.has_tasks:
            scores["Task"] += weights["task_checkbox"]
        if re.search(r"\b(projekt|project|notizen)\b", note.title, flags=re.IGNORECASE):
            scores["Project"] += weights["project_title"]

        src = note.metadata.get("source")
        if isinstance(src, str) and re.search(r"/article|/blog|doi|arxiv", src, flags=re.IGNORECASE):
            scores["Literature"] += weights["literature_source"]

        if re.search(r"\b(chapter|episode|story|szene)\b", note.body, flags=re.IGNORECASE):
            scores["Story"] += weights["story_keywords"]

        if not scores:
            scores["Inbox"] = weights["fallback_inbox"]

        note.classification, note.confidence = max(scores.items(), key=lambda pair: pair[1])

    def _build_title_index(self, notes: list[Note]) -> None:
        for note in notes:
            self.alias_index[note.title.lower()] = note.title
            for alias in note.aliases:
                self.alias_index[alias.lower()] = note.title

    def _insert_links(self, note: Note) -> None:
        protected, placeholders = self._protect_segments(note.body)
        inserted = 0

        for candidate in sorted(self.alias_index.keys(), key=len, reverse=True):
            canonical = self.alias_index[candidate]
            if canonical == note.title:
                continue
            if self._link_confidence(candidate, protected) < self.args.link_min_confidence:
                continue

            regex = re.compile(rf"\b({re.escape(candidate)})\b", flags=re.IGNORECASE)

            def replace(match: re.Match[str]) -> str:
                nonlocal inserted
                if inserted >= self.args.max_links_per_note:
                    return match.group(0)
                inserted += 1
                self.link_report[note.source_path].append(canonical)
                return f"[[{canonical}]]"

            protected = regex.sub(replace, protected)

        note.body = self._restore_segments(protected, placeholders)
        note.links_inserted = inserted

    def _link_confidence(self, candidate: str, text: str) -> float:
        score = 0.0
        if re.search(rf"\b{re.escape(candidate)}\b", text, flags=re.IGNORECASE):
            score += 0.4
        if re.search(rf"^#+\s+{re.escape(candidate)}\b", text, flags=re.IGNORECASE | re.MULTILINE):
            score += 0.2

        count = len(re.findall(rf"\b{re.escape(candidate)}\b", text, flags=re.IGNORECASE))
        if count > 1:
            score += min(0.1, count * 0.03)

        if len(candidate) <= 3 and candidate.upper() not in self.config.get("whitelist_titles", []):
            score -= 0.4
        if candidate.lower() in set(self.config.get("stopwords", [])):
            score -= 0.3

        return max(0.0, min(1.0, score))

    def _protect_segments(self, text: str) -> tuple[str, dict[str, str]]:
        placeholders: dict[str, str] = {}
        protected = text

        def stash(segment: str, prefix: str, index: int) -> str:
            key = f"__{prefix}_{index}__"
            placeholders[key] = segment
            return key

        # fenced code blocks
        lines = protected.splitlines(keepends=True)
        rebuilt: list[str] = []
        in_fence = False
        fence_buf: list[str] = []
        code_idx = 0
        for line in lines:
            if line.strip().startswith("```"):
                fence_buf.append(line)
                if in_fence:
                    rebuilt.append(stash("".join(fence_buf), "CODE", code_idx))
                    code_idx += 1
                    fence_buf = []
                    in_fence = False
                else:
                    in_fence = True
                continue
            if in_fence:
                fence_buf.append(line)
            else:
                rebuilt.append(line)
        if fence_buf:
            rebuilt.extend(fence_buf)
        protected = "".join(rebuilt)

        patterns = [
            (re.compile(r"`[^`]*`"), "INLINE"),
            (re.compile(r"\[\[[^\]]+\]\]"), "WIKI"),
            (re.compile(r"!?\[[^\]]+\]\([^\)]+\)"), "MDLINK"),
        ]

        for pattern, prefix in patterns:
            idx = 0

            def replacer(match: re.Match[str]) -> str:
                nonlocal idx
                key = stash(match.group(0), prefix, idx)
                idx += 1
                return key

            protected = pattern.sub(replacer, protected)

        return protected, placeholders

    @staticmethod
    def _restore_segments(text: str, placeholders: dict[str, str]) -> str:
        restored = text
        for key, value in placeholders.items():
            restored = restored.replace(key, value)
        return restored

    def _compose(self, note: Note) -> str:
        frontmatter: dict[str, object] = {
            "title": note.title,
            "tags": note.tags,
            "evernote": {
                "original_filename": note.original_filename,
                "export_format": "markdown",
            },
            "classification": {
                "type": note.classification,
                "confidence": round(note.confidence, 2),
            },
        }

        for key in ("created", "updated", "source"):
            value = note.metadata.get(key)
            if isinstance(value, str) and value:
                frontmatter[key] = value

        if note.aliases:
            frontmatter["aliases"] = note.aliases

        header = yaml_dump(frontmatter).strip()
        body = note.body.strip() + "\n"

        if self.config.get("inline_tags") and note.tags:
            body += "\n" + " ".join(f"#{tag}" for tag in note.tags) + "\n"

        return f"---\n{header}\n---\n\n{body}"

    def _rewrite_attachments(self, note: Note, text: str, output_dir: Path) -> tuple[str, int]:
        moved = 0
        resources_name = self.args.resources_dir_name
        attachments_dir = self.args.attachments_dir

        def rewrite(match: re.Match[str]) -> str:
            nonlocal moved
            target_raw = match.group(1).strip()
            if resources_name not in target_raw:
                return match.group(0)

            source_file = (note.source_path.parent / target_raw).resolve()
            if not source_file.is_file():
                return match.group(0)

            dest_root = output_dir / attachments_dir
            dest_root.mkdir(parents=True, exist_ok=True)
            dest_file = self._unique_attachment_path(dest_root, source_file.name, source_file)

            if not self.args.dry_run and (not dest_file.exists() or dest_file.read_bytes() != source_file.read_bytes()):
                shutil.copy2(source_file, dest_file)

            moved += 1
            rel = f"{attachments_dir}/{dest_file.name}"
            is_image = dest_file.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}

            if is_image and self.config.get("prefer_wikilink_embeds", True):
                return f"![[{rel}]]"

            prefix = "!" if match.group(0).startswith("!") else ""
            return f"{prefix}[]({rel})"

        return MARKDOWN_LINK_RE.sub(rewrite, text), moved

    def _unique_attachment_path(self, dest_dir: Path, filename: str, source_file: Path) -> Path:
        candidate = dest_dir / filename
        if not candidate.exists():
            return candidate

        try:
            if candidate.read_bytes() == source_file.read_bytes():
                return candidate
        except OSError:
            pass

        stem = Path(filename).stem
        suffix = Path(filename).suffix
        digest = hashlib.sha1(str(source_file).encode("utf-8")).hexdigest()[:8]
        return dest_dir / f"{stem}-{digest}{suffix}"

    def _next_safe_filename(self, folder: Path, title: str) -> str:
        safe = sanitize_filename(title)
        candidate = folder / safe
        n = 2
        while candidate in self.used_filenames:
            candidate = folder / f"{safe} ({n})"
            n += 1
        self.used_filenames.add(candidate)
        return candidate.name

    @staticmethod
    def _write_log(output_dir: Path, entries: list[dict[str, object]]) -> None:
        logs_dir = output_dir / "_logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        with (logs_dir / "transform.jsonl").open("w", encoding="utf-8") as fh:
            for row in entries:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    @staticmethod
    def _stats(notes: Iterable[Note]) -> dict[str, object]:
        collected = list(notes)
        return {
            "notes_total": len(collected),
            "links_inserted_total": sum(note.links_inserted for note in collected),
            "attachments_moved_total": sum(note.attachments_moved for note in collected),
            "by_classification": dict(Counter(note.classification for note in collected)),
        }

    @staticmethod
    def _norm_tag(value: str) -> str:
        normalized = value.strip().lower()
        for src, dst in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
            normalized = normalized.replace(src, dst)
        normalized = re.sub(r"[^a-z0-9\s-]", "", normalized)
        normalized = re.sub(r"\s+", "-", normalized)
        normalized = re.sub(r"-+", "-", normalized)
        return normalized.strip("-")


def sanitize_filename(title: str, max_len: int = 120) -> str:
    sanitized = re.sub(r"[\\/:*?\"<>|]", " ", title)
    sanitized = re.sub(r"\s+", " ", sanitized).strip()
    return (sanitized[:max_len].rstrip() or "Untitled")


def yaml_load(text: str) -> dict[str, object]:
    if yaml is not None:
        return yaml.safe_load(text) or {}

    # Lightweight parser for simple mapping/list config and frontmatter structures.
    result: dict[str, object] = {}
    stack: list[tuple[int, object]] = [(-1, result)]

    def parse_scalar(raw: str) -> object:
        value = raw.strip()
        if value in {"true", "false", "True", "False"}:
            return value.lower() == "true"
        if re.fullmatch(r"-?\d+", value):
            return int(value)
        if re.fullmatch(r"-?\d+\.\d+", value):
            return float(value)
        if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
            return value[1:-1]
        return value

    lines = [ln.rstrip("\n") for ln in text.splitlines() if ln.strip() and not ln.strip().startswith("#")]
    for line in lines:
        indent = len(line) - len(line.lstrip(" "))
        while len(stack) > 1 and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        token = line.strip()

        if token.startswith("- "):
            if isinstance(parent, list):
                parent.append(parse_scalar(token[2:]))
            continue

        if ":" not in token or not isinstance(parent, dict):
            continue

        key, raw_value = token.split(":", 1)
        key = key.strip()
        raw_value = raw_value.strip()

        if raw_value == "":
            container: object = {}
            parent[key] = container
            stack.append((indent, container))
        elif raw_value.startswith("[") and raw_value.endswith("]"):
            inside = raw_value[1:-1].strip()
            if not inside:
                parent[key] = []
            else:
                parent[key] = [parse_scalar(part.strip()) for part in inside.split(",")]
        else:
            parent[key] = parse_scalar(raw_value)

    # best effort list conversion for known keys
    for k in ("tags", "aliases", "stopwords", "whitelist_titles", "regex_mappings"):
        if k in result and isinstance(result[k], dict) and not result[k]:
            result[k] = []

    return result


def yaml_dump(data: dict[str, object]) -> str:
    if yaml is not None:
        return yaml.safe_dump(data, sort_keys=False, allow_unicode=True)

    def dump(value: object, indent: int = 0) -> str:
        pad = " " * indent
        if isinstance(value, dict):
            lines: list[str] = []
            for k, v in value.items():
                if isinstance(v, (dict, list)):
                    lines.append(f"{pad}{k}:")
                    lines.append(dump(v, indent + 2))
                else:
                    scalar = dump(v, 0).strip()
                    lines.append(f"{pad}{k}: {scalar}")
            return "\n".join(lines)
        if isinstance(value, list):
            return "\n".join(f"{pad}- {dump(v, 0).strip()}" for v in value)
        if isinstance(value, str):
            if re.search(r"[:#\-\[\]{}]", value) or value[:1].isdigit() or not value:
                return f"'{value}'"
            return value
        return str(value)

    return dump(data) + "\n"


def load_config(path: Path | None, args: argparse.Namespace) -> dict[str, object]:
    base = json.loads(json.dumps(DEFAULT_CONFIG))

    if not path:
        auto = Path("config.yaml")
        path = auto if auto.exists() else None

    if path and path.exists():
        overrides = yaml_load(path.read_text(encoding="utf-8")) or {}
        if isinstance(overrides, dict):
            deep_update(base, overrides)

    base["attachments_dir"] = args.attachments_dir or base["attachments_dir"]
    base["resources_dir_name"] = args.resources_dir_name or base["resources_dir_name"]

    return base


def deep_update(base: dict[str, object], override: dict[str, object]) -> None:
    for key, value in override.items():
        if isinstance(base.get(key), dict) and isinstance(value, dict):
            deep_update(base[key], value)
        else:
            base[key] = value
