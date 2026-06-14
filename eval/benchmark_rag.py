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


def calculate_metrics(retrieved_ids: list[int], expected_ids: list[int], top_k: int) -> dict:
    expected_set = set(expected_ids)
    hit_at_1 = bool(retrieved_ids[:1] and retrieved_ids[0] in expected_set)
    hit_at_3 = bool(any(cid in expected_set for cid in retrieved_ids[:3]))
    hit_at_k = bool(any(cid in expected_set for cid in retrieved_ids[:top_k]))
    
    rr = 0.0
    for rank, cid in enumerate(retrieved_ids[:top_k], 1):
        if cid in expected_set:
            rr = 1.0 / rank
            break
            
    return {
        "hit_at_1": hit_at_1,
        "hit_at_3": hit_at_3,
        "hit_at_k": hit_at_k,
        "reciprocal_rank": round(rr, 4)
    }


def run_code_review_benchmark(top_k: int = 3, output_path: str = "data/rag_benchmark_results.json"):
    import json
    
    dataset_path = "eval/datasets/code_review.jsonl"
    if not os.path.exists(dataset_path):
        print(f"Error: Dataset not found at {dataset_path}")
        return
    
    cases = []
    with open(dataset_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                try:
                    cases.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
                    
    print(f"\n{'─'*60}")
    print(f"  Karl RAG Retrieval Benchmark — code_review.jsonl")
    print(f"  Loaded {len(cases)} cases | top_k={top_k}")
    print(f"{'─'*60}")
    
    # Build a fresh in-memory RAG index
    rag = RAGPipeline(contextual_headers=False)
    rag.index.reset()
    rag.documents = []
    
    # Ingest contexts
    print(f"\n  Ingesting {len(cases)} code contexts...")
    for i, case in enumerate(cases):
        text = case.get("context", case.get("code", ""))
        doc_id = case.get("id", f"code_{i:03d}")
        
        vec = rag.encoder.encode([text]).astype("float32")
        rag.index.add(vec)
        rag.documents.append({
            "text": text,
            "source_file": doc_id,
            "chunk_id": len(rag.documents),
            "ingested_at": "benchmark_code_review",
        })
        
    print(f"  Index size: {rag.index.ntotal} vectors\n")
    
    modes = ["dense", "sparse", "hybrid"]
    results_by_mode = {mode: [] for mode in modes}
    query_details = []
    
    for i, case in enumerate(cases):
        query_text = case["prompt"]
        expected_ids = [i]
        
        case_info = {
            "case_id": case.get("id", f"code_{i:03d}"),
            "query": query_text,
            "expected_chunk_ids": expected_ids,
        }
        
        for mode in modes:
            retrieved = rag.retrieve_with_metadata(query_text, top_k=top_k, mode=mode)
            retrieved_ids = [r["chunk_id"] for r in retrieved]
            
            metrics = calculate_metrics(retrieved_ids, expected_ids, top_k)
            results_by_mode[mode].append(metrics)
            
            case_info[mode] = {
                "retrieved_ids": retrieved_ids,
                "hit_at_1": metrics["hit_at_1"],
                "hit_at_3": metrics["hit_at_3"],
                "mrr": metrics["reciprocal_rank"]
            }
        
        query_details.append(case_info)
        
    # Aggregate metrics
    summary = {}
    for mode in modes:
        mode_results = results_by_mode[mode]
        n = len(mode_results)
        hit_1 = sum(1 for r in mode_results if r["hit_at_1"]) / n if n > 0 else 0.0
        hit_3 = sum(1 for r in mode_results if r["hit_at_3"]) / n if n > 0 else 0.0
        mrr = sum(r["reciprocal_rank"] for r in mode_results) / n if n > 0 else 0.0
        
        summary[mode] = {
            "hit_at_1": round(hit_1, 4),
            "hit_at_3": round(hit_3, 4),
            "mrr": round(mrr, 4),
        }
        
    # Print the aggregate summary table
    print(f"  Aggregate ({len(cases)} queries):")
    print(f"    {'Mode':<10} Hit@1    Hit@3    MRR")
    print(f"    {'─'*10} ─────    ─────    ───")
    for mode in modes:
        s = summary[mode]
        print(f"    {mode:<10} {s['hit_at_1']:<8.1%} {s['hit_at_3']:<8.1%} {s['mrr']:<8.3f}")
    print(f"  {'─'*60}\n")
    
    # Save to JSON
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    output_data = {
        "dataset": "code_review.jsonl",
        "top_k": top_k,
        "modes": summary,
        "queries": query_details
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2)
    print(f"  Results successfully saved to {output_path}\n")


def main():
    import argparse
    p = argparse.ArgumentParser(description="Karl RAG retrieval benchmark")
    p.add_argument("--top-k", type=int, default=3, help="Retrieval cutoff (default: 3)")
    p.add_argument("--headers", action="store_true", help="Enable contextual chunk headers")
    p.add_argument("--compare", action="store_true", help="Run twice: without vs with headers, compare")
    p.add_argument("--synthetic", action="store_true", help="Run original synthetic benchmark instead of code review")
    p.add_argument("--output", type=str, default="data/rag_benchmark_results.json", help="Path to save results JSON")
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
    elif args.synthetic:
        results = run_benchmark(top_k=args.top_k, contextual_headers=args.headers)
        print_results(results, args.top_k)
    else:
        run_code_review_benchmark(top_k=args.top_k, output_path=args.output)


if __name__ == "__main__":
    main()

