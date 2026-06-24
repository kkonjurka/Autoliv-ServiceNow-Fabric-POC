# Fabric notebook source

# CELL ********************

"""Build ontology node and edge tables from curated ServiceNow Delta tables."""

from __future__ import annotations

import os

from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql import types as T

try:
    import networkx as nx
except ImportError:  # pragma: no cover - Fabric runtime dependency
    nx = None

SOURCE_DATABASE = os.getenv("SERVICENOW_CURATED_DATABASE", "")
TARGET_DATABASE = os.getenv("SERVICENOW_ONTOLOGY_DATABASE", SOURCE_DATABASE)
EMPTY_NODE_SCHEMA = "node_id string, node_type string, name string, properties_json string"
EMPTY_EDGE_SCHEMA = (
    "edge_id string, source_node_id string, target_node_id string, "
    "relationship_type string, properties_json string"
)


# CELL ********************

def qualify_table_name(database_name: str, table_name: str) -> str:
    return f"{database_name}.{table_name}" if database_name else table_name


def source_table_name(table_name: str) -> str:
    return qualify_table_name(SOURCE_DATABASE, table_name)


def target_table_name(table_name: str) -> str:
    return qualify_table_name(TARGET_DATABASE, table_name)


def table_exists(table_name: str) -> bool:
    return spark.catalog.tableExists(source_table_name(table_name))


def read_table(table_name: str, required: bool = True) -> DataFrame:
    if table_exists(table_name):
        return spark.table(source_table_name(table_name))
    if required:
        raise ValueError(f"Required curated table not found: {source_table_name(table_name)}")
    return spark.createDataFrame([], T.StructType([]))


def empty_nodes() -> DataFrame:
    return spark.createDataFrame([], EMPTY_NODE_SCHEMA)


def empty_edges() -> DataFrame:
    return spark.createDataFrame([], EMPTY_EDGE_SCHEMA)


def pick_col(df: DataFrame, candidates: list[str], alias: str, data_type: str = "string"):
    for candidate in candidates:
        if candidate in df.columns:
            return F.col(candidate).alias(alias)
    return F.lit(None).cast(data_type).alias(alias)


def union_all(dataframes: list[DataFrame]) -> DataFrame:
    if not dataframes:
        raise ValueError("union_all requires at least one DataFrame")
    result = dataframes[0]
    for df in dataframes[1:]:
        result = result.unionByName(df, allowMissingColumns=True)
    return result


def edge_hash(relationship_type: str, source_column: str, target_column: str):
    return F.sha2(
        F.concat_ws("|", F.lit(relationship_type), F.col(source_column), F.col(target_column)),
        256,
    )


def write_delta(df: DataFrame, table_name: str) -> None:
    (
        df.write.mode("overwrite")
        .format("delta")
        .option("overwriteSchema", "true")
        .saveAsTable(target_table_name(table_name))
    )


incidents = read_table("incidents")
categories = read_table("categories")
assignment_groups = read_table("assignment_groups")
kb_articles = read_table("kb_articles")
incident_kb_links = read_table("incident_kb_links")
attachments = read_table("attachments", required=False)
images = read_table("images", required=False)
retrieval_documents = read_table("retrieval_documents")
resolution_notes = read_table("resolution_notes", required=False)
change_requests = read_table("change_requests", required=False)
incident_changes = read_table("incident_changes", required=False)


# CELL ********************

incident_nodes = incidents.select(
    F.concat(F.lit("incident:"), F.col("incident_id")).alias("node_id"),
    F.lit("Incident").alias("node_type"),
    F.coalesce(F.col("number"), F.col("incident_id")).alias("name"),
    F.to_json(
        F.struct(
            "incident_id",
            "number",
            pick_col(incidents, ["short_description"], "short_description"),
            pick_col(incidents, ["state"], "state"),
            pick_col(incidents, ["priority"], "priority"),
            pick_col(incidents, ["opened_at"], "opened_at", "timestamp"),
            pick_col(incidents, ["resolved_at"], "resolved_at", "timestamp"),
            pick_col(incidents, ["closed_at"], "closed_at", "timestamp"),
        )
    ).alias("properties_json"),
)

user_candidates: list[DataFrame] = []
if {"opened_by_id", "opened_by_name"}.issubset(set(incidents.columns)):
    user_candidates.append(
        incidents.select(
            F.col("opened_by_id").alias("user_id"),
            F.col("opened_by_name").alias("user_name"),
            F.lit("opened_by").alias("user_role"),
        )
    )
if {"assigned_to_id", "assigned_to_name"}.issubset(set(incidents.columns)):
    user_candidates.append(
        incidents.select(
            F.col("assigned_to_id").alias("user_id"),
            F.col("assigned_to_name").alias("user_name"),
            F.lit("assigned_to").alias("user_role"),
        )
    )

users_derived = (
    union_all(user_candidates).where(F.col("user_id").isNotNull()).dropDuplicates(["user_id"])
    if user_candidates
    else spark.createDataFrame([], "user_id string, user_name string, user_role string")
)

user_nodes = users_derived.select(
    F.concat(F.lit("user:"), F.col("user_id")).alias("node_id"),
    F.lit("User").alias("node_type"),
    F.coalesce(F.col("user_name"), F.col("user_id")).alias("name"),
    F.to_json(F.struct("user_id", "user_name", "user_role")).alias("properties_json"),
)

assignment_group_nodes = assignment_groups.select(
    F.concat(F.lit("group:"), F.col("assignment_group_id")).alias("node_id"),
    F.lit("AssignmentGroup").alias("node_type"),
    F.col("name").alias("name"),
    F.to_json(F.struct("assignment_group_id", "description", "escalation_email")).alias("properties_json"),
)

category_nodes = categories.select(
    F.concat(F.lit("category:"), F.col("category_id")).alias("node_id"),
    F.lit("Category").alias("node_type"),
    F.concat_ws(" / ", F.col("name"), F.col("subcategory")).alias("name"),
    F.to_json(F.struct("category_id", "name", "subcategory")).alias("properties_json"),
)

ag = assignment_groups.alias("ag")
cat = categories.alias("cat")
business_service_source = (
    incidents.alias("i")
    .join(ag, on="assignment_group_id", how="left")
    .join(cat, on="category_id", how="left")
    .select(
        F.sha2(F.concat_ws("|", F.col("assignment_group_id"), F.col("category_id")), 256).alias("business_service_id"),
        F.col("assignment_group_id"),
        F.col("category_id"),
        F.concat_ws(" / ", F.col("ag.name"), F.col("cat.name")).alias("business_service_name"),
        F.col("cat.subcategory").alias("subcategory"),
    )
    .dropDuplicates(["business_service_id"])
)

business_service_nodes = business_service_source.select(
    F.concat(F.lit("service:"), F.col("business_service_id")).alias("node_id"),
    F.lit("BusinessService").alias("node_type"),
    F.coalesce(F.col("business_service_name"), F.col("business_service_id")).alias("name"),
    F.to_json(
        F.struct(
            "business_service_id",
            "assignment_group_id",
            "category_id",
            "subcategory",
            F.lit("Derived from assignment group + category for the POC scope").alias("derivation"),
        )
    ).alias("properties_json"),
)

kb_article_nodes = kb_articles.select(
    F.concat(F.lit("kb:"), F.col("kb_article_id")).alias("node_id"),
    F.lit("KnowledgeArticle").alias("node_type"),
    F.col("title").alias("name"),
    F.to_json(
        F.struct(
            "kb_article_id",
            "kb_article_number",
            pick_col(kb_articles, ["category_id"], "category_id"),
            pick_col(kb_articles, ["category_name"], "category_name"),
            pick_col(kb_articles, ["category_subcategory"], "category_subcategory"),
            pick_col(kb_articles, ["audience"], "audience"),
            pick_col(kb_articles, ["keywords"], "keywords"),
        )
    ).alias("properties_json"),
)

attachment_nodes = (
    attachments.where(F.col("attachment_id").isNotNull()).select(
        F.concat(F.lit("attachment:"), F.col("attachment_id")).alias("node_id"),
        F.lit("Attachment").alias("node_type"),
        F.col("file_name").alias("name"),
        F.to_json(
            F.struct("incident_id", "content_type", "description", "mock_url", "uploaded_at")
        ).alias("properties_json"),
    )
    if attachments.columns
    else empty_nodes()
)

image_nodes = (
    images.where(F.col("image_id").isNotNull()).select(
        F.concat(F.lit("image:"), F.col("image_id")).alias("node_id"),
        F.lit("Image").alias("node_type"),
        F.col("file_name").alias("name"),
        F.to_json(
            F.struct("incident_id", "content_type", "description", "mock_url", "uploaded_at")
        ).alias("properties_json"),
    )
    if images.columns
    else (
        attachments.where(F.col("content_type").startswith("image/")).select(
            F.concat(F.lit("image:"), F.col("attachment_id")).alias("node_id"),
            F.lit("Image").alias("node_type"),
            F.col("file_name").alias("name"),
            F.to_json(
                F.struct("incident_id", "content_type", "description", "mock_url", "uploaded_at")
            ).alias("properties_json"),
        )
        if attachments.columns
        else empty_nodes()
    )
)

document_nodes = retrieval_documents.select(
    F.concat(F.lit("document:"), F.col("retrieval_document_id")).alias("node_id"),
    F.lit("Document").alias("node_type"),
    F.col("title").alias("name"),
    F.to_json(
        F.struct("source_type", "source_id", "incident_id", "kb_article_id", "updated_at", "metadata_json")
    ).alias("properties_json"),
)

change_request_nodes = (
    change_requests.select(
        F.concat(F.lit("change:"), F.col("change_request_id")).alias("node_id"),
        F.lit("ChangeRequest").alias("node_type"),
        F.coalesce(F.col("number"), F.col("change_request_id")).alias("name"),
        F.to_json(F.struct(*[F.col(column_name) for column_name in change_requests.columns])).alias("properties_json"),
    )
    if change_requests.columns
    else empty_nodes()
)

resolution_text = (
    resolution_notes.select(
        F.col("incident_id"),
        pick_col(resolution_notes, ["note_text_clean", "resolution_notes_clean"], "resolution_text"),
    )
    if resolution_notes.columns
    else incidents.select(
        F.col("incident_id"),
        pick_col(incidents, ["resolution_notes_clean"], "resolution_text"),
    )
)

resolution_pattern_source = (
    resolution_text.where(F.col("resolution_text").isNotNull())
    .select(
        "incident_id",
        F.lower(F.trim(F.regexp_replace(F.col("resolution_text"), r"[^a-zA-Z0-9 ]", " "))).alias("normalized_text"),
    )
    .where(F.length(F.col("normalized_text")) > 20)
    .select(
        "incident_id",
        F.array_join(F.slice(F.split(F.col("normalized_text"), " "), 1, 12), " ").alias("pattern_label"),
    )
)

resolution_pattern_nodes = (
    resolution_pattern_source.withColumn("resolution_pattern_id", F.sha2(F.col("pattern_label"), 256))
    .groupBy("resolution_pattern_id", "pattern_label")
    .agg(F.countDistinct("incident_id").alias("incident_count"))
    .select(
        F.concat(F.lit("pattern:"), F.col("resolution_pattern_id")).alias("node_id"),
        F.lit("ResolutionPattern").alias("node_type"),
        F.initcap(F.col("pattern_label")).alias("name"),
        F.to_json(F.struct("resolution_pattern_id", "pattern_label", "incident_count")).alias("properties_json"),
    )
)

ontology_nodes = union_all(
    [
        incident_nodes,
        user_nodes,
        assignment_group_nodes,
        category_nodes,
        business_service_nodes,
        kb_article_nodes,
        attachment_nodes,
        image_nodes,
        document_nodes,
        change_request_nodes,
        resolution_pattern_nodes,
    ]
).dropDuplicates(["node_id"])


# CELL ********************

opened_by_edges = (
    incidents.where(F.col("opened_by_id").isNotNull())
    .select(
        F.concat(F.lit("incident:"), F.col("incident_id")).alias("source_node_id"),
        F.concat(F.lit("user:"), F.col("opened_by_id")).alias("target_node_id"),
        F.lit("OPENED_BY").alias("relationship_type"),
        F.to_json(F.struct(F.col("opened_by_name").alias("user_name"))).alias("properties_json"),
    )
    .withColumn("edge_id", edge_hash("OPENED_BY", "source_node_id", "target_node_id"))
    if "opened_by_id" in incidents.columns
    else empty_edges()
)

assigned_to_user_edges = (
    incidents.where(F.col("assigned_to_id").isNotNull())
    .select(
        F.concat(F.lit("incident:"), F.col("incident_id")).alias("source_node_id"),
        F.concat(F.lit("user:"), F.col("assigned_to_id")).alias("target_node_id"),
        F.lit("ASSIGNED_TO_USER").alias("relationship_type"),
        F.to_json(F.struct(F.col("assigned_to_name").alias("user_name"))).alias("properties_json"),
    )
    .withColumn("edge_id", edge_hash("ASSIGNED_TO_USER", "source_node_id", "target_node_id"))
    if "assigned_to_id" in incidents.columns
    else empty_edges()
)

assignment_group_edges = (
    incidents.where(F.col("assignment_group_id").isNotNull())
    .select(
        F.concat(F.lit("incident:"), F.col("incident_id")).alias("source_node_id"),
        F.concat(F.lit("group:"), F.col("assignment_group_id")).alias("target_node_id"),
        F.lit("ASSIGNED_TO_GROUP").alias("relationship_type"),
        F.lit("{}").alias("properties_json"),
    )
    .withColumn("edge_id", edge_hash("ASSIGNED_TO_GROUP", "source_node_id", "target_node_id"))
)

category_edges = (
    incidents.where(F.col("category_id").isNotNull())
    .select(
        F.concat(F.lit("incident:"), F.col("incident_id")).alias("source_node_id"),
        F.concat(F.lit("category:"), F.col("category_id")).alias("target_node_id"),
        F.lit("BELONGS_TO_CATEGORY").alias("relationship_type"),
        F.lit("{}").alias("properties_json"),
    )
    .withColumn("edge_id", edge_hash("BELONGS_TO_CATEGORY", "source_node_id", "target_node_id"))
)

business_service_edges = (
    incidents.where(F.col("assignment_group_id").isNotNull() & F.col("category_id").isNotNull())
    .select(
        F.concat(F.lit("incident:"), F.col("incident_id")).alias("source_node_id"),
        F.concat(
            F.lit("service:"),
            F.sha2(F.concat_ws("|", F.col("assignment_group_id"), F.col("category_id")), 256),
        ).alias("target_node_id"),
        F.lit("IMPACTS_SERVICE").alias("relationship_type"),
        F.to_json(
            F.struct(F.lit("assignment_group + category heuristic").alias("derivation"))
        ).alias("properties_json"),
    )
    .withColumn("edge_id", edge_hash("IMPACTS_SERVICE", "source_node_id", "target_node_id"))
)

kb_edges = (
    incident_kb_links.where(F.col("incident_id").isNotNull() & F.col("kb_article_id").isNotNull())
    .select(
        F.concat(F.lit("incident:"), F.col("incident_id")).alias("source_node_id"),
        F.concat(F.lit("kb:"), F.col("kb_article_id")).alias("target_node_id"),
        F.lit("REFERENCES_KB").alias("relationship_type"),
        F.lit("{}").alias("properties_json"),
    )
    .withColumn("edge_id", edge_hash("REFERENCES_KB", "source_node_id", "target_node_id"))
)

attachment_edges = (
    attachments.where(F.col("attachment_id").isNotNull())
    .select(
        F.concat(F.lit("incident:"), F.col("incident_id")).alias("source_node_id"),
        F.concat(F.lit("attachment:"), F.col("attachment_id")).alias("target_node_id"),
        F.lit("HAS_ATTACHMENT").alias("relationship_type"),
        F.to_json(F.struct("content_type", "mock_url")).alias("properties_json"),
    )
    .withColumn("edge_id", edge_hash("HAS_ATTACHMENT", "source_node_id", "target_node_id"))
    if attachments.columns
    else empty_edges()
)

image_edges = (
    images.where(F.col("image_id").isNotNull())
    .select(
        F.concat(F.lit("incident:"), F.col("incident_id")).alias("source_node_id"),
        F.concat(F.lit("image:"), F.col("image_id")).alias("target_node_id"),
        F.lit("HAS_IMAGE").alias("relationship_type"),
        F.to_json(F.struct("content_type", "mock_url")).alias("properties_json"),
    )
    .withColumn("edge_id", edge_hash("HAS_IMAGE", "source_node_id", "target_node_id"))
    if images.columns
    else (
        attachments.where(F.col("content_type").startswith("image/"))
        .select(
            F.concat(F.lit("incident:"), F.col("incident_id")).alias("source_node_id"),
            F.concat(F.lit("image:"), F.col("attachment_id")).alias("target_node_id"),
            F.lit("HAS_IMAGE").alias("relationship_type"),
            F.to_json(F.struct("content_type", "mock_url")).alias("properties_json"),
        )
        .withColumn("edge_id", edge_hash("HAS_IMAGE", "source_node_id", "target_node_id"))
        if attachments.columns
        else empty_edges()
    )
)

document_edges = (
    retrieval_documents.where(F.col("incident_id").isNotNull())
    .select(
        F.concat(F.lit("incident:"), F.col("incident_id")).alias("source_node_id"),
        F.concat(F.lit("document:"), F.col("retrieval_document_id")).alias("target_node_id"),
        F.lit("HAS_DOCUMENT").alias("relationship_type"),
        F.to_json(F.struct("source_type", "updated_at")).alias("properties_json"),
    )
    .withColumn("edge_id", edge_hash("HAS_DOCUMENT", "source_node_id", "target_node_id"))
)

kb_document_edges = (
    retrieval_documents.where(F.col("kb_article_id").isNotNull())
    .select(
        F.concat(F.lit("kb:"), F.col("kb_article_id")).alias("source_node_id"),
        F.concat(F.lit("document:"), F.col("retrieval_document_id")).alias("target_node_id"),
        F.lit("BACKED_BY_DOCUMENT").alias("relationship_type"),
        F.to_json(F.struct("source_type", "updated_at")).alias("properties_json"),
    )
    .withColumn("edge_id", edge_hash("BACKED_BY_DOCUMENT", "source_node_id", "target_node_id"))
)

resolution_pattern_edges = (
    resolution_pattern_source.withColumn("resolution_pattern_id", F.sha2(F.col("pattern_label"), 256))
    .select(
        F.concat(F.lit("incident:"), F.col("incident_id")).alias("source_node_id"),
        F.concat(F.lit("pattern:"), F.col("resolution_pattern_id")).alias("target_node_id"),
        F.lit("RESOLVED_BY_PATTERN").alias("relationship_type"),
        F.to_json(F.struct("pattern_label")).alias("properties_json"),
    )
    .withColumn("edge_id", edge_hash("RESOLVED_BY_PATTERN", "source_node_id", "target_node_id"))
)

change_request_edges = (
    incident_changes.where(F.col("incident_id").isNotNull() & F.col("change_request_id").isNotNull())
    .select(
        F.concat(F.lit("incident:"), F.col("incident_id")).alias("source_node_id"),
        F.concat(F.lit("change:"), F.col("change_request_id")).alias("target_node_id"),
        F.lit("RELATES_TO_CHANGE").alias("relationship_type"),
        F.to_json(
            F.struct(
                *[
                    F.col(column_name)
                    for column_name in incident_changes.columns
                    if column_name not in {"incident_id", "change_request_id"}
                ]
            )
        ).alias("properties_json"),
    )
    .withColumn("edge_id", edge_hash("RELATES_TO_CHANGE", "source_node_id", "target_node_id"))
    if incident_changes.columns
    else empty_edges()
)

ontology_edges = union_all(
    [
        opened_by_edges,
        assigned_to_user_edges,
        assignment_group_edges,
        category_edges,
        business_service_edges,
        kb_edges,
        attachment_edges,
        image_edges,
        document_edges,
        kb_document_edges,
        resolution_pattern_edges,
        change_request_edges,
    ]
).select("edge_id", "source_node_id", "target_node_id", "relationship_type", "properties_json").dropDuplicates(["edge_id"])

write_delta(ontology_nodes, "ontology_nodes")
write_delta(ontology_edges, "ontology_edges")

print(f"Wrote {ontology_nodes.count()} ontology nodes to {target_table_name('ontology_nodes')}")
print(f"Wrote {ontology_edges.count()} ontology edges to {target_table_name('ontology_edges')}")

if nx is not None:
    sampled_nodes = ontology_nodes.limit(5000).collect()
    sampled_edges = ontology_edges.limit(5000).collect()
    graph = nx.MultiDiGraph()
    for row in sampled_nodes:
        graph.add_node(row.node_id, node_type=row.node_type, name=row.name)
    for row in sampled_edges:
        graph.add_edge(
            row.source_node_id,
            row.target_node_id,
            key=row.edge_id,
            relationship_type=row.relationship_type,
        )
    print(f"NetworkX validation graph contains {graph.number_of_nodes()} nodes and {graph.number_of_edges()} edges.")
else:
    print("NetworkX is not installed in this runtime; Spark Delta outputs were written without in-memory graph validation.")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
