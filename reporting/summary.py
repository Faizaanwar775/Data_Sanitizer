
from __future__ import annotations

import logging
from typing import List

logger = logging.getLogger("datasanitizer.reporting.summary")


def log_summary(
    rows_read: int,
    exact_duplicates_removed: int,
    rejected_count: int,
    near_duplicates_removed: int,
    final_written: int,
    duplicate_examples: List[dict],
) -> None:
    
    cleaned_ok = rows_read - exact_duplicates_removed - rejected_count

    logger.info("=== Post-Run Summary ===")
    logger.info("Rows read (raw input):              %d", rows_read)
    logger.info("Exact duplicate rows removed:        %d", exact_duplicates_removed)
    logger.info("Rows rejected (failed cleaning):     %d", rejected_count)
    logger.info("Rows cleaned successfully:           %d", cleaned_ok)
    logger.info("  of which near-duplicates removed:  %d", near_duplicates_removed)
    logger.info("Final rows written to clean output:  %d", final_written)
    logger.info(
        "Reconciliation check: %d (read) = %d (exact dup) + %d (rejected) "
        "+ %d (near dup) + %d (final written) -> %s",
        rows_read,
        exact_duplicates_removed,
        rejected_count,
        near_duplicates_removed,
        final_written,
        "OK"
        if rows_read
        == exact_duplicates_removed
        + rejected_count
        + near_duplicates_removed
        + final_written
        else "MISMATCH",
    )

    if duplicate_examples:
        logger.info("--- Sample duplicate resolutions (up to %d shown) ---", len(duplicate_examples))
        for i, ex in enumerate(duplicate_examples, start=1):
            logger.info(
                "  [%d] key=%s | existing=%s | incoming=%s | kept=%s",
                i,
                ex["key"],
                ex["existing"],
                ex["incoming"],
                ex["kept"],
            )
