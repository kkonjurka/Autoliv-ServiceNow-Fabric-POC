# Fabric notebook source

# CELL ********************

"""Fabric notebook to transform raw landing JSON into curated structured and retrieval tables."""

from __future__ import annotations

import html
import os
import re
from html.parser import HTMLParser
from pathlib import PurePosixPath
from typing import Optional

from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import BooleanType, DoubleType, StringType, StructType
from pyspark.sql.functions import udf

RAW_ROOT = PurePosixPath("Files/raw/servicenow")
TARGET_DATABASE = os.getenv("SERVICENOW_CURATED_DATABASE", "")

# --- Inlined HTML cleaning (from 03_HTML_to_Text) ---

BLOCK_TAG_BREAKS = {
    "br", "div", "li", "ol", "p", "section",
    "table", "tbody", "td", "th", "thead", "tr", "ul",
}


class _HtmlToTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self._parts: list[str] = []
        self._suppress_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        normalized_tag = tag.lower()
        if normalized_tag in {"script", "style"}:
            self._suppress_depth += 1
            return
        if self._suppress_depth == 0 and normalized_tag in BLOCK_TAG_BREAKS:
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        normalized_tag = tag.lower()
        if normalized_tag in {"script", "style"} and self._suppress_depth > 0:
            self._suppress_depth -= 1
            return
        if self._suppress_depth == 0 and normalized_tag in BLOCK_TAG_BREAKS:
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._suppress_depth == 0 and data:
            self._parts.append(data)

    def handle_entityref(self, name: str) -> None:
        if self._suppress_depth == 0:
            self._parts.append(f"&{name};")

    def handle_charref(self, name: str) -> None:
        if self._suppress_depth == 0:
            self._parts.append(f"&#{name};")

    def get_text(self) -> str:
        return "".join(self._parts)


def normalize_whitespace(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    normalized = value.replace("\r", "\n")
    normalized = re.sub(r"\n\s*\n+", "\n\n", normalized)
    normalized = re.sub(r"[ \t]+", " ", normalized)
    normalized = re.sub(r" *\n *", "\n", normalized)
    normalized = normalized.strip()
    return normalized or None


def clean_plain_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    return normalize_whitespace(html.unescape(value))


def clean_html_to_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    parser = _HtmlToTextParser()
    parser.feed(value)
    parser.close()
    return clean_plain_text(parser.get_text())


def clean_field(html_value: Optional[str], plain_text_value: Optional[str] = None) -> Optional[str]:
    cleaned_html = clean_html_to_text(html_value)
    if cleaned_html:
        return cleaned_html
    return clean_plain_text(plain_text_value)


# Register UDFs
spark.udf.register("clean_html_to_text", udf(clean_html_to_text, StringType()))
spark.udf.register("clean_plain_text", udf(clean_plain_text, StringType()))
spark.udf.register("clean_field", udf(lambda h, p: clean_field(h, p), StringType()))


def qualify_table_name(table_name: str) -> str:
    return f"{TARGET_DATABASE}.{table_name}" if TARGET_DATABASE else table_name


def read_json(path: PurePosixPath) -> DataFrame:
    return spark.read.option("multiLine", True).json(str(path))


def write_delta(df: DataFrame, table_name: str) -> None:
    (
        df.write.mode("overwrite")
        .format("delta")
        .option("overwriteSchema", "true")
        .saveAsTable(qualify_table_name(table_name))
    )


def deduplicate(df: DataFrame, keys: list[str]) -> DataFrame:
    return df.dropDuplicates(keys)


incident_detail_raw = read_json(RAW_ROOT / "incidents" / "detail" / "*" / "*.json")
kb_articles_raw = read_json(RAW_ROOT / "kb_articles" / "list" / "*" / "*.json")
attachments_raw = read_json(RAW_ROOT / "attachments" / "list" / "*" / "*.json")
images_raw = read_json(RAW_ROOT / "images" / "list" / "*" / "*.json")
documents_raw = read_json(RAW_ROOT / "documents" / "list" / "*" / "*.json")

incident_details = incident_detail_raw.select(
    "id",
    "number",
    "short_description",
    "description_html",
    "description_text",
    "state",
    "priority",
    "impact",
    "urgency",
    "opened_at",
    "updated_at",
    "resolved_at",
    "follow_up_required",
    "follow_up_reason",
    "resolution_summary_html",
    "resolution_summary_text",
    F.col("requester.id").alias("requester_id"),
    F.col("assignee.id").alias("assignee_id"),
    F.col("assignment_group.id").alias("assignment_group_id"),
    F.col("category.id").alias("category_id"),
    "requester",
    "assignee",
    "assignment_group",
    "category",
    "work_notes",
    "resolution_notes",
    "related_kb_articles",
    "change_requests",
    "slas",
    "attachments",
    "images",
    "documents",
    "external_references",
)

kb_articles = deduplicate(
    kb_articles_raw.select(F.explode("items").alias("item"))
    .select(
        F.col("item.id").alias("kb_article_id"),
        F.col("item.number").alias("kb_article_number"),
        F.col("item.title").alias("title"),
        F.col("item.audience").alias("audience"),
        F.col("item.content_html").alias("content_html"),
        F.expr("clean_field(item.content_html, item.content_text)").alias("content_text_clean"),
        F.array_join(F.col("item.keywords"), ", ").alias("keywords"),
        F.to_timestamp(F.col("item.published_at")).alias("published_at"),
        F.to_timestamp(F.col("item.updated_at")).alias("updated_at"),
        F.col("item.category.id").alias("category_id"),
        F.col("item.category.name").alias("category_name"),
        F.col("item.category.subcategory").alias("category_subcategory"),
    ),
    ["kb_article_id"],
)

incident_kb_articles = (
    incident_details.select("id", F.explode_outer("related_kb_articles").alias("kb"))
    .select(
        F.col("id").alias("incident_id"),
        F.col("kb.id").alias("kb_article_id"),
        F.col("kb.relevance_reason").alias("relevance_reason"),
    )
    .where(F.col("kb_article_id").isNotNull())
)

categories = deduplicate(
    incident_details.select(
        F.col("category.id").alias("category_id"),
        F.col("category.name").alias("name"),
        F.col("category.subcategory").alias("subcategory"),
    ).unionByName(
        kb_articles.select(
            "category_id",
            F.col("category_name").alias("name"),
            F.col("category_subcategory").alias("subcategory"),
        ),
        allowMissingColumns=True,
    ),
    ["category_id"],
)

assignment_groups = deduplicate(
    incident_details.select(
        F.col("assignment_group.id").alias("assignment_group_id"),
        F.col("assignment_group.name").alias("name"),
        F.col("assignment_group.description").alias("description"),
        F.col("assignment_group.escalation_email").alias("escalation_email"),
    ),
    ["assignment_group_id"],
)

requester_users = incident_details.select(
    F.col("requester.id").alias("user_id"),
    F.col("requester.full_name").alias("full_name"),
    F.col("requester.email").alias("email"),
    F.col("requester.title").alias("title"),
    F.col("requester.location").alias("location"),
    F.col("requester.department").alias("department"),
)
assignee_users = incident_details.where(F.col("assignee.id").isNotNull()).select(
    F.col("assignee.id").alias("user_id"),
    F.col("assignee.full_name").alias("full_name"),
    F.col("assignee.email").alias("email"),
    F.col("assignee.title").alias("title"),
    F.col("assignee.location").alias("location"),
    F.col("assignee.department").alias("department"),
)
work_note_users = incident_details.select(F.explode_outer("work_notes").alias("note")).select(
    F.col("note.author.id").alias("user_id"),
    F.col("note.author.full_name").alias("full_name"),
    F.col("note.author.email").alias("email"),
    F.col("note.author.title").alias("title"),
    F.col("note.author.location").alias("location"),
    F.col("note.author.department").alias("department"),
)
resolution_note_users = incident_details.select(F.explode_outer("resolution_notes").alias("note")).select(
    F.col("note.author.id").alias("user_id"),
    F.col("note.author.full_name").alias("full_name"),
    F.col("note.author.email").alias("email"),
    F.col("note.author.title").alias("title"),
    F.col("note.author.location").alias("location"),
    F.col("note.author.department").alias("department"),
)

users = deduplicate(
    requester_users.unionByName(assignee_users)
    .unionByName(work_note_users, allowMissingColumns=True)
    .unionByName(resolution_note_users, allowMissingColumns=True)
    .where(F.col("user_id").isNotNull()),
    ["user_id"],
)

incidents = incident_details.select(
    F.col("id").alias("incident_id"),
    "number",
    "short_description",
    "state",
    "priority",
    "impact",
    "urgency",
    F.to_timestamp("opened_at").alias("opened_at"),
    F.to_timestamp("updated_at").alias("updated_at"),
    F.to_timestamp("resolved_at").alias("resolved_at"),
    F.col("follow_up_required").cast(BooleanType()).alias("follow_up_required"),
    "follow_up_reason",
    F.col("requester.id").alias("requester_id"),
    F.col("assignee.id").alias("assignee_id"),
    F.col("assignment_group.id").alias("assignment_group_id"),
    F.col("category.id").alias("category_id"),
    F.expr("clean_field(description_html, description_text)").alias("description_text_clean"),
    F.expr("clean_field(resolution_summary_html, resolution_summary_text)").alias("resolution_summary_text_clean"),
    "description_html",
    "resolution_summary_html",
)

work_notes = (
    incident_details.select(F.col("id").alias("incident_id"), F.explode_outer("work_notes").alias("note"))
    .select(
        F.col("note.id").alias("work_note_id"),
        "incident_id",
        F.col("note.author.id").alias("author_user_id"),
        F.to_timestamp(F.col("note.created_at")).alias("created_at"),
        F.col("note.note_html").alias("note_html"),
        F.expr("clean_field(note.note_html, note.note_text)").alias("note_text_clean"),
    )
    .where(F.col("work_note_id").isNotNull())
)

resolution_notes = (
    incident_details.select(F.col("id").alias("incident_id"), F.explode_outer("resolution_notes").alias("note"))
    .select(
        F.col("note.id").alias("resolution_note_id"),
        "incident_id",
        F.col("note.author.id").alias("author_user_id"),
        F.to_timestamp(F.col("note.created_at")).alias("created_at"),
        F.col("note.note_html").alias("note_html"),
        F.expr("clean_field(note.note_html, note.note_text)").alias("note_text_clean"),
    )
    .where(F.col("resolution_note_id").isNotNull())
)

change_requests = deduplicate(
    incident_details.select(F.explode_outer("change_requests").alias("chg"))
    .select(
        F.col("chg.id").alias("change_request_id"),
        F.col("chg.number").alias("number"),
        F.col("chg.title").alias("title"),
        F.col("chg.state").alias("state"),
        F.col("chg.risk").alias("risk"),
        F.to_timestamp(F.col("chg.planned_start")).alias("planned_start"),
        F.to_timestamp(F.col("chg.planned_end")).alias("planned_end"),
        F.to_timestamp(F.col("chg.implemented_at")).alias("implemented_at"),
    )
    .where(F.col("change_request_id").isNotNull()),
    ["change_request_id"],
)

incident_changes = (
    incident_details.select(F.col("id").alias("incident_id"), F.explode_outer("change_requests").alias("chg"))
    .select(
        "incident_id",
        F.col("chg.id").alias("change_request_id"),
        F.col("chg.relationship_type").alias("relationship_type"),
    )
    .where(F.col("change_request_id").isNotNull())
)

slas = (
    incident_details.select(F.col("id").alias("incident_id"), F.explode_outer("slas").alias("sla"))
    .select(
        F.col("sla.id").alias("sla_id"),
        "incident_id",
        F.col("sla.name").alias("name"),
        F.col("sla.stage").alias("stage"),
        F.col("sla.target_hours").cast(DoubleType()).alias("target_hours"),
        F.col("sla.elapsed_hours").cast(DoubleType()).alias("elapsed_hours"),
        F.col("sla.breached").cast(BooleanType()).alias("breached"),
    )
    .where(F.col("sla_id").isNotNull())
)


def flatten_assets(raw_df: DataFrame, id_column_name: str) -> DataFrame:
    return (
        raw_df.select(F.explode("items").alias("item"))
        .select(
            F.col("item.id").alias(id_column_name),
            F.col("item.incident_id").alias("incident_id"),
            F.col("item.incident_number").alias("incident_number"),
            F.col("item.file_name").alias("file_name"),
            F.col("item.content_type").alias("content_type"),
            F.col("item.description").alias("description"),
            F.col("item.mock_url").alias("mock_url"),
            F.to_timestamp(F.col("item.uploaded_at")).alias("uploaded_at"),
            F.col("item.file_size_kb").cast("int").alias("file_size_kb"),
            F.col("item.width_px").cast("int").alias("width_px"),
            F.col("item.height_px").cast("int").alias("height_px"),
        )
        .where(F.col(id_column_name).isNotNull())
        .dropDuplicates([id_column_name])
    )


attachments = flatten_assets(attachments_raw, "attachment_id").drop("width_px", "height_px")
images = flatten_assets(images_raw, "image_id").drop("file_size_kb")
documents = flatten_assets(documents_raw, "document_id").drop("width_px", "height_px")

external_references = (
    incident_details.select(F.col("id").alias("incident_id"), F.explode_outer("external_references").alias("ref"))
    .select(
        F.col("ref.id").alias("external_reference_id"),
        "incident_id",
        F.col("ref.reference_type").alias("reference_type"),
        F.col("ref.title").alias("title"),
        F.col("ref.url").alias("url"),
        F.col("ref.source_system").alias("source_system"),
    )
    .where(F.col("external_reference_id").isNotNull())
)

incident_kb_links = incident_kb_articles.dropDuplicates(["incident_id", "kb_article_id"])

retrieval_documents = (
    incidents.select(
        F.concat(F.lit("incident:"), F.col("incident_id")).alias("retrieval_document_id"),
        F.lit("incident_description").alias("source_type"),
        F.col("incident_id").alias("source_id"),
        F.col("incident_id"),
        F.lit(None).cast(StringType()).alias("kb_article_id"),
        F.col("number").alias("title"),
        F.col("description_text_clean").alias("clean_text"),
        F.col("description_html").alias("html_source"),
        F.col("updated_at").alias("updated_at"),
        F.to_json(
            F.struct(
                "state",
                "priority",
                "impact",
                "urgency",
                "assignment_group_id",
                "category_id",
            )
        ).alias("metadata_json"),
    )
    .unionByName(
        incidents.where(F.col("resolution_summary_text_clean").isNotNull()).select(
            F.concat(F.lit("resolution-summary:"), F.col("incident_id")).alias("retrieval_document_id"),
            F.lit("incident_resolution_summary").alias("source_type"),
            F.col("incident_id").alias("source_id"),
            F.col("incident_id"),
            F.lit(None).cast(StringType()).alias("kb_article_id"),
            F.col("number").alias("title"),
            F.col("resolution_summary_text_clean").alias("clean_text"),
            F.col("resolution_summary_html").alias("html_source"),
            F.col("updated_at").alias("updated_at"),
            F.to_json(F.struct("state", "priority", "assignment_group_id", "category_id")).alias("metadata_json"),
        )
    )
    .unionByName(
        work_notes.select(
            F.concat(F.lit("work-note:"), F.col("work_note_id")).alias("retrieval_document_id"),
            F.lit("work_note").alias("source_type"),
            F.col("work_note_id").alias("source_id"),
            "incident_id",
            F.lit(None).cast(StringType()).alias("kb_article_id"),
            F.concat(F.lit("Work note for "), F.col("incident_id")).alias("title"),
            F.col("note_text_clean").alias("clean_text"),
            F.col("note_html").alias("html_source"),
            F.col("created_at").alias("updated_at"),
            F.to_json(F.struct("author_user_id")).alias("metadata_json"),
        )
    )
    .unionByName(
        resolution_notes.select(
            F.concat(F.lit("resolution-note:"), F.col("resolution_note_id")).alias("retrieval_document_id"),
            F.lit("resolution_note").alias("source_type"),
            F.col("resolution_note_id").alias("source_id"),
            "incident_id",
            F.lit(None).cast(StringType()).alias("kb_article_id"),
            F.concat(F.lit("Resolution note for "), F.col("incident_id")).alias("title"),
            F.col("note_text_clean").alias("clean_text"),
            F.col("note_html").alias("html_source"),
            F.col("created_at").alias("updated_at"),
            F.to_json(F.struct("author_user_id")).alias("metadata_json"),
        )
    )
    .unionByName(
        kb_articles.select(
            F.concat(F.lit("kb-article:"), F.col("kb_article_id")).alias("retrieval_document_id"),
            F.lit("kb_article").alias("source_type"),
            F.col("kb_article_id").alias("source_id"),
            F.lit(None).cast(StringType()).alias("incident_id"),
            "kb_article_id",
            "title",
            F.col("content_text_clean").alias("clean_text"),
            F.col("content_html").alias("html_source"),
            F.col("updated_at").alias("updated_at"),
            F.to_json(F.struct("category_id", "audience", "keywords")).alias("metadata_json"),
        )
    )
    .where(F.col("clean_text").isNotNull())
)

write_delta(users, "users")
write_delta(assignment_groups, "assignment_groups")
write_delta(categories, "categories")
write_delta(incidents, "incidents")
write_delta(kb_articles, "kb_articles")
write_delta(work_notes, "work_notes")
write_delta(resolution_notes, "resolution_notes")
write_delta(change_requests, "change_requests")
write_delta(incident_changes, "incident_changes")
write_delta(slas, "slas")
write_delta(attachments, "attachments")
write_delta(images, "images")
write_delta(documents, "documents")
write_delta(external_references, "external_references")
write_delta(incident_kb_links, "incident_kb_links")
write_delta(retrieval_documents, "retrieval_documents")

print(
    {
        "incidents": incidents.count(),
        "users": users.count(),
        "kb_articles": kb_articles.count(),
        "work_notes": work_notes.count(),
        "resolution_notes": resolution_notes.count(),
        "retrieval_documents": retrieval_documents.count(),
    }
)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
