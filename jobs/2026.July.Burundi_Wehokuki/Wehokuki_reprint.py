#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_reprint.py
===================
Extracts required reprint tickets from a master layout file to match 
the original vertical format.
"""

import csv
import glob
import os
import sys
import zipfile
import xml.etree.ElementTree as ET

# --- CONFIGURATION MATCHING YOUR LAYOUT ---
SERIAL_LEN = 12
TICKETS_PER_BOOK = 100
SERIAL_COL_INDEX = 1        # SerialNo1_01 is in Column 2 (Index 1)
VOID_SERIAL = "88-88888-888"

_ODS_NS = {
    "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
    "text":  "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
}

def _ods_cell_text(cell):
    parts = [t.text or "" for t in cell.iter("{%s}p" % _ODS_NS["text"])]
    return "".join(parts).strip()

def read_reprint_list(ods_path):
    with zipfile.ZipFile(ods_path) as z:
        xml_bytes = z.read("content.xml")
    root = ET.fromstring(xml_bytes)

    serials = []
    for row in root.iter("{%s}table-row" % _ODS_NS["table"]):
        cells = row.findall("{%s}table-cell" % _ODS_NS["table"])
        if not cells: 
            continue
        value = _ods_cell_text(cells[0])
        if not value: 
            continue
        
        # Look for standard 12-character serials (e.g., 02-00001-001)
        if len(value) == SERIAL_LEN and value.replace("-", "").isdigit():
            serials.append(value)
    return serials

def expand_book(first_serial):
    """Generates all 100 serial numbers for a given book."""
    prefix = first_serial[:-3]
    start = int(first_serial[-3:])
    return [f"{prefix}{str(start + i).zfill(3)}" for i in range(TICKETS_PER_BOOK)]

def detect_delimiter(path):
    with open(path, encoding="utf-8", newline="") as f:
        sample = f.read(8192)
    return "\t" if sample.count("\t") > sample.count(",") else ","

def main():
    print("=" * 60)
    print("  Reprint Database Extractor")
    print("=" * 60)

    folder = os.getcwd()
    layout_files = sorted(glob.glob(os.path.join(folder, "*LAYOUT*.TXT")) + 
                          glob.glob(os.path.join(folder, "*LAYOUT*.txt")))
    ods_files = sorted(glob.glob(os.path.join(folder, "*.ods")))

    if not layout_files:
        sys.exit("ERROR: No '*LAYOUT*.TXT' file found in this folder.")
    if not ods_files:
        sys.exit("ERROR: No '.ods' reprint list found in this folder.")

    layout_path = layout_files[0]
    ods_path = ods_files[0]
    print(f"Layout File  : {os.path.basename(layout_path)}")
    print(f"Reprint List : {os.path.basename(ods_path)}")

    # 1. Parse initial serial numbers from ODS
    book_serials = read_reprint_list(ods_path)
    print(f"\nFound {len(book_serials)} books to reprint.")

    # 2. Expand each book into 100 ticket serial numbers
    needed_serials = []
    for bs in book_serials:
        needed_serials.extend(expand_book(bs))
    print(f"Total ticket rows to extract: {len(needed_serials)}")

    # 3. Read the layout file and map serial numbers to full row data
    print("\nReading master layout...")
    delim = detect_delimiter(layout_path)
    layout_data = {}
    header = None

    with open(layout_path, encoding="utf-8", newline="") as f:
        reader = csv.reader(f, delimiter=delim)
        for i, row in enumerate(reader):
            if not row:
                continue
            
            # Identify header by looking for 'SerialNo' or non-numeric serial column
            if i == 0 and ("SerialNo" in row[SERIAL_COL_INDEX] or not row[SERIAL_COL_INDEX].replace("-", "").isdigit()):
                header = row
                continue
            
            if len(row) > SERIAL_COL_INDEX:
                serial = row[SERIAL_COL_INDEX].strip()
                # Store row data for requested serials
                if serial in needed_serials and serial not in layout_data:
                    layout_data[serial] = row

    # 4. Write output matching the exact structure of the layout file
    out_name = "REPRINT_DATABASE.csv"
    out_path = os.path.join(folder, out_name)
    
    missing_count = 0
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        if header:
            writer.writerow(header)
            
        for serial in needed_serials:
            if serial in layout_data:
                writer.writerow(layout_data[serial])
            else:
                missing_count += 1
                # Fallback blank row if a serial isn't found in master layout
                writer.writerow([""] + [serial] + [""] * 19)

    print("\nExtraction Complete.")
    print(f"Output File : {out_path}")
    print(f"Total Rows  : {len(needed_serials)}")
    if missing_count > 0:
        print(f"WARNING: {missing_count} ticket serials were not found in the layout file!")

if __name__ == "__main__":
    main()