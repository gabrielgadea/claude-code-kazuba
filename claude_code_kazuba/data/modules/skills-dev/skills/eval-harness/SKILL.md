---
name: eval-harness
description: |
  Evaluation-driven development framework. Define measurable criteria, create
  a test harness, measure before/after. Use when quality must be quantified,
  not just asserted.
version: "1.0.0"
author: "Gabriel Gadea"
tags: ["evaluation", "measurement", "quality", "tdd"]
triggers:
  - "create eval"
  - "measure quality"
  - "eval harness"
  - "benchmark before after"
  - "criar avaliacao"
  - "medir qualidade"
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
context: main
---

# Eval Harness

## When to Use

- Optimizing performance (latency, throughput, memory)
- Improving output quality (accuracy, relevance, completeness)
- Comparing approaches objectively
- Validating that a refactor does not degrade behavior

## Core Principle

> If you cannot measure it, you cannot improve it.
> If you did not measure before, you cannot prove you improved it.

## Workflow

### Step 1: Define Evaluation Criteria

Write down exactly what "better" means. Be specific and measurable.

```yaml
eval_criteria:
  - name: latency_p95
    metric: milliseconds
    baseline: null  # Will be measured
    target: "<100ms"
    weight: 0.4

  - name: accuracy
    metric: percentage
    baseline: null
    target: ">95%"
    weight: 0.4

  - name: memory_peak
    metric: megabytes
    baseline: null
    target: "<512MB"
    weight: 0.2
```

### Step 2: Create Test Corpus

Build a representative dataset for evaluation. Requirements:
- Minimum 20 test cases (statistical significance)
- Cover happy path, edge cases, and failure modes
- Include known-answer cases for accuracy measurement
- Save as reproducible fixture (JSON, CSV, or pytest fixture)

### Step 3: Measure Baseline

Run the current implementation against the test corpus:

```python
import time
import tracemalloc

def measure_baseline(test_corpus, implementation):
    results = []
    for case in test_corpus:
        tracemalloc.start()
        start = time.perf_counter()

        output = implementation(case.input)

        elapsed = time.perf_counter() - start
        _, peak_mem = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        results.append({
            "case_id": case.id,
            "latency_ms": elapsed * 1000,
            "memory_mb": peak_mem / 1024 / 1024,
            "correct": output == case.expected,
        })
    return results
```

Record baseline: `eval_results/baseline_{timestamp}.json`

### Step 4: Implement Changes

Make your optimization/improvement. Keep changes atomic and testable.

### Step 5: Measure After

Run the same test corpus with the new implementation.
Record: `eval_results/after_{timestamp}.json`

### Step 6: Compare and Report

```
EVAL REPORT: {description}
================================
Criteria        | Baseline  | After     | Target    | Status
----------------|-----------|-----------|-----------|-------
latency_p95     | 145ms     | 82ms      | <100ms    | PASS
accuracy        | 91.3%     | 96.1%     | >95%      | PASS
memory_peak     | 489MB     | 512MB     | <512MB    | PASS

Weighted Score: 0.87 -> 0.95 (+9.2%)
VERDICT: IMPROVEMENT VALIDATED
```

## Scoring Formula

```
score = sum(criterion.weight * normalize(criterion.value, criterion.target))
```

Where `normalize` maps the value to [0, 1] relative to the target:
- At target = 1.0
- Double the target (bad direction) = 0.0
- Half the target (good direction) = 1.0 (capped)

## Anti-Patterns

- **Measuring one, optimizing another**: If you measure latency but your target is accuracy, you will optimize the wrong thing.
- **Too few test cases**: 3 cases is not a benchmark, it is an anecdote.
- **Ignoring variance**: Report p50, p95, p99 — not just mean.
- **Optimizing without baseline**: "It feels faster" is not data.
- **Cherry-picking results**: Use the full corpus, not just cases that improved.
