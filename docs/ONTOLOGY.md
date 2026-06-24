# ServiceNow Ontology Layer

## 1. Core entity nodes

| Node | Source | Identity | Description |
| --- | --- | --- | --- |
| `Incident` | `incidents` | `incident_id` | Central operational ticket node with state, priority, age, and ticket summary attributes. |
| `User` | Derived from `incidents.opened_by_*`, `incidents.assigned_to_*`, and optional curated user tables | `user_id` | Represents requesters, assignees, and other people attached to ticket flow. |
| `AssignmentGroup` | `assignment_groups` | `assignment_group_id` | Support-team ownership node used for workload, routing, and escalation questions. |
| `Category` | `categories` | `category_id` | Topic classification node used by incidents and knowledge articles. |
| `BusinessService` | Derived for the POC from `assignment_groups` + `categories` until CMDB/service data exists | Hash of assignment group and category | Scoped service/application proxy for impact and support-domain traversal. |
| `KnowledgeArticle` | `kb_articles` | `kb_article_id` | Structured KB article metadata node for reuse and grounding. |
| `Attachment` | `attachments` | `attachment_id` | File metadata node for evidence attached to incidents. |
| `Document` | `retrieval_documents` and optional curated document metadata | `retrieval_document_id` or `document_id` | Cleaned narrative/supporting text node for grounding and graph traversal. |
| `Image` | `images` when present, otherwise image-like rows in `attachments` | `image_id` or `attachment_id` | Screenshot or image evidence node. |
| `ChangeRequest` | Optional curated `change_requests` and `incident_changes` | `change_request_id` | Operational change node for tickets that relate to releases, changes, or remediation actions. |
| `ResolutionPattern` | Derived from normalized `resolution_notes` or incident resolution text | Hash of normalized fix phrase | Reusable resolution motif for “similar fix” navigation. |

## 2. Core relationships

| Relationship | From | To | Cardinality | Description |
| --- | --- | --- | --- | --- |
| `OPENED_BY` | Incident | User | Many-to-one | Connects a ticket to the person who opened it. |
| `ASSIGNED_TO_USER` | Incident | User | Many-to-one | Connects a ticket to the current assignee when available. |
| `ASSIGNED_TO_GROUP` | Incident | AssignmentGroup | Many-to-one | Shows resolver-group ownership of the incident. |
| `BELONGS_TO_CATEGORY` | Incident | Category | Many-to-one | Classifies the incident within the ServiceNow category hierarchy. |
| `IMPACTS_SERVICE` | Incident | BusinessService | Many-to-one (POC heuristic) | Links the incident to a scoped service/application proxy built from category and support ownership. |
| `REFERENCES_KB` | Incident | KnowledgeArticle | Many-to-many | Preserves explicit ticket-to-KB reuse links from `incident_kb_links`. |
| `HAS_ATTACHMENT` | Incident | Attachment | One-to-many | Links metadata for logs, files, or supporting evidence attached to a ticket. |
| `HAS_IMAGE` | Incident | Image | One-to-many | Links screenshot/image evidence to a ticket. |
| `HAS_DOCUMENT` | Incident | Document | One-to-many | Links cleaned narrative retrieval artifacts back to incidents for grounding. |
| `BACKED_BY_DOCUMENT` | KnowledgeArticle | Document | One-to-many | Connects KB metadata to the cleaned retrieval corpus entry used for AI grounding. |
| `RELATES_TO_CHANGE` | Incident | ChangeRequest | Many-to-many | Optional relationship for tickets connected to changes or releases. |
| `RESOLVED_BY_PATTERN` | Incident | ResolutionPattern | Many-to-many | Maps incidents to canonicalized fix patterns derived from resolution text. |

## 3. Implementation as a Fabric notebook

Notebook path: `servicenow-demo_Ontology_Graph.Notebook\`

The notebook implements the ontology as Delta-backed graph tables:

- Reads curated Lakehouse tables such as `incidents`, `categories`, `assignment_groups`, `kb_articles`, `slas`, `incident_kb_links`, `attachments`, `work_notes`, `resolution_notes`, and `retrieval_documents`.
- Builds a normalized `ontology_nodes` table with schema `node_id`, `node_type`, `name`, `properties_json`.
- Builds a normalized `ontology_edges` table with schema `edge_id`, `source_node_id`, `target_node_id`, `relationship_type`, `properties_json`.
- Writes both outputs back as Delta tables for downstream graph export, notebook analysis, or agent grounding.
- Optionally validates a sampled in-memory graph with NetworkX when that package is available in the Fabric runtime.

### Notebook output tables

| Table | Purpose |
| --- | --- |
| `ontology_nodes` | Canonical node catalog for tickets, people, groups, categories, KB articles, documents, images, attachments, changes, and resolution patterns. |
| `ontology_edges` | Canonical relationship catalog used for traversal, grounding, and graph analytics. |

## 4. Example graph traversal questions

1. Which knowledge articles, documents, and attachments are connected to a specific incident?
2. Which other incidents were resolved by the same resolution pattern as a selected ticket?
3. Which assignment groups and categories are most connected to SLA-breached incidents?
4. Which KB articles are most frequently reused by tickets owned by Network Support?
5. Which business-service proxy nodes are connected to the oldest open incidents?
6. Which incidents linked to a category also share the same image or document evidence type?

## 5. Guidance on splitting

Split the ontology into smaller subgraphs when one of these conditions is true:

1. **Operational and knowledge use cases diverge.** Keep a core support-operations graph for incidents, groups, categories, SLA, and users, and move KB/retrieval-heavy paths into a knowledge graph.
2. **Asset density grows quickly.** If attachments, images, and documents dominate the node count, isolate an evidence graph so operational traversals stay small and predictable.
3. **Change or CMDB coverage becomes first-class.** When real `change_requests`, `business services`, or CMDB entities arrive, promote them into a separate service-impact subgraph.
4. **Traversal ambiguity increases.** If too many many-to-many paths cause confusing agent grounding, publish smaller domain graphs with explicit routing.
5. **Refresh cadence differs.** Keep fast-moving ticket/SLA entities in one graph and slower-changing KB or service entities in another.

Recommended split path if needed:

- **Support Operations Graph:** incidents, users, assignment groups, categories, SLAs
- **Knowledge & Resolution Graph:** incidents, KB articles, retrieval documents, resolution patterns
- **Evidence & Change Graph:** attachments, images, documents, change requests, external evidence
