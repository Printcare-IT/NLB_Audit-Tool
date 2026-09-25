#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Turn a specification document (.pdf, .docx or legacy .doc) into plain text.

Both formats are reduced to the same shape so one set of parsers serves both:
  * PDF  -> pdfplumber in layout mode (keeps table rows on one line), falling
            back to the `pdftotext -layout` command if pdfplumber is missing.
  * DOCX -> python-docx, walking paragraphs and tables in document order;
            each table row becomes "| cell | cell |".
  * DOC  -> converted to .docx with LibreOffice first, then as DOCX.

`flatten()` then collapses everything to single-spaced text with markdown
bold markers, table pipes and dash variants normalised, which is the form
the parsers match against.

Requirements (desktop):  pip install pdfplumber python-docx
                         LibreOffice, only if legacy .doc files are used.
"""

import os
import re
import shutil
import subprocess
import tempfile


# ------------------------------------------------------------------ #
#  PDF                                                                #
# ------------------------------------------------------------------ #

def _pdf_text(path):
    try:
        import pdfplumber
        with pdfplumber.open(path) as pdf:
            return "\n".join((p.extract_text(layout=True) or "")
                             for p in pdf.pages)
    except ImportError:
        pass
    exe = shutil.which("pdftotext")
    if not exe:
        raise RuntimeError("Cannot read PDF: install pdfplumber "
                           "(pip install pdfplumber) or poppler's pdftotext.")
    out = subprocess.run([exe, "-layout", path, "-"],
                         capture_output=True, text=True, check=True)
    return out.stdout


# ------------------------------------------------------------------ #
#  DOCX                                                               #
# ------------------------------------------------------------------ #

def _docx_text(path):
    from docx import Document
    from docx.table import Table, _Cell
    from docx.text.paragraph import Paragraph

    doc = Document(path)

    def cell_text(cell):
        # cell.text ignores tables nested inside the cell (NLB specs put the
        # low-tier agent letter in one), so walk the cell's children instead
        parts = []
        for ch in cell._tc.iterchildren():
            t = ch.tag.rsplit("}", 1)[-1]
            if t == "p":
                parts.append(Paragraph(ch, cell).text)
            elif t == "tbl":
                for row in Table(ch, cell).rows:
                    parts.append(" ".join(cell_text(c) for c in _unique(row.cells)))
        return " ".join(" ".join(parts).split())

    def _unique(cells):
        prev = None
        for c in cells:
            if c._tc is prev:      # merged cells repeat the same object
                continue
            prev = c._tc
            yield c

    lines = []
    for child in doc.element.body.iterchildren():
        tag = child.tag.rsplit("}", 1)[-1]
        if tag == "p":
            txt = Paragraph(child, doc).text
            if txt.strip():
                lines.append(txt)
        elif tag == "tbl":
            for row in Table(child, doc).rows:
                lines.append("| " + " | ".join(cell_text(c) for c in _unique(row.cells)) + " |")
    return "\n".join(lines)


# ------------------------------------------------------------------ #
#  Legacy DOC                                                         #
# ------------------------------------------------------------------ #

_SOFFICE_CANDIDATES = [
    "soffice", "libreoffice",
    r"C:\Program Files\LibreOffice\program\soffice.exe",
    r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    "/Applications/LibreOffice.app/Contents/MacOS/soffice",
]


def _find_soffice():
    for c in _SOFFICE_CANDIDATES:
        p = shutil.which(c) or (c if os.path.isfile(c) else None)
        if p:
            return p
    return None


def _doc_to_docx(path):
    out_dir = tempfile.mkdtemp(prefix="doc2docx_")
    # Prefer the sandbox-safe wrapper when it exists (Claude environment);
    # on a normal desktop, call LibreOffice directly.
    wrapper = "/mnt/skills/public/docx/scripts/office/soffice.py"
    if os.path.isfile(wrapper):
        cmd = ["python3", wrapper, "--headless", "--convert-to", "docx",
               "--outdir", out_dir, path]
    else:
        exe = _find_soffice()
        if not exe:
            raise RuntimeError("Cannot convert legacy .doc: LibreOffice not "
                               "found. Install it, or save the file as .docx.")
        cmd = [exe, "--headless", "--convert-to", "docx", "--outdir",
               out_dir, path]
    subprocess.run(cmd, capture_output=True, timeout=300)
    base = os.path.splitext(os.path.basename(path))[0] + ".docx"
    target = os.path.join(out_dir, base)
    if not os.path.isfile(target):
        # some LibreOffice builds ignore --outdir; look beside the source
        alt = os.path.join(os.path.dirname(path), base)
        if os.path.isfile(alt):
            return alt
        raise RuntimeError(f"LibreOffice did not produce {base}")
    return target


# ------------------------------------------------------------------ #
#  Public API                                                         #
# ------------------------------------------------------------------ #

def to_text(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        return _pdf_text(path)
    if ext == ".docx":
        return _docx_text(path)
    if ext == ".doc":
        return _docx_text(_doc_to_docx(path))
    raise ValueError(f"Unsupported document type: {path}")


_DASHES = re.compile(r"[\u2010\u2011\u2012\u2013\u2014\u2015\u2212]")
_QUOTES_D = re.compile(r"[\u201c\u201d\u201e\u00ab\u00bb]")
_QUOTES_S = re.compile(r"[\u2018\u2019\u201a]")


def flatten(text):
    """Single-spaced text with bold markers, table pipes, dash and quote
    variants normalised.  This is what the parsers match against."""
    t = text.replace("**", "")
    t = t.replace("|", " ")
    t = _DASHES.sub("-", t)
    t = _QUOTES_D.sub('"', t)
    t = _QUOTES_S.sub("'", t)
    t = t.replace("\u00a0", " ").replace("\f", " ")
    return re.sub(r"\s+", " ", t).strip()
