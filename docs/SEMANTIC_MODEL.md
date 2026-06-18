# Fabric Semantic Model and Ontology Design

**Owner:** Book, Semantic Modeler  
**Date:** 2026-06-17T15:02:35.115-04:00  
**Status:** Proposed design for Fabric deployment

## 1. Scope and assumptions

This design covers the structured semantic model and the scoped ontology layer for the Autoliv ServiceNow to Microsoft Fabric POC. It assumes Fabric curated tables are available for `incidents`, `users`, `assignment_groups`, `categories`, `kb_articles`, `work_notes`, `resolution_notes`, `change_requests`, `incident_changes`, `slas`, `attachments`, `images`, `documents`, and `external_references`.

Assumptions:

1. The semantic model is built on curated Fabric tables plus semantic-layer derived views; it does not change raw or curated source tables.
2. `Business service/application` is a conformed dimension derived from category, assignment group, and change/request metadata until a CMDB or service catalog table is added.
3. `Resolution pattern` is a derived semantic dimension built from normalized `resolution_notes`, `resolution_summary_text`, and linked KB usage.
4. `KB article reuse` is modeled through a derived bridge from explicit incident-to-KB links when available, or from `external_references` and KB identifiers when explicit links are absent.
5. `Reopen rate` requires a derived `reopen_count` or reopen event flag from incident history; if no reopen signal exists yet, the measure remains present but should be marked preview in deployment.

## 2. Semantic model design

### 2.1 Recommended model shape

Use a star schema centered on `FactTickets` and `FactSla`, with bridge tables for KB usage, asset usage, change relationships, and resolution patterns.

Core semantic tables:

| Table | Type | Grain | Built from | Purpose |
| --- | --- | --- | --- | --- |
| `FactTickets` | Fact | One row per incident/ticket | `incidents` plus derived keys and durations | Core operational ticket analytics |
| `FactSla` | Fact | One row per SLA record per ticket | `slas` | SLA breach and elapsed-target analysis |
| `BridgeTicketKnowledgeArticle` | Bridge | One row per ticket-KB relationship | explicit ticket-KB links or derived from `external_references` + `kb_articles` | KB reuse and article effectiveness |
| `BridgeTicketAsset` | Bridge | One row per ticket asset reference | `attachments`, `images`, `documents` | Attachment/document/image type slicing |
| `BridgeTicketChange` | Bridge | One row per ticket-change relationship | `incident_changes` + `change_requests` | Change impact analysis |
| `BridgeTicketResolutionPattern` | Bridge | One row per ticket-resolution pattern | derived from `resolution_notes` and `incidents` | Resolution pattern frequency |

A hidden support dimension `DimChangeRequest` is also recommended for ontology export and change drill-through, but it does not need to be exposed as a primary Data Agent dimension in the POC.

### 2.2 Dimensions

| Dimension | Grain | Source / derivation | Key attributes | Notes |
| --- | --- | --- | --- | --- |
| `DimDate` | One row per calendar date | generated calendar | date, year, quarter, month, week, day of week, fiscal period | Role-playing for opened, updated, resolved, SLA due dates |
| `DimUser` | One row per user | `users` | user id, full name, email, department, title, location, manager name, active flag | Role-play as requester and assignee |
| `DimAssignmentGroup` | One row per support group | `assignment_groups` | group id, group name, description, escalation email, support tier, owning service | Can map to support tier later |
| `DimCategory` | One row per category/subcategory pair | `categories` | category id, category, subcategory, category path, domain family | Primary analytic classification |
| `DimBusinessService` | One row per business service/application | derived conformed mapping | service key, service name, application name, service owner, service domain | Derived now; replace with CMDB/service table later |
| `DimPriority` | One row per priority level | derived from `incidents.priority` | priority code, priority label, priority rank, severity band | Keep numeric rank for sorting |
| `DimState` | One row per ticket state/status | derived from `incidents.state` | state key, state label, state group, is_open, is_resolved | Supports open/backlog logic |
| `DimResolutionCode` | One row per resolution code | derived from incident closure semantics | resolution code, resolution family, success flag | If no native code exists, map from normalized closure text |
| `DimKnowledgeArticle` | One row per KB article | `kb_articles` | article id, article number, title, category, audience, published date, updated date | Hide long text from Data Agent unless needed |
| `DimAssetType` | One row per attachment/document type | unified from `attachments`, `images`, `documents` | asset type, mime/content type, logical class, file extension family | Supports attachment/document/image type questions |
| `DimResolutionPattern` | One row per canonical pattern | derived semantic catalog | pattern id, pattern name, pattern family, fix verb, confidence | Required to support pattern frequency |

### 2.3 Fact and bridge details

| Table | Important fields | Notes |
| --- | --- | --- |
| `FactTickets` | ticket id, ticket number, opened date key, updated date key, resolved date key, requester user key, assignee user key, assignment group key, category key, business service key, priority key, state key, resolution code key, open age days, resolution duration hours, reopen count, follow-up flag | Main reporting table |
| `FactSla` | sla id, ticket id, sla name, sla stage, target hours, elapsed hours, breached flag, due date key | Use for breach and elapsed/target measures |
| `BridgeTicketKnowledgeArticle` | ticket id, article id, relevance reason, reuse source | Makes KB reuse explicit |
| `BridgeTicketAsset` | ticket id, asset id, asset type key, asset class, uploaded date key | Unifies attachments, images, documents |
| `BridgeTicketChange` | ticket id, change request id, relationship type | Enables change-linked incident analysis |
| `BridgeTicketResolutionPattern` | ticket id, resolution pattern id, extraction source, extraction confidence | Keeps ontology and semantic model aligned |

### 2.4 Measures

| Measure | Definition | DAX pattern | Notes |
| --- | --- | --- | --- |
| `Ticket Volume` | Count of tickets in current filter context | `COUNTROWS ( FactTickets )` | Base ticket measure |
| `Open Ticket Count` | Count of tickets in open/in-progress/on-hold states | `CALCULATE ( [Ticket Volume], KEEPFILTERS ( DimState[IsOpen] = TRUE () ) )` | Uses conformed state logic |
| `Backlog by Priority` | Open ticket count sliced by priority | `Open Ticket Count` | Visual uses `DimPriority` on rows/axis |
| `Avg Resolution Time (Hours)` | Average hours from open to resolve for resolved tickets | `AVERAGEX ( FILTER ( FactTickets, NOT ISBLANK ( FactTickets[ResolvedDateKey] ) ), FactTickets[ResolutionDurationHours] )` | Excludes unresolved tickets |
| `SLA Breach Count` | Distinct tickets with at least one breached SLA | `CALCULATE ( DISTINCTCOUNT ( FactSla[TicketId] ), KEEPFILTERS ( FactSla[BreachedFlag] = TRUE () ) )` | Distinct ticket count is business-friendly |
| `Reopen Rate` | Reopened resolved tickets divided by resolved tickets | `DIVIDE ( [Reopened Ticket Count], [Resolved Ticket Count] )` | Mark preview if reopen signal is incomplete |
| `Aging Open Tickets` | Open ticket count sliced by open-age bucket | `Open Ticket Count` | Requires `FactTickets[OpenAgeBucket]` helper column |
| `Ticket Volume by Category` | Ticket volume sliced by category/subcategory | `Ticket Volume` | Visual uses `DimCategory` |
| `Resolution Pattern Frequency` | Tickets associated to each resolution pattern | `DISTINCTCOUNT ( BridgeTicketResolutionPattern[TicketId] )` | Use with `DimResolutionPattern` |
| `KB Article Reuse Count` | Ticket-KB relationship count in current KB/article filters | `COUNTROWS ( BridgeTicketKnowledgeArticle )` | Can be analyzed by article, category, service |

Recommended helper measures:

| Helper measure | DAX pattern | Purpose |
| --- | --- | --- |
| `Resolved Ticket Count` | `CALCULATE ( [Ticket Volume], KEEPFILTERS ( DimState[IsResolved] = TRUE () ) )` | Denominator for time and reopen metrics |
| `Reopened Ticket Count` | `CALCULATE ( DISTINCTCOUNT ( FactTickets[TicketId] ), FILTER ( FactTickets, FactTickets[ReopenCount] > 0 ) )` | Numerator for reopen rate |
| `Open Ticket Age (Days)` | `AVERAGEX ( FILTER ( FactTickets, RELATED ( DimState[IsOpen] ) = TRUE () ), FactTickets[OpenAgeDays] )` | Helpful for aging trend cards |

### 2.5 Relationships

| From | To | Cardinality | Active | Purpose |
| --- | --- | --- | --- | --- |
| `FactTickets[OpenedDateKey]` | `DimDate[DateKey]` | Many-to-one | Yes | Primary time analysis |
| `FactTickets[ResolvedDateKey]` | `DimDate[DateKey]` | Many-to-one | No | Resolve-time analysis via `USERELATIONSHIP` when needed |
| `FactTickets[UpdatedDateKey]` | `DimDate[DateKey]` | Many-to-one | No | Operational recency analysis |
| `FactTickets[RequesterUserKey]` | `DimUser[UserKey]` | Many-to-one | Yes | Requester analysis |
| `FactTickets[AssigneeUserKey]` | `DimUser[UserKey]` | Many-to-one | No | Assignee analysis through role-play or duplicate view |
| `FactTickets[AssignmentGroupKey]` | `DimAssignmentGroup[AssignmentGroupKey]` | Many-to-one | Yes | Support-group analytics |
| `FactTickets[CategoryKey]` | `DimCategory[CategoryKey]` | Many-to-one | Yes | Category/subcategory analytics |
| `FactTickets[BusinessServiceKey]` | `DimBusinessService[BusinessServiceKey]` | Many-to-one | Yes | Service/application analytics |
| `FactTickets[PriorityKey]` | `DimPriority[PriorityKey]` | Many-to-one | Yes | Severity and backlog slicing |
| `FactTickets[StateKey]` | `DimState[StateKey]` | Many-to-one | Yes | Open/resolved state logic |
| `FactTickets[ResolutionCodeKey]` | `DimResolutionCode[ResolutionCodeKey]` | Many-to-one | Yes | Closure/reason analytics |
| `FactSla[TicketId]` | `FactTickets[TicketId]` | Many-to-one | Yes | Ticket-to-SLA analysis |
| `FactSla[DueDateKey]` | `DimDate[DateKey]` | Many-to-one | No | SLA due-date trending |
| `BridgeTicketKnowledgeArticle[TicketId]` | `FactTickets[TicketId]` | Many-to-one | Yes | KB reuse across tickets |
| `BridgeTicketKnowledgeArticle[KnowledgeArticleKey]` | `DimKnowledgeArticle[KnowledgeArticleKey]` | Many-to-one | Yes | Article-level reuse |
| `BridgeTicketAsset[TicketId]` | `FactTickets[TicketId]` | Many-to-one | Yes | Asset-supported tickets |
| `BridgeTicketAsset[AssetTypeKey]` | `DimAssetType[AssetTypeKey]` | Many-to-one | Yes | Attachment/document/image type analysis |
| `BridgeTicketChange[TicketId]` | `FactTickets[TicketId]` | Many-to-one | Yes | Change-linked tickets |
| `BridgeTicketResolutionPattern[TicketId]` | `FactTickets[TicketId]` | Many-to-one | Yes | Pattern frequency |
| `BridgeTicketResolutionPattern[ResolutionPatternKey]` | `DimResolutionPattern[ResolutionPatternKey]` | Many-to-one | Yes | Pattern drill-down |

## 3. Ontology design

### 3.1 Node types

| Node | Derived from | Identity | Important properties | Scope note |
| --- | --- | --- | --- | --- |
| `Ticket` | `FactTickets` / `incidents` | ticket id, ticket number | state, priority, opened/resolved dates, follow-up flag, age, summary | Central operational node |
| `UserRequester` | `DimUser` | user id | full name, title, department, location, manager | Scoped to requester/assignee support use cases |
| `SupportGroup` | `DimAssignmentGroup` | group id | group name, description, escalation email, support tier | Operational ownership node |
| `CategorySubcategory` | `DimCategory` | category key | category, subcategory, domain family | Ticket classification node |
| `BusinessService` | `DimBusinessService` | service key | service name, app name, owner, domain | Keeps service impact visible |
| `KnowledgeArticle` | `DimKnowledgeArticle` | article id / article number | title, category, audience, freshness | Resolution guidance node |
| `Attachment` | `BridgeTicketAsset` + attachment class | asset id | file name, file type, uploaded date, description | Metadata-only node |
| `Document` | `BridgeTicketAsset` + document class | asset id | file name, document type, summary/description | Metadata-only node |
| `Image` | `BridgeTicketAsset` + image class | asset id | file name, image type, width, height, description | Metadata-only node |
| `ChangeRequest` | `change_requests` | change id / change number | title, state, risk, planned dates, implemented date | Related-change node |
| `ResolutionPattern` | `DimResolutionPattern` | pattern id | pattern name, family, canonical action, confidence | Derived knowledge node |

### 3.2 Relationship types

| Relationship | From | To | Source / derivation | Cardinality | Note |
| --- | --- | --- | --- | --- | --- |
| `OPENED_BY` | `Ticket` | `UserRequester` | requester key from `FactTickets` | Many-to-one | Required |
| `ASSIGNED_TO` | `Ticket` | `SupportGroup` | assignment group key | Many-to-one | Required |
| `BELONGS_TO_CATEGORY` | `Ticket` | `CategorySubcategory` | category key | Many-to-one | Required |
| `IMPACTS_SERVICE` | `Ticket` | `BusinessService` | business service key | Many-to-one | Required |
| `REFERENCES_KB` | `Ticket` | `KnowledgeArticle` | KB bridge | Many-to-many | Required |
| `HAS_ATTACHMENT` | `Ticket` | `Attachment` | asset bridge filtered to attachment class | One-to-many | Required |
| `HAS_DOCUMENT` | `Ticket` | `Document` | asset bridge filtered to document class | One-to-many | POC scoped |
| `HAS_IMAGE` | `Ticket` | `Image` | asset bridge filtered to image class | One-to-many | POC scoped |
| `RELATES_TO_CHANGE` | `Ticket` | `ChangeRequest` | incident-change bridge | Many-to-many | Required |
| `RESOLVED_BY_PATTERN` | `Ticket` | `ResolutionPattern` | resolution pattern bridge | Many-to-many | Required |
| `KB_APPLIES_TO_CATEGORY` | `KnowledgeArticle` | `CategorySubcategory` | KB category key | Many-to-one | Useful for KB traversal |
| `GROUP_SUPPORTS_SERVICE` | `SupportGroup` | `BusinessService` | service-group mapping | Many-to-many | Optional in POC |

### 3.3 Ontology implementation path

Build the ontology from semantic-model entities, not raw Fabric landing tables:

1. Publish and validate the semantic model first.
2. Materialize node-export views from dimension and fact/bridge tables.
3. Materialize relationship-export views directly from the semantic bridges.
4. Keep node payloads compact: identifiers, labels, key business attributes, and URLs only.
5. Version the ontology scope with the semantic model so graph paths stay aligned with business definitions.

## 4. Example business questions the semantic model answers

1. How many open tickets are currently assigned to each support group, and which priorities dominate the backlog?
2. What is the average resolution time for Database / SQL Performance incidents this month?
3. Which business services have the highest SLA breach count over the last 30 days?
4. Which categories generate the most follow-up-required tickets?
5. Which KB articles are reused most often for critical or high-priority incidents?
6. What resolution patterns appear most frequently for Identity and Access incidents?
7. Which assignment groups are carrying the oldest open tickets by aging bucket?

## 5. Example graph traversal questions the ontology supports

1. Starting from a ticket, which KB articles, change requests, and supporting files are connected to it?
2. Which other tickets resolved by the same resolution pattern also impacted the same business service?
3. For a given support group, which categories and services are most commonly linked through resolved tickets?
4. Which tickets tied to a planned change also reference the same KB article?
5. What attachments, images, or documents support tickets in the same category as a selected incident?

## 6. Guidance on when to split into sub-models

Split the model when one or more of these conditions appears:

1. **User intent diverges:** operational backlog/SLA users need different objects than knowledge-reuse or asset-reference users.
2. **Bridge growth overwhelms the star:** too many many-to-many paths make Data Agent answers ambiguous or slow.
3. **Measure catalog exceeds business clarity:** when the model needs more than roughly 25 actively used measures or multiple conflicting definitions for the same KPI.
4. **Attachment and document analysis becomes first-class:** move asset-heavy analytics into a separate evidence/reference model.
5. **Change-impact analysis broadens:** create a dedicated change and service-impact model once changes, outages, and CMDB services grow beyond ticket support scope.

Recommended split path if needed:

- **Core Support Operations Model:** tickets, dates, users, groups, category, priority, state, SLA
- **Knowledge and Resolution Model:** KB reuse, resolution patterns, historical support content
- **Asset and Reference Model:** attachments, documents, images, external references

## 7. Fabric Data Agent configuration guidance

1. Point the Fabric Data Agent at the published semantic model, not raw tables.
2. Expose only business-friendly dimensions, measures, and ticket identifiers; hide bridge-table internals and long narrative text.
3. Add rich descriptions and synonyms:
   - `Ticket Volume`: incidents, tickets, case count
   - `Open Ticket Count`: active incidents, unresolved tickets, backlog
   - `Assignment Group`: support team, resolver group
   - `Business Service`: application, platform, supported service
4. Mark `Ticket Volume`, `Open Ticket Count`, `Avg Resolution Time (Hours)`, `SLA Breach Count`, `Reopen Rate`, `Resolution Pattern Frequency`, and `KB Article Reuse Count` as preferred question-answering measures.
5. Keep the Data Agent scoped to structured questions: counts, trends, priorities, groups, categories, services, SLA, and KB reuse.
6. Do not route narrative resolution-note retrieval, attachment content inspection, or image understanding into the Data Agent; those belong to retrieval and asset tool paths.
7. Add sample questions during agent setup:
   - "How many critical tickets are open by assignment group?"
   - "What is the average resolution time for Database incidents this week?"
   - "Which KB articles are reused most for VPN tickets?"
   - "How many tickets breached SLA for the Operations IT group?"
8. If `Reopen Rate` is still based on a partial derived signal, label it clearly in the semantic model description so the agent does not overstate certainty.

## 8. Implementation notes

1. Prefer import mode for the POC unless Fabric capacity and freshness needs justify Direct Lake.
2. Add sort-by columns for priority, state grouping, and aging buckets.
3. Use hidden surrogate keys and expose friendly labels only.
4. Keep descriptions on every measure and dimension attribute that the Data Agent will see.
5. Validate the model with both visual slicing and natural-language test questions before publishing the ontology layer.
