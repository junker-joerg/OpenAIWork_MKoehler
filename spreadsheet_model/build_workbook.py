#!/usr/bin/env python3
"""Erzeugt ein einzelnes XLSX-Workbook mit Arbeitsblättern aus CSV/MD-Assets.

Keine externen Pakete notwendig (nur Python-Standardbibliothek).
"""

from __future__ import annotations

import csv
import datetime as dt
import html
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

BASE = Path(__file__).resolve().parent
OUT = BASE / "hyperion_spreadsheet_model.xlsx"

SHEETS = [
    ("Parameters", BASE / "00_parameters.csv"),
    ("Goods", BASE / "01_goods.csv"),
    ("Worlds", BASE / "02_worlds.csv"),
    ("Profiles", BASE / "03_profiles.csv"),
    ("Events", BASE / "04_events_table.csv"),
]


def col_name(idx: int) -> str:
    letters = ""
    idx += 1
    while idx:
        idx, rem = divmod(idx - 1, 26)
        letters = chr(65 + rem) + letters
    return letters


def parse_csv(path: Path) -> list[list[str]]:
    with path.open(newline="", encoding="utf-8") as fh:
        return [row for row in csv.reader(fh)]


def parse_guide(path: Path) -> list[list[str]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    rows = [["line", "text"]]
    for i, line in enumerate(lines, start=1):
        rows.append([str(i), line])
    return rows


def xml_cell(r: int, c: int, value: str) -> str:
    ref = f"{col_name(c)}{r}"
    if value == "":
        return f'<c r="{ref}"/>'

    is_number = False
    try:
        float(value)
        is_number = value.replace(".", "", 1).replace("-", "", 1).isdigit()
    except ValueError:
        pass

    if is_number:
        return f'<c r="{ref}"><v>{escape(value)}</v></c>'

    text = escape(value)
    return f'<c r="{ref}" t="inlineStr"><is><t>{text}</t></is></c>'


def sheet_xml(rows: list[list[str]]) -> str:
    if not rows:
        rows = [[""]]
    max_col = max(len(r) for r in rows)
    dim = f"A1:{col_name(max_col - 1)}{len(rows)}"

    row_xml = []
    for r_idx, row in enumerate(rows, start=1):
        cells = [xml_cell(r_idx, c_idx, row[c_idx] if c_idx < len(row) else "") for c_idx in range(max_col)]
        row_xml.append(f'<row r="{r_idx}">{"".join(cells)}</row>')

    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<dimension ref="{dim}"/>'
        '<sheetViews><sheetView workbookViewId="0"/></sheetViews>'
        '<sheetFormatPr defaultRowHeight="15"/>'
        f'<sheetData>{"".join(row_xml)}</sheetData>'
        '</worksheet>'
    )


def build() -> None:
    data_sheets: list[tuple[str, list[list[str]]]] = [(name, parse_csv(path)) for name, path in SHEETS]
    data_sheets.append(("Guide", parse_guide(BASE / "SPREADSHEET_GUIDE.md")))

    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    workbook_sheets = "".join(
        f'<sheet name="{escape(name)}" sheetId="{i}" r:id="rId{i}"/>'
        for i, (name, _) in enumerate(data_sheets, start=1)
    )

    workbook_rels = "".join(
        f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>'
        for i in range(1, len(data_sheets) + 1)
    ) + '<Relationship Id="rId999" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'

    content_types_overrides = "".join(
        f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        for i in range(1, len(data_sheets) + 1)
    )

    with zipfile.ZipFile(OUT, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "[Content_Types].xml",
            (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                '<Default Extension="xml" ContentType="application/xml"/>'
                '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
                '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
                '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
                '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>'
                f'{content_types_overrides}'
                '</Types>'
            ),
        )
        zf.writestr(
            "_rels/.rels",
            (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
                '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
                '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>'
                '</Relationships>'
            ),
        )
        zf.writestr(
            "docProps/core.xml",
            (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
                'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
                'xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
                '<dc:creator>Codex</dc:creator>'
                '<cp:lastModifiedBy>Codex</cp:lastModifiedBy>'
                f'<dcterms:created xsi:type="dcterms:W3CDTF">{now}</dcterms:created>'
                f'<dcterms:modified xsi:type="dcterms:W3CDTF">{now}</dcterms:modified>'
                '</cp:coreProperties>'
            ),
        )
        zf.writestr(
            "docProps/app.xml",
            (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" '
                'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">'
                '<Application>Spreadsheet Model Builder</Application>'
                '</Properties>'
            ),
        )
        zf.writestr(
            "xl/workbook.xml",
            (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                '<bookViews><workbookView/></bookViews>'
                f'<sheets>{workbook_sheets}</sheets>'
                '</workbook>'
            ),
        )
        zf.writestr(
            "xl/_rels/workbook.xml.rels",
            (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                f'{workbook_rels}'
                '</Relationships>'
            ),
        )
        zf.writestr(
            "xl/styles.xml",
            (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                '<fonts count="1"><font><sz val="11"/><name val="Calibri"/></font></fonts>'
                '<fills count="1"><fill><patternFill patternType="none"/></fill></fills>'
                '<borders count="1"><border/></borders>'
                '<cellStyleXfs count="1"><xf/></cellStyleXfs>'
                '<cellXfs count="1"><xf xfId="0"/></cellXfs>'
                '</styleSheet>'
            ),
        )

        for i, (_, rows) in enumerate(data_sheets, start=1):
            zf.writestr(f"xl/worksheets/sheet{i}.xml", sheet_xml(rows))


if __name__ == "__main__":
    build()
