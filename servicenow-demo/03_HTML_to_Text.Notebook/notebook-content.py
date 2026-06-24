# Fabric notebook source

# CELL ********************

"""Fabric notebook helpers for HTML-to-text normalization."""

# ## Notebook purpose
# This notebook contains reusable text-cleaning helpers for the ServiceNow pipeline.
# It supports the curated transform stage by turning HTML-rich notes and article content
# into readable plain text that can be indexed, searched, and displayed cleanly.

from __future__ import annotations

import html
import re
from html.parser import HTMLParser
from typing import Optional

from pyspark.sql import SparkSession
from pyspark.sql.functions import udf
from pyspark.sql.types import StringType

# ## Define which HTML tags should create line breaks in the cleaned output
# These tags represent block-like content, so the parser treats them as places where
# readable plain text should start a new line.
BLOCK_TAG_BREAKS = {
    "br",
    "div",
    "li",
    "ol",
    "p",
    "section",
    "table",
    "tbody",
    "td",
    "th",
    "thead",
    "tr",
    "ul",
}


class _HtmlToTextParser(HTMLParser):
    """Collect readable text from HTML while skipping script and style content."""
    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self._parts: list[str] = []
        self._suppress_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[override]
        normalized_tag = tag.lower()
        if normalized_tag in {"script", "style"}:
            self._suppress_depth += 1
            return
        if self._suppress_depth == 0 and normalized_tag in BLOCK_TAG_BREAKS:
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:  # type: ignore[override]
        normalized_tag = tag.lower()
        if normalized_tag in {"script", "style"} and self._suppress_depth > 0:
            self._suppress_depth -= 1
            return
        if self._suppress_depth == 0 and normalized_tag in BLOCK_TAG_BREAKS:
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:  # type: ignore[override]
        if self._suppress_depth == 0 and data:
            self._parts.append(data)

    def handle_entityref(self, name: str) -> None:  # type: ignore[override]
        if self._suppress_depth == 0:
            self._parts.append(f"&{name};")

    def handle_charref(self, name: str) -> None:  # type: ignore[override]
        if self._suppress_depth == 0:
            self._parts.append(f"&#{name};")

    def get_text(self) -> str:
        return "".join(self._parts)


def normalize_whitespace(value: Optional[str]) -> Optional[str]:
    """Clean up repeated spaces and blank lines in a text string."""
    if value is None:
        return None
    normalized = value.replace("\r", "\n")
    normalized = re.sub(r"\n\s*\n+", "\n\n", normalized)
    normalized = re.sub(r"[ \t]+", " ", normalized)
    normalized = re.sub(r" *\n *", "\n", normalized)
    normalized = normalized.strip()
    return normalized or None


def clean_plain_text(value: Optional[str]) -> Optional[str]:
    """Decode entities in plain text and normalize the final spacing."""
    if value is None:
        return None
    return normalize_whitespace(html.unescape(value))


def clean_html_to_text(value: Optional[str]) -> Optional[str]:
    """Convert HTML to readable text and then normalize the result."""
    if value is None:
        return None

    parser = _HtmlToTextParser()
    parser.feed(value)
    parser.close()
    return clean_plain_text(parser.get_text())


def clean_field(html_value: Optional[str], plain_text_value: Optional[str] = None) -> Optional[str]:
    """Return the cleaned HTML version when present, else fall back to plain text."""
    cleaned_html = clean_html_to_text(html_value)
    if cleaned_html:
        return cleaned_html
    return clean_plain_text(plain_text_value)


def register_html_cleaning_udfs(spark: SparkSession) -> None:
    """Register Spark UDFs so other notebooks can call the text cleaners in SQL expressions."""
    spark.udf.register("clean_html_to_text", udf(clean_html_to_text, StringType()))
    spark.udf.register("clean_plain_text", udf(clean_plain_text, StringType()))
    spark.udf.register(
        "clean_field",
        udf(lambda html_value, plain_text_value: clean_field(html_value, plain_text_value), StringType()),
    )


# ## Register the helper functions automatically inside a live Fabric Spark session
# This makes the UDFs immediately available when the notebook is attached to Spark.
if "spark" in globals():
    register_html_cleaning_udfs(spark)  # type: ignore[name-defined]

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
