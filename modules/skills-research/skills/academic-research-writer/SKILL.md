---
name: academic-research-writer
description: |
  Academic writing skill with peer-reviewed sources, IEEE citation format,
  and a 7-step workflow from topic definition to final review.
version: "1.0.0"
author: "Gabriel Gadea"
tags: ["research", "academic", "writing", "citations"]
triggers:
  - "academic paper"
  - "research paper"
  - "write paper"
  - "IEEE format"
  - "artigo academico"
  - "escrever artigo"
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, WebSearch, WebFetch
context: main
---

# Academic Research Writer

## When to Use

- Writing technical reports or white papers
- Producing research summaries with verifiable sources
- Creating documentation that requires citation rigor
- Any output where credibility depends on sourcing

## 7-Step Workflow

### Step 1: Topic Definition

Define the research question precisely:
- **Topic**: One sentence describing the subject area.
- **Research Question**: Specific, answerable question.
- **Scope**: What is included and excluded.
- **Audience**: Who will read this and what they already know.

### Step 2: Source Discovery

Search for peer-reviewed and authoritative sources:
- Academic databases (Google Scholar, IEEE Xplore, ACM DL, arXiv)
- Official documentation and specifications
- Reputable technical blogs and conference proceedings
- Government and standards body publications

**Minimum sources**: 5 for a short paper, 15+ for a comprehensive review.

### Step 3: Source Verification

For each source, verify:
- [ ] Published in a peer-reviewed venue OR is official documentation
- [ ] Publication date is within relevance window (usually < 5 years)
- [ ] Author has identifiable credentials
- [ ] Claims are supported by data or formal proof
- [ ] Source is accessible (URL works, DOI resolves)

**Red flags**: No author, no date, no references, predatory journal, broken links.

### Step 4: Outline Construction

Build a structured outline following academic conventions:
1. Abstract (150-300 words)
2. Introduction (context, motivation, contribution)
3. Background / Related Work
4. Methodology / Approach
5. Results / Findings
6. Discussion
7. Conclusion
8. References

### Step 5: Draft Writing

Write each section following these rules:
- **Claims require citations**: Every factual claim must reference a source.
- **No unsupported opinions**: If you believe something, find evidence.
- **Active voice preferred**: "We propose" not "It is proposed".
- **Precise language**: Avoid "very", "many", "significant" without quantification.
- **One idea per paragraph**: Topic sentence, evidence, analysis.

### Step 6: Citation Formatting (IEEE)

Use IEEE numeric citation style:

**In-text**: `[1]`, `[2, 3]`, `[4]-[7]`

**Reference list**:
```
[1] A. Author, "Title of article," Journal Name, vol. X, no. Y, pp. Z-W, Month Year.
[2] B. Author and C. Author, "Title," in Proc. Conf. Name, City, Country, Year, pp. Z-W.
[3] D. Author, Book Title, Xth ed. City, Country: Publisher, Year.
[4] E. Author, "Title," Website Name. [Online]. Available: https://url. [Accessed: Mon. DD, YYYY].
```

### Step 7: Final Review

Checklist before submission:
- [ ] All claims have citations
- [ ] All citations appear in reference list
- [ ] All references are cited in text
- [ ] No broken links
- [ ] Abstract is self-contained
- [ ] Consistent terminology throughout
- [ ] Figures and tables are numbered and referenced
- [ ] Grammar and spell check passed
- [ ] Word count within target

## Quality Metrics

| Metric | Target |
|--------|--------|
| Citation density | >= 1 per 150 words |
| Source recency | >= 60% from last 5 years |
| Peer-reviewed ratio | >= 50% of sources |
| Self-contained abstract | Yes (no citations in abstract) |
