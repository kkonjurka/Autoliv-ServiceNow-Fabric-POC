# Autoliv ServiceNow to Microsoft Fabric — Show & Tell Preparation
## Stakeholder Presentation Guide

**Prepared:** June 24, 2026
**Event:** POC Show-and-Tell with Autoliv Stakeholders
**Presenter:** Microsoft POC Team
**Audience:** Mix of Autoliv business and technical stakeholders

---

## 1. Talk Track — What to Say at Each Stage

Use this section as speaker notes. The goal is to narrate a coherent story, not just click through screens.

### Opening (2 minutes)

> "Today we're going to show you something we built specifically around the kinds of data and support challenges that came up in our conversations with Autoliv. Before I get into the demo, I want to set the stage so you understand what you're looking at — because this is not a canned product demo. We actually built this.
>
> The challenge we were trying to solve is a common one in large enterprises: your IT support teams know what happened three months ago when the VPN went down, but that knowledge lives in a combination of ServiceNow tickets, KB articles, work notes, and the heads of a few senior engineers. Every new incident that looks similar starts from scratch.
>
> What we've built here is an AI-assisted architecture that brings that knowledge together — structured analytics, historical resolution content, documents and attachments — and lets an IT support engineer ask a natural-language question and get a grounded, cited answer in seconds. Let me show you how it works."

### Transition to Architecture (1 minute)

> "Before we dive into the demo, here's the shape of what we built. [Show diagram.] There are three layers.
>
> First, the data layer — Microsoft Fabric, where we've ingested, cleaned, and shaped the ServiceNow data into curated tables, a semantic model, and a retrieval corpus.
>
> Second, the intelligence layer — a Fabric Data Agent for structured questions, Azure AI Search for historical content, and an asset tool for attachments and documents.
>
> Third, the orchestration layer — an Azure AI Foundry agent that figures out which tool to call, combines the results, and gives you a cited, grounded answer.
>
> One thing I want to call out up front: the database you're about to see is SQLite — it's a demo stand-in for your real ServiceNow system. Everything else — the Fabric Lakehouse, the semantic model, the Fabric Data Agent, the Foundry agent — is the real thing. Let's look at the source first."

### Closing (2 minutes)

> "So what you've just seen is a working proof of concept of a pattern that can scale to your real ServiceNow environment. The SQLite stand-in gets replaced by your real ServiceNow API. The mock data gets replaced by your actual ticket history. The Fabric assets we've built — the semantic model, the Data Agent, the ontology — those are the real deliverables that carry forward.
>
> The path from here is: validate this against your real data, tune the retrieval with your actual KB articles and resolution history, and put it in front of two or three support engineers to see if the answers are useful. That's the pilot.
>
> We have a set of questions we'd like to resolve with your team before the pilot starts. We can walk through those now, or we can take questions on what you've seen first."

---

## 2. Demo Script — 10-Step Flow

### Step 1: Show the Mock API and Explain the SQLite Stand-In

**What to show:** Open a browser to the live API at:
`https://aca-servicenow-mock-api.delightfulbush-6b8b9877.eastus.azurecontainerapps.io/health`

Then show:
- `/incidents?state=open&priority=1` — returns open critical tickets
- `/incidents/{id}` — single incident with nested notes, KB links, change requests
- `/kb-articles` — knowledge base articles with HTML content

**What to say:**
> "This is the mock ServiceNow API we built. It's containerized, running on Azure Container Apps, and accessible over public HTTPS. Behind it is a SQLite database with 32 incidents and 8 KB articles seeded with realistic ServiceNow-style data — open and closed tickets, work notes, resolution summaries, SLA records, attachments, and change requests.
>
> SQLite is just a POC convenience — it lets us stand up a ServiceNow-shaped API in minutes without requiring access to your live environment. In a real deployment, this is replaced by direct ServiceNow API ingestion. The shape of the data — the fields, the nesting, the pagination — mirrors what we'd get from ServiceNow. That's what matters."

---

### Step 2: Show Fabric Ingestion

**What to show:** In Fabric, open the `01_ingest_raw.py` notebook. Show the API call pattern, pagination loop, and raw JSON landing in `Files/raw/servicenow/`.

**What to say:**
> "This Fabric notebook calls the API, paginates through all the endpoints, and lands raw JSON exactly as it came back — no transformations yet. You'll see incidents, KB articles, attachments, images, documents — everything. Each ingestion run creates a manifest entry so we know what was pulled and when. In a production setup this becomes a scheduled pipeline with incremental ingestion."

---

### Step 3: Show Curated Tables

**What to show:** Open the Fabric Lakehouse and navigate to the Delta tables. Show `incidents`, `users`, `assignment_groups`, `categories`, `kb_articles`, `slas`, `work_notes`, `resolution_notes`, `incident_kb_links`.

**What to say:**
> "The transform notebook takes that raw JSON and normalizes it into 15 relational Delta tables. Every nested collection — work notes, resolution notes, SLA records, KB links — gets unpacked into its own table with proper foreign keys. This is your governed data layer. Everything downstream — the semantic model, the search index, the ontology — is built from these curated tables, not from the raw API payload."

---

### Step 4: Show Cleaned Text

**What to show:** Show the `retrieval_documents` table. Highlight the `clean_text` column next to `html_source`. Show a few rows with stripped HTML versus the original formatted content. Optionally open the `03_html_to_text.py` notebook.

**What to say:**
> "ServiceNow stores a lot of its narrative content as HTML — KB article bodies, work notes, resolution summaries. We run a cleaning pass that strips the markup and produces plain text that the search index can actually use. We keep both — the original HTML for fidelity, and the cleaned text for retrieval. This `retrieval_documents` table is the unified corpus that feeds Azure AI Search. One row per indexable artifact: incident descriptions, resolution summaries, work notes, and full KB article content."

---

### Step 5: Show the Semantic Model and Measures

**What to show:** Open the Fabric semantic model. Show the diagram view with `FactTickets`, `FactSla`, dimension tables, and bridge tables. Click into a few measures — `Open Ticket Count`, `SLA Breach Count`, `Avg Resolution Time (Hours)`.

**What to say:**
> "This is the semantic model — the business-friendly layer that sits above the curated tables. It's a star schema with a central ticket fact table, SLA facts, and a set of dimensions for date, user, assignment group, category, priority, and state. The measures are what make the Fabric Data Agent useful. Instead of writing DAX, the agent reads the measure definitions and uses them to answer natural-language questions. When a support engineer asks 'how many high-priority tickets are open for the Network team?' — the agent knows exactly which measures and filters to apply."

---

### Step 6: Show the Ontology

**What to show:** Open the ontology notebook output. Show the `ontology_nodes` and `ontology_edges` Delta tables. Optionally show a small NetworkX graph visualization. Highlight a few rows that show how `Incident → REFERENCES_KB → KnowledgeArticle` and `Incident → RESOLVED_BY_PATTERN → ResolutionPattern` are represented.

**What to say:**
> "Beyond the semantic model, we built an ontology — a graph of how business entities relate to each other. Where the semantic model answers 'how many,' the ontology answers 'how are things connected.' You can traverse from a ticket to the KB articles cited in its resolution, to other tickets that used the same resolution pattern, to the support group that owns those tickets. This is what gives the AI agent the ability to reason across entities, not just aggregate columns."

---

### Step 7: Ask the Fabric Data Agent a Structured Question

**What to show:** Open the Fabric Data Agent. Ask:
> "How many open tickets are assigned to each support group, and which group has the most high-priority incidents?"

Show the response — a table or narrative answer with group names, counts, and priority breakdowns.

**What to say:**
> "Here's the Fabric Data Agent. It's connected directly to the semantic model we just saw. I've asked it a structured operational question — the kind of thing a team lead or support manager might want to know at the start of the day. Notice how it uses the measures and dimensions we defined: open ticket count, assignment group, priority. It didn't write SQL. It reasoned over the semantic model and gave back a structured, grounded answer."

---

### Step 8: Ask a Historical Ticket Question via the Foundry Orchestrator

**What to show:** Switch to the Azure AI Foundry agent. Ask:
> "Find similar historical tickets to VPN timeout errors and summarize how they were resolved."

Show the agent routing to the search tool, returning similar incident snippets with resolution summaries and source IDs.

**What to say:**
> "Now I'm asking a different type of question — not 'what's the count' but 'what happened before.' This is the Foundry orchestrator at work. It classified this question as a retrieval task and called the Azure AI Search tool, not the Fabric Data Agent. The search index contains the cleaned text from all our resolution notes, work notes, and incident descriptions. It found several historically similar tickets, pulled the resolution summaries, and synthesized a response. Notice the citations — each claim is backed by a specific incident ID."

---

### Step 9: Ask for KB Articles and Document References

**What to show:** Ask the Foundry orchestrator:
> "Are there any knowledge base articles or documents related to SAP login failures? Include any relevant attachments."

Show the agent calling both the search tool (for KB text) and the asset tool (for attachments), then combining results.

**What to say:**
> "Now we're asking a mixed question — KB content and file references. The orchestrator recognized this needs two tools: search retrieval for the KB article text, and the asset tool for attachments tied to matching tickets. Here you can see it calling both in sequence and merging the results. The KB article is cited with its article ID; the attachment is cited with its file metadata and URL. In production, those URLs would resolve to real documents in your content store."

---

### Step 10: Show the Full Orchestrated Response and Production Path

**What to show:** Ask the orchestrator a full recommendation question:
> "Based on the current open critical ticket about network connectivity in the Chicago plant, suggest a likely resolution path and include supporting evidence."

Show the full structured response: direct answer, supporting evidence from Fabric + search, references with source IDs, and a confidence/human-review note.

Then switch to the architecture diagram and briefly walk the production upgrade path.

**What to say:**
> "This is the full orchestrator at work. It called the Fabric Data Agent for the current ticket's state, priority, and SLA risk. It called AI Search for similar historical incidents and resolution patterns. It assembled a recommended resolution path, cited every claim, and — importantly — it ends with a human review note. The agent never implies an action has been taken. It gives a recommendation; a support engineer makes the decision.
>
> The production path from here is: connect to your real ServiceNow API, ingest your actual ticket history, and tune the retrieval with your real KB articles. The Fabric assets — the Lakehouse, the semantic model, the Data Agent — carry forward directly. We've already built the foundation."

---

## 3. Expected Questions and Answers

### Q1: Why SQLite? That's not production-ready.

**A:** Correct — and we'd never recommend SQLite for production. It's a POC convenience that let us build and demo a ServiceNow-shaped API without requiring access to your live system. Every other piece of the architecture — the Fabric Lakehouse, semantic model, Data Agent, Foundry agent — is built exactly as it would be in production. The SQLite API gets replaced by a direct ServiceNow API connection in the pilot phase.

---

### Q2: Can you connect directly to our ServiceNow instance?

**A:** Yes. The POC is designed specifically so that the mock API layer is the only thing that changes. The Fabric ingestion notebooks call an HTTPS endpoint and ingest the JSON response — the same pattern works whether that endpoint is our mock API or your real ServiceNow. We'd need read-only API credentials, agreement on which endpoints and fields to pull, and alignment on the API version you're running.

---

### Q3: What ServiceNow data does this use? Does it cover our custom fields?

**A:** The POC covers the standard ServiceNow data shapes — incidents, users, groups, categories, KB articles, work notes, SLAs, change requests, and attachments. Custom fields and extended tables require a mapping exercise. One of our first steps in the pilot would be to review your actual ServiceNow schema and map custom fields into the curated model.

---

### Q4: How current is the data? Is this real-time?

**A:** The POC runs on manually triggered ingestion — we pull the data and it's current at the time of the run. In production, you'd run scheduled incremental ingestion: new and updated tickets pulled every 15–60 minutes depending on your SLA requirements. True real-time streaming is possible but adds complexity and is typically not necessary for support resolution scenarios.

---

### Q5: What happens to sensitive data — PII, security incidents?

**A:** Great question, and an important one for the pilot design. Microsoft Fabric supports row-level security, sensitivity labels, and access-controlled workspaces. In production, we'd apply classification to sensitive fields, restrict retrieval indices to appropriate audience scopes, and ensure the Foundry agent only surfaces data the requesting user is authorized to see. This is a design requirement for the pilot, not an afterthought.

---

### Q6: How accurate are the AI answers? Can it hallucinate?

**A:** The architecture is specifically designed to minimize hallucination through grounding. The Fabric Data Agent answers from a defined semantic model — it cannot invent measures that don't exist. The search tool returns actual text from actual records and cites source IDs. The Foundry orchestrator is instructed never to answer from memory when a tool can provide evidence, and to say so explicitly when evidence is weak or missing. No system is zero-risk, which is why every suggested resolution includes a human review note.

---

### Q7: What does the support engineer's UI look like?

**A:** In this POC, we're demonstrating through the Foundry agent interface and the Fabric Data Agent UI. In production, the Foundry agent can be surfaced through Microsoft Copilot Studio, a Teams bot, a custom web interface, or embedded in ServiceNow itself via the ServiceNow integration framework. The agent API is consistent regardless of the surface.

---

### Q8: How does this compare to ServiceNow's own AI features?

**A:** ServiceNow Now Assist and Virtual Agent are strong within the ServiceNow platform. This architecture is complementary — it brings ServiceNow data into Microsoft Fabric where it can be enriched, combined with data from other Microsoft systems, and reasoned over using enterprise AI capabilities in Foundry. If Autoliv is already licensing ServiceNow AI features, the right conversation is which questions belong in-platform vs. which need cross-system context.

---

### Q9: Who maintains this after the POC?

**A:** The Fabric assets (Lakehouse, semantic model, Data Agent) are managed through the standard Microsoft Fabric governance experience — Fabric workspaces, Git integration, and deployment pipelines. The Foundry agent is deployed in Azure AI Foundry with version-controlled prompt and tool configurations. A small Fabric-literate team — similar to what you'd have for Power BI governance — can own ongoing maintenance. We'd document the runbook and support the handover.

---

### Q10: How does this scale to 10× the ticket volume?

**A:** Microsoft Fabric is elastic by design. The Lakehouse and semantic model scale with Fabric capacity — you'd increase capacity SKU and potentially move to Direct Lake mode for larger datasets. Azure AI Search scales independently of Fabric. The Foundry orchestrator scales as an Azure resource. We'd size based on your actual incident volumes and query concurrency during the pilot.

---

### Q11: Can this handle attachments — actual files, not just metadata?

**A:** The POC demonstrates metadata-first asset handling: file names, types, descriptions, sizes, and mock URLs. Actual file content processing — OCR on scanned documents, log parsing, script execution — requires additional pipeline work. The architecture has a dedicated asset tool path specifically designed to grow into full content processing. For the pilot, metadata plus URL references is typically sufficient for support engineers who can open the actual file with one click.

---

### Q12: How does the ontology help versus just having the semantic model?

**A:** The semantic model is optimized for aggregation — counts, averages, breach rates. The ontology is optimized for traversal — given this ticket, what else is connected to it? The ontology answers questions like "which other tickets were resolved by the same pattern?" or "which KB articles are most connected to tickets assigned to Network Support?" These are graph questions, not SQL questions. Together they cover both analytical and relational reasoning.

---

### Q13: What's the cost of running this in production?

**A:** The main cost drivers are: Fabric capacity (F-SKU, billed by compute hours), Azure AI Search (scale tier × query volume), Azure AI Foundry / Azure OpenAI (token consumption per query), and Azure Container Apps if you keep a mock or proxy layer. We can run a cost model once we know your approximate ticket volume, query frequency, and history depth. The POC runs on minimal capacity tiers.

---

### Q14: Can the agent take action — close a ticket, send a notification?

**A:** Not in the POC, by design. The architecture keeps the agent in a read-and-recommend posture. Adding write-back actions — closing tickets, triggering workflows, sending notifications — is technically feasible through ServiceNow's REST API or Power Automate connectors, but requires additional human-in-the-loop controls, audit logging, and approval workflows. That would be a Phase 3 capability once the read-and-recommend pattern is validated.

---

### Q15: How do you handle tickets that don't have good historical precedent?

**A:** The orchestrator is designed to say so explicitly. If the search tool returns low-confidence or sparse results, the agent reports that directly and flags the ticket for human review rather than fabricating a plausible-sounding answer. This is a guardrail built into the Foundry agent system instructions. "We don't have strong historical precedent for this issue" is a valid and useful answer.

---

### Q16: What Microsoft licenses do we need?

**A:** At minimum: a Microsoft Fabric capacity (F2 or above for development, F4+ recommended for production workloads), Azure AI Foundry / Azure OpenAI deployment, and Azure AI Search (standard tier for production). If you're an existing Microsoft 365 customer with Copilot licensing, there may be entitlement overlap worth reviewing with your Microsoft account team.

---

## 4. Risks and Limitations — Honest Disclosure

Be transparent about the following. Stakeholders respect honesty more than overselling.

### What this POC is

- A working end-to-end demonstration of the target architecture
- Built on real Fabric, real Foundry, and real Azure AI Search assets
- Using a realistic mock dataset shaped like ServiceNow data
- Designed to be extended directly to real ServiceNow ingestion

### What this POC is not

- A production-ready system
- Connected to Autoliv's live ServiceNow environment
- Tested against Autoliv's actual data volumes, custom fields, or support workflows
- Hardened for security, access control, or compliance requirements
- Tuned for Autoliv's specific resolution vocabulary and KB content

### Known limitations to disclose

| Limitation | Honest framing |
|---|---|
| SQLite data source | A POC stand-in only — not the target architecture. Everything except the data source is production-pattern. |
| 32 incidents / 8 KB articles | Small dataset sufficient for demonstrating the architecture; retrieval accuracy improves significantly with real volume. |
| No real-time ingestion | Manual trigger in the POC; production would require scheduled incremental pipelines. |
| No access controls | Row-level security and role-based access not applied in the POC; required for production. |
| Mock attachment URLs | Files don't actually exist behind the URLs — metadata only in the POC. |
| Retrieval accuracy | AI Search relevance has not been tuned with Autoliv's actual vocabulary, incident language, or KB content. Expect improvement after real-data calibration. |
| Reopen rate measure | The semantic model includes this measure but flags it as preview — the reopen signal in the mock data is derived, not a native ServiceNow field. |
| Cost estimates not finalized | Actual cost depends on Autoliv's data volumes and query patterns, which we have not yet measured. |

### What could go wrong in production

- **ServiceNow API changes** break ingestion if not handled with schema versioning
- **Data quality issues** in historical tickets (missing fields, inconsistent resolution text) will reduce retrieval accuracy
- **Access control complexity** may require custom row-level security logic for sensitive incident categories
- **Model drift** — as ServiceNow data patterns change, the semantic model measures and retrieval relevance will need periodic recalibration

---

## 5. Recommended Next Steps After the Show-and-Tell

### Immediate (within 1 week)

- [ ] Schedule a technical discovery session: ServiceNow API version, available fields, custom tables, and authentication method
- [ ] Share this documentation with the Autoliv technical team for review and feedback
- [ ] Agree on the pilot scope: which support team, which ticket categories, which time horizon of history

### Short-term (2–4 weeks)

- [ ] Establish read-only ServiceNow API access for a scoped pilot environment
- [ ] Review Autoliv's existing KB article structure and identify which namespaces are in scope
- [ ] Identify any existing Fabric or Power BI workspaces to determine where pilot assets should land
- [ ] Confirm Microsoft licensing status (Fabric capacity, Azure AI, Azure OpenAI)

### Pilot (4–8 weeks)

- [ ] Ingest 90–180 days of real incident history from the pilot support team
- [ ] Align the semantic model dimensions to Autoliv's actual support group, category, and service terminology
- [ ] Index real KB articles and resolution notes; evaluate retrieval relevance with real support engineers
- [ ] Run a structured user acceptance test: 3–5 support engineers, 20+ representative questions
- [ ] Collect feedback and produce a go/no-go recommendation for production

### Questions to answer before pilot starts

1. Who is the Autoliv technical owner for this initiative?
2. What is the approval process for read-only ServiceNow API access?
3. Are there data sensitivity requirements that constrain which tickets can be ingested?
4. Is there a preferred Azure region for Fabric and Azure AI resources?
5. What does success look like at the end of the pilot — a specific MTTR reduction, agent adoption rate, or stakeholder sign-off?

---

*Live mock API: `https://aca-servicenow-mock-api.delightfulbush-6b8b9877.eastus.azurecontainerapps.io`*

*For technical questions or to schedule a discovery session, contact the Microsoft POC team.*
