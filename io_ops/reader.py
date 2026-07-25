
from __future__ import annotations

import csv
import logging
from typing import Iterator

logger = logging.getLogger("datasanitizer.io_ops.reader")


def read_raw_rows(path: str) -> Iterator[dict]:
    
    with open(path, newline="", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            logger.warning("Input file %s appears to have no header row.", path)
            return
        for line_number, row in enumerate(reader, start=2):  # header = line 1
            # Guard against short/long rows (csv.DictReader puts overflow
            # values in a None key, and missing columns become None) so a
            # single ragged row never raises deep inside the pipeline.
            row["_source_line"] = line_number
            yield row
