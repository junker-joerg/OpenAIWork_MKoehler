# ever2obsidian

Production-ready CLI tool to transform Evernote-exported Markdown into clean Obsidian notes.

## Features

- Evernote metadata extraction into YAML frontmatter.
- Cleanup of Evernote artifacts (comments, markers, decorative trailing symbols).
- Configurable marker-to-tag mapping and note classification.
- Automatic wikilink insertion with confidence scoring and protected zones.
- Attachment/resource relocation and link rewriting.
- Deterministic/idempotent output.
- JSONL transformation logs and optional summary statistics.

## Installation

```bash
pip install -e .
```

## CLI

```bash
ever2obsidian --input <dir> --output <dir> [options]
```

Options:

- `--config <path_to_yaml>`
- `--attachments-dir <relative_path>` (default: `attachments`)
- `--resources-dir-name <name>` (default: `_resources`)
- `--dry-run`
- `--verbose`
- `--stats`
- `--no-linking`
- `--no-classify`
- `--no-tagging`
- `--link-min-confidence <0..1>` (default: `0.65`)
- `--max-links-per-note <int>` (default: `200`)
- `--exclude <glob>` (repeatable)
- `--include <glob>` (repeatable)

Exit codes:

- `0` success
- non-zero fatal errors

## Example

```bash
ever2obsidian \
  --input ./evernote-export \
  --output ./obsidian-vault \
  --config ./config.yaml \
  --stats
```

## Output

- Notes are written to classified folders:
  - `People/`, `Research/`, `Projects/`, `Tasks/`, `Literature/`, `Story/`, `Inbox/`, `Other/`
- Attachments are copied to `<output>/attachments/` (configurable)
- Logs are written to `<output>/_logs/transform.jsonl`

## Configuration

Copy and adapt `config.example.yaml`.

```yaml
attachments_dir: attachments
resources_dir_name: _resources
prefer_wikilink_embeds: true
keep_meta_section: false
inline_tags: false
folder_map:
  People: People
  Research: Research
  Project: Projects
  Task: Tasks
  Literature: Literature
  Story: Story
  Inbox: Inbox
  Other: Other
classification_weights:
  person_marker: 0.7
  research_marker: 0.7
  task_checkbox: 0.6
  project_title: 0.6
  literature_source: 0.65
  story_keywords: 0.6
  fallback_inbox: 0.45
stopwords: [and, the, und, oder, der, die, das]
whitelist_titles: [AI, ML, UX]
tag_rules:
  regex_mappings:
    - pattern: "\\bpython\\b"
      tag: python
```

## Testing

```bash
pytest -q
```
