"""
RAG Retrieval Benchmark — Karl Workbench
==========================================
Compares retrieval quality metrics on a fixed query set.
Does NOT require the LLM to be loaded — pure embedding + search benchmark.

Usage:
  python eval/benchmark_rag.py
  python eval/benchmark_rag.py --top-k 5 --headers

The benchmark uses an internal synthetic corpus. To test your own documents,
ingest them first via the UI and run with --live flag to query the live index.
"""

import os
import sys
import time
import textwrap
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.rag_pipeline import RAGPipeline


# ── Synthetic benchmark corpus ────────────────────────────────────────────────
# Small, controlled corpus so the benchmark is reproducible without loading files.

CORPUS = [
    ("doc_a", "The quarterly revenue for Q3 2025 was $42 million, up 18% from Q3 2024."),
    ("doc_a", "Operating expenses for Q3 2025 totaled $28 million including $5M in R&D."),
    ("doc_a", "The company expects Q4 2025 revenue between $45M and $48M."),
    ("doc_b", "The return policy allows 30-day returns for most items with original receipt."),
    ("doc_b", "Electronics must be returned within 15 days and must be in original packaging."),
    ("doc_b", "Gift cards and downloadable software are non-refundable under any circumstances."),
    ("doc_c", "CEO Sandra Holt joined Meridian Technologies in 2019 from a rival cloud firm."),
    ("doc_c", "CTO Marcus Webb leads a team of 200 engineers across Austin and Seattle offices."),
    ("doc_c", "Meridian's flagship product, CloudShield, serves 3,200 enterprise customers."),
    ("doc_d", "Patient Maria Gonzalez was admitted on April 1 with community-acquired pneumonia."),
    ("doc_d", "Attending physician Dr. Samuel Okafor prescribed amoxicillin-clavulanate 875mg."),
    ("doc_d", "Patient was discharged April 5 with follow-up scheduled in two weeks."),
]

# Each query: (query_text, list_of_expected_chunk_indices_in_CORPUS)
BENCHMARK_QUERIES = [
    ("What was Q3 2025 revenue?",                  [0, 1]),
    ("What is the return window for electronics?",  [4]),
    ("Who is the CEO of Meridian?",                 [6]),
    ("What medication was the patient given?",      [10]),
    ("What are Q4 revenue projections?",            [2]),
    ("Are gift cards refundable?",                  [5]),
    ("Where are Meridian's engineering offices?",   [7]),
    ("When was the patient discharged?",            [11]),
]


@dataclass
class QueryResult:
    query: str
    hit_at_1: bool
    hit_at_3: bool
    hit_at_k: bool
    reciprocal_rank: float
    latency_ms: float


def run_benchmark(top_k: int = 3, contextual_headers: bool = False) -> list[QueryResult]:
    print(f"\n{'─'*60}")
    print(f"  Karl RAG Retrieval Benchmark")
    print(f"  top_k={top_k} | contextual_headers={contextual_headers}")
    print(f"{'─'*60}")

    # Build a fresh in-memory RAG index (does NOT touch the persisted index)
    rag = RAGPipeline(contextual_headers=contextual_headers)
    rag.index.reset()  # Start fresh — don't load persisted
    rag.documents = []

    # Ingest synthetic corpus via ingest_text
    print(f"\n  Ingesting {len(CORPUS)} synthetic chunks...")
    for source, text in CORPUS:
        # Ingest as single-chunk items (don't split these short sentences further)
        from sentence_transformers import SentenceTransformer
        import numpy as np
        vec = rag.encoder.encode([text]).astype("float32")
        rag.index.add(vec)
        rag.documents.append({
            "text": text,
            "source_file": source,
            "chunk_id": len(rag.documents),
            "ingested_at": "benchmark",
        })

    print(f"  Index size: {rag.index.ntotal} vectors\n")

    results = []
    for query, expected_ids in BENCHMARK_QUERIES:
        t0 = time.perf_counter()
        metrics = rag.eval_retrieval(query, expected_chunk_ids=expected_ids, top_k=top_k)
        latency_ms = (time.perf_counter() - t0) * 1000

        results.append(QueryResult(
            query=query,
            hit_at_1=metrics["hit_at_1"],
            hit_at_3=metrics["hit_at_3"],
            hit_at_k=metrics["hit_at_k"],
            reciprocal_rank=metrics["reciprocal_rank"],
            latency_ms=round(latency_ms, 1),
        ))

    return results


def print_results(results: list[QueryResult], top_k: int):
    bar = "─" * 60
    print(f"\n  Per-query results (top_k={top_k}):\n")
    print(f"  {'Query':<42} H@1  H@3  H@k   MRR   ms")
    print(f"  {'─'*42} ─── ─── ─── ─────  ─────")

    for r in results:
        q_short = textwrap.shorten(r.query, 40, placeholder="…")
        h1  = "✓" if r.hit_at_1 else "✗"
        h3  = "✓" if r.hit_at_3 else "✗"
        hk  = "✓" if r.hit_at_k else "✗"
        print(
            f"  {q_short:<42} {h1:<3}  {h3:<3}  {hk:<3}  "
            f"{r.reciprocal_rank:.3f}  {r.latency_ms:.0f}"
        )

    n = len(results)
    mrr  = sum(r.reciprocal_rank for r in results) / n
    h1   = sum(r.hit_at_1 for r in results) / n
    h3   = sum(r.hit_at_3 for r in results) / n
    hk   = sum(r.hit_at_k for r in results) / n
    avg_ms = sum(r.latency_ms for r in results) / n

    print(f"\n  {bar}")
    print(f"  Aggregate ({n} queries):")
    print(f"    Hit@1   : {h1:.1%}")
    print(f"    Hit@3   : {h3:.1%}")
    print(f"    Hit@k   : {hk:.1%}")
    print(f"    MRR     : {mrr:.3f}")
    print(f"    Avg lat : {avg_ms:.0f}ms")
    print(f"  {bar}\n")

    return {"hit_at_1": h1, "hit_at_3": h3, "hit_at_k": hk, "mrr": mrr}


def main():
    import argparse
    p = argparse.ArgumentParser(description="Karl RAG retrieval benchmark")
    p.add_argument("--top-k", type=int, default=3, help="Retrieval cutoff (default: 3)")
    p.add_argument("--headers", action="store_true", help="Enable contextual chunk headers")
    p.add_argument("--compare", action="store_true", help="Run twice: without vs with headers, compare")
    args = p.parse_args()

    if args.compare:
        print("\n  === Run 1: No contextual headers ===")
        r1 = run_benchmark(top_k=args.top_k, contextual_headers=False)
        m1 = print_results(r1, args.top_k)

        print("\n  === Run 2: With contextual headers ===")
        r2 = run_benchmark(top_k=args.top_k, contextual_headers=True)
        m2 = print_results(r2, args.top_k)

        print("\n  === Delta (headers vs no headers) ===")
        for metric in ("hit_at_1", "hit_at_3", "hit_at_k", "mrr"):
            delta = m2[metric] - m1[metric]
            sign  = "+" if delta >= 0 else ""
            print(f"    {metric:<12}: {sign}{delta:.3f}")
        print()
    else:
        results = run_benchmark(top_k=args.top_k, contextual_headers=args.headers)
        print_results(results, args.top_k)


if __name__ == "__main__":
    main()
