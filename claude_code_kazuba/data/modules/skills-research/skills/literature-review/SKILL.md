---
name: literature-review
description: |
  Systematic literature review with source verification, gap analysis, and
  synthesis. Produces a structured review covering existing work and identifying
  research opportunities.
version: "1.0.0"
author: "Gabriel Gadea"
tags: ["research", "literature", "review", "synthesis"]
triggers:
  - "literature review"
  - "systematic review"
  - "survey of"
  - "state of the art"
  - "revisao de literatura"
  - "estado da arte"
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, WebSearch, WebFetch
context: main
---

# Literature Review

## When to Use

- Before starting a new project (understand existing solutions)
- Evaluating technology choices (what has been tried, what worked)
- Writing the "Related Work" section of a paper
- Conducting due diligence on an approach

## Workflow

### Step 1: Define Scope

```yaml
review_scope:
  topic: "Exact topic description"
  research_questions:
    - "RQ1: What approaches exist for X?"
    - "RQ2: What are the trade-offs between approaches?"
    - "RQ3: What gaps remain?"
  inclusion_criteria:
    - "Published 2020-2026"
    - "Peer-reviewed or official documentation"
    - "English or Portuguese"
  exclusion_criteria:
    - "Blog posts without data"
    - "Preprints not yet peer-reviewed (unless seminal)"
  search_terms:
    - '"exact phrase" AND keyword'
    - "synonym1 OR synonym2"
```

### Step 2: Search Strategy

Execute searches across multiple sources:

| Source | Type | Search Method |
|--------|------|---------------|
| Google Scholar | Academic | Title + keyword search |
| IEEE Xplore | Academic | Advanced search with filters |
| ACM Digital Library | Academic | Full-text search |
| arXiv | Preprints | Subject area + keyword |
| GitHub | Code | Topic + stars + recent activity |
| Official docs | Primary | Direct navigation |

Record: query, source, date, number of results.

### Step 3: Screen and Select

For each result:
1. Read title and abstract.
2. Apply inclusion/exclusion criteria.
3. Rate relevance (high/medium/low).
4. Keep high + medium relevance papers.

Target: 15-30 sources for a focused review, 50+ for a comprehensive survey.

### Step 4: Extract and Catalog

For each selected source, extract:

```yaml
source:
  id: "[1]"
  title: "Paper Title"
  authors: ["A. Author", "B. Author"]
  year: 2024
  venue: "Conference/Journal Name"
  url: "https://doi.org/..."
  approach: "Brief description of the approach"
  key_findings: "Main results"
  strengths: "What it does well"
  limitations: "Known weaknesses"
  relevance: "How it relates to our research questions"
```

### Step 5: Source Verification

For each source, verify:
- [ ] DOI resolves to the actual paper
- [ ] Authors are real (check institutional affiliations)
- [ ] Venue is legitimate (check journal/conference ranking)
- [ ] Results are reproducible (if applicable)
- [ ] Citations are consistent (cross-check references)

**Never cite a paper you have not read.** If you cannot access the full text,
note it as "abstract only" and reduce its weight in your analysis.

### Step 6: Synthesize

Organize findings by theme, not by source:

```markdown
## Theme 1: [Approach Category]

Multiple studies have explored [theme]. [1] proposed X, achieving Y results.
Building on this, [2] extended the approach to handle Z. However, [3] showed
that this approach fails when [condition].

**Consensus**: ...
**Debate**: ...
**Gap**: ...
```

### Step 7: Gap Analysis

Identify what is missing:
- **Methodological gaps**: No one has tried approach X.
- **Application gaps**: Approach works in domain A but untested in B.
- **Scale gaps**: Solutions exist for small scale but not large.
- **Integration gaps**: Individual parts exist but no unified solution.

### Step 8: Output

```markdown
# Literature Review: [Topic]

## Abstract
[150-300 words summarizing scope, findings, and gaps]

## 1. Introduction
[Context, motivation, research questions]

## 2. Search Methodology
[Sources, queries, inclusion/exclusion criteria]

## 3. Findings by Theme
### 3.1 [Theme 1]
### 3.2 [Theme 2]
### 3.3 [Theme N]

## 4. Comparative Analysis
[Table comparing approaches across dimensions]

## 5. Gap Analysis
[What is missing, what needs further research]

## 6. Conclusion
[Summary, recommendations]

## References
[IEEE format]
```

## Quality Checklist

- [ ] All research questions answered
- [ ] Sources span multiple search venues
- [ ] No single source dominates the review
- [ ] Synthesis is thematic, not source-by-source
- [ ] Gaps are specific and actionable
- [ ] All sources verified
