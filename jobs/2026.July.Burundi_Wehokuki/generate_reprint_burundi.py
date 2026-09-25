#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_reprint_burundi.py
===========================

Reprint-database generator for the Burundi WEHOKUKI style layout.

This layout is different from the multi-channel games:
  * Single-channel data file - ONE record is ONE card (21 columns:
    PageNo, SerialNo, VIRN, SystemPrizeCode, PrizePrintCode, Play1-6,
    Agent_ValCode1-9, QA_SampleCode). There is NO barcode column.
  * Serial format is GG-BBBBB-TTT (game-book-ticket), e.g. 02-00107-001.
    VOID serial is 88-88888-888 and VOID VIRN is 88888888 (8 digits).
  * A book is 100 tickets (TTT 001..100).
  * The cards are PRINTED in 7 channels, 56 cards per page. In the single-column
    data file this is expressed purely through the ORDER of the records.

Reprint ordering (verified against the reference reprint file):
  1. Read the book numbers to reprint (5-digit) and sort them.
  2. Deal them across 7 channels in BANDS: each band is 35 books - 5 consecutive
     books per channel (books 0-4 -> ch1, 5-9 -> ch2, ... 30-34 -> ch7).
  3. Within a band there are 5 "sub-bands" (a = 0..4). Sub-band a takes one book
     from each channel: the book at index  base + channel*5 + a.
  4. For each sub-band's 7 books, emit tickets interleaved across the channels:
        for ticket t in 1..100:
            for channel in 1..7:
                emit ticket t of that channel's book
     If a channel has no book (the final partial band), a VOID card is emitted in
     that slot so the 7-wide channel structure is preserved.

VOID / make-ready:
  * The first 40 pages are leading make-ready, copied exactly from the layout's
    own leading VOID rows.
  * The VOID slots in the final partial band, the part-page filler, and the 10
    trailing make-ready pages are filled from the layout's VOID rows.

Every real card's data (VIRN, prize codes, play symbols, agent codes, QA) is
copied from the layout, looked up by serial number.
"""

import csv
import glob
import os
import sys


# ----------------------------------------------------------------------------
# CONFIG
# ----------------------------------------------------------------------------
NUM_CHANNELS        = 7          # cards are printed across 7 channels
BOOKS_PER_CHAN_BAND = 5          # consecutive books each channel gets per band
ROWS_PER_PAGE       = 56         # 56 cards per page (single-channel file)
TICKETS_PER_BOOK    = 100        # TTT 001..100

LEADING_VOID_PAGES  = 40
TRAILING_VOID_PAGES = 10

NUM_COLUMNS         = 21         # PageNo + 20 data columns (no barcode)
SERIAL_COL          = 1          # SerialNo is column index 1
PAGENO_WIDTH        = 6

VOID_SERIAL         = "88-88888-888"
VOID_VIRN           = "88888888"
VOID_VIRN_COL       = 2          # VIRN is column index 2

GAME_PREFIX         = "02"       # GG in GG-BBBBB-TTT (WEHOKUKI game 02)

BAND_SIZE = NUM_CHANNELS * BOOKS_PER_CHAN_BAND      # 35 books per band


# ----------------------------------------------------------------------------
# 1. Reading the reprint list (.ods) - stdlib only
# ----------------------------------------------------------------------------
import zipfile
import xml.etree.ElementTree as ET

_ODS_NS = {
    "table":  "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
    "text":   "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
}


def _cell_text(cell):
    return "".join(t.text or "" for t in cell.iter("{%s}p" % _ODS_NS["text"])).strip()


def read_reprint_books(ods_path):
    """
    Return a sorted list of 5-digit book numbers to reprint.
    Column A holds the book numbers from a few header rows down; we simply keep
    every value that is exactly 5 digits.
    """
    with zipfile.ZipFile(ods_path) as z:
        root = ET.fromstring(z.read("content.xml"))
    books = []
    for row in root.iter("{%s}table-row" % _ODS_NS["table"]):
        cells = row.findall("{%s}table-cell" % _ODS_NS["table"])
        if not cells:
            continue
        v = _cell_text(cells[0])
        if v.isdigit() and len(v) == 5:
            books.append(v)
    return sorted(set(books))


# ----------------------------------------------------------------------------
# 2. Book distribution -> ordered list of "slots" (serial or None for VOID)
# ----------------------------------------------------------------------------
def build_slot_sequence(books):
    """
    Turn the sorted book list into the full ordered sequence of card slots.
    Each slot is a serial string, or None where a channel has no book (VOID).
    """
    n = len(books)
    n_bands = (n + BAND_SIZE - 1) // BAND_SIZE
    slots = []
    for band in range(n_bands):
        base = band * BAND_SIZE
        for a in range(BOOKS_PER_CHAN_BAND):
            row_books = []
            for ch in range(NUM_CHANNELS):
                idx = base + ch * BOOKS_PER_CHAN_BAND + a
                row_books.append(books[idx] if idx < n else None)
            if all(b is None for b in row_books):
                continue
            for t in range(1, TICKETS_PER_BOOK + 1):
                for bk in row_books:
                    slots.append("%s-%s-%03d" % (GAME_PREFIX, bk, t) if bk else None)
    return slots


# ----------------------------------------------------------------------------
# 3. Reading the layout (delimiter auto-detected)
# ----------------------------------------------------------------------------
def detect_delimiter(path):
    with open(path, encoding="utf-8", newline="") as f:
        sample = f.read(8192)
    return "\t" if sample.count("\t") > sample.count(",") else ","


def load_layout(path, needed_serials, leading_void_needed):
    """
    Stream the layout once and pull out:
      serial_block   : dict serial -> full data row (21 cols, incl PageNo slot 0
                       replaced later) for needed serials
      leading_void   : the first `leading_void_needed` VOID rows, in order
                       (copied verbatim for the leading make-ready pages)
      void_pool      : all VOID rows (data columns), for filler
    """
    delim = detect_delimiter(path)
    serial_block = {}
    leading_void = []
    void_pool = []
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.reader(f, delimiter=delim)
        next(reader, None)
        for row in reader:
            if len(row) < NUM_COLUMNS:
                continue
            serial = row[SERIAL_COL]
            data = row[1:NUM_COLUMNS]                 # 20 data cols (drop PageNo)
            if serial == VOID_SERIAL:
                if len(leading_void) < leading_void_needed:
                    leading_void.append(data)
                void_pool.append(data)
            elif serial in needed_serials and serial not in serial_block:
                serial_block[serial] = data
    return serial_block, leading_void, void_pool


# ----------------------------------------------------------------------------
# 4. Building the output rows
# ----------------------------------------------------------------------------
def _void_data(pool_block):
    """A VOID data row (20 cols): fixed serial/VIRN, make-ready codes from pool."""
    block = list(pool_block)
    block[SERIAL_COL - 1] = VOID_SERIAL          # data is offset by 1 (no PageNo)
    block[VOID_VIRN_COL - 1] = VOID_VIRN
    return block


def build_output_rows(slots, serial_block, leading_void, void_pool):
    if not void_pool:
        raise SystemExit("ERROR: no VOID rows found in layout.")

    cur = {"i": 0}

    def next_void():
        b = void_pool[cur["i"] % len(void_pool)]
        cur["i"] += 1
        return _void_data(b)

    rows = []                                      # each row = 20 data cols
    missing = set()

    # (a) leading make-ready: exact copy of the layout's leading VOID rows
    lead_target = LEADING_VOID_PAGES * ROWS_PER_PAGE
    for k in range(lead_target):
        rows.append(list(leading_void[k]) if k < len(leading_void) else next_void())

    # (b) the interleaved data slots (real cards + VOID where a channel is empty)
    for s in slots:
        if s is None:
            rows.append(next_void())
        else:
            block = serial_block.get(s)
            if block is None:
                missing.add(s)
                block = _fallback(s)
            rows.append(list(block))

    # (c) finish the last part-page with VOID
    while len(rows) % ROWS_PER_PAGE != 0:
        rows.append(next_void())

    # (d) trailing make-ready pages
    for _ in range(TRAILING_VOID_PAGES * ROWS_PER_PAGE):
        rows.append(next_void())

    # (e) prepend sequential PageNo
    out = []
    for idx, data in enumerate(rows):
        page = str(idx // ROWS_PER_PAGE + 1).zfill(PAGENO_WIDTH)
        out.append([page] + data)
    return out, missing


def _fallback(serial):
    block = [serial, "", "99"] + [" "] * (NUM_COLUMNS - 1 - 4) + ["$"]
    return block[:NUM_COLUMNS - 1]


# ----------------------------------------------------------------------------
# 5. Header + writing
# ----------------------------------------------------------------------------
def build_header(layout_path):
    delim = detect_delimiter(layout_path)
    with open(layout_path, encoding="utf-8", newline="") as f:
        return next(csv.reader(f, delimiter=delim))


def write_csv(path, header, rows):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


# ----------------------------------------------------------------------------
# 6. Non-interactive entry point + CLI
# ----------------------------------------------------------------------------
def run_generation(layout_path, ods_path, output_path):
    books = read_reprint_books(ods_path)
    slots = build_slot_sequence(books)
    needed = {s for s in slots if s}

    lead_target = LEADING_VOID_PAGES * ROWS_PER_PAGE
    serial_block, leading_void, void_pool = load_layout(layout_path, needed, lead_target)

    rows, missing = build_output_rows(slots, serial_block, leading_void, void_pool)
    header = build_header(layout_path)
    write_csv(output_path, header, rows)
    return {
        "output_path": output_path,
        "books": len(books),
        "real_cards": len(needed),
        "rows": len(rows),
        "pages": len(rows) // ROWS_PER_PAGE,
        "columns": len(header),
        "missing": len(missing),
    }


def main():
    folder = os.getcwd()
    layouts = sorted(glob.glob(os.path.join(folder, "*LAYOUT*.TXT")) +
                     glob.glob(os.path.join(folder, "*LAYOUT*.txt")))
    ods = sorted(glob.glob(os.path.join(folder, "*.ods")))
    if not layouts:
        sys.exit("No *LAYOUT*.TXT found in %s" % folder)
    if not ods:
        sys.exit("No .ods reprint list found in %s" % folder)

    layout_path = layouts[0] if len(layouts) == 1 else _pick(layouts, "layout file")
    ods_path = ods[0] if len(ods) == 1 else _pick(ods, "reprint list")

    out = os.path.join(folder, "BURUNDI_REPRINT_DATABASE.csv")
    info = run_generation(layout_path, ods_path, out)
    print("Done.")
    print("  books        :", info["books"])
    print("  real cards   :", info["real_cards"])
    print("  rows / pages :", info["rows"], "/", info["pages"])
    print("  columns      :", info["columns"])
    print("  output       :", info["output_path"])
    if info["missing"]:
        print("  WARNING: %d serials not found in layout." % info["missing"])


def _pick(options, label):
    print("Choose the %s:" % label)
    for i, o in enumerate(options, 1):
        print("  %d) %s" % (i, os.path.basename(o)))
    while True:
        c = input("Enter number: ").strip()
        if c.isdigit() and 1 <= int(c) <= len(options):
            return options[int(c) - 1]


if __name__ == "__main__":
    main()
