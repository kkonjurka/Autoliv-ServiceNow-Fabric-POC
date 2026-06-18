# Three-Path Agent Architecture

## Purpose

Use this pattern when a support-oriented POC mixes structured operational data, unstructured narrative text, and attachment or document references.

## Pattern

Split the architecture into three explicit answer paths:

1. **Structured path** for normalized entities, measures, filters, and operational questions.
2. **Unstructured path** for cleaned text, semantic similarity, and narrative evidence retrieval.
3. **Reference path** for attachments, images, documents, logs, scripts, URLs, and metadata-first lookups.

## Why

This prevents overloading a structured data agent with text-heavy and file-heavy tasks, preserves grounded references, and keeps responsibilities clear across the semantic model, retrieval layer, and document tooling.

## Apply When

- A Fabric Data Agent or BI semantic layer is part of the solution.
- HTML-like notes or KB content must be searchable.
- Attachments or documents exist but should not be forced into the semantic model.

## Expected Outputs

- A routing-aware orchestrator design
- Separate storage and retrieval responsibilities
- Clear mock-vs-production boundaries for each path
