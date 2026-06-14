"""
RAG Retrieval Benchmark — Karl Workbench
==========================================
Compares retrieval quality metrics on a fixed query set.
Now includes generation-level BLEU and ROUGE metrics using the local LLM.

Usage:
  python eval/benchmark_rag.py
  python eval/benchmark_rag.py --top-k 5 --headers
"""

import os
import sys
import time
import textwrap
import json
import re
import math
import collections
from dataclasses import dataclass
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.rag_pipeline import RAGPipeline
from app.engine.model_loader import ModelLoader
from core.interaction_loop import build_prompt
from core.cognitive_parser import parse_thought_stream


# ── NLP Metric Helpers (Pure Python & NumPy) ──────────────────────────────────

def _tokenize(text):
    """
    Tokenize text by lowercasing and splitting by whitespace/punctuation.
    Strictly follows: lowercase + re.split by non-alphanumeric.
    """
    if not isinstance(text, str):
        text = str(text)
    # Lowercase and split by any sequence of non-alphanumeric characters
    tokens = [t for t in re.split(r'[^a-z0-9]+', text.lower()) if t]
    return tokens

def _get_ngrams(tokens, n):
    """Generates n-grams from a list of tokens."""
    return [tuple(tokens[i:i+n]) for i in range(len(tokens)-n+1)]

def compute_bleu(reference, hypothesis, n_max=2):
    """
    Bilingual Evaluation Understudy (BLEU) implementation.
    Strictly follows provided mathematical specifications.
    """
    ref_tokens = _tokenize(reference)
    hyp_tokens = _tokenize(hypothesis)
    
    c = len(hyp_tokens)
    r = len(ref_tokens)
    
    if c == 0:
        return 0.0
    
    precisions = []
    for n in range(1, n_max + 1):
        ref_ngrams = collections.Counter(_get_ngrams(ref_tokens, n))
        hyp_ngrams = collections.Counter(_get_ngrams(hyp_tokens, n))
        
        matches = 0
        hyp_ngram_count = len(_get_ngrams(hyp_tokens, n))
        if hyp_ngram_count > 0:
            for ngram, count in hyp_ngrams.items():
                if ngram in ref_ngrams:
                    # p_n = sum(Count_clip(g)) / sum(Count(g))
                    matches += min(count, ref_ngrams[ngram])
            precision = matches / hyp_ngram_count
        else:
            precision = 0.0
        precisions.append(precision)
    
    # Brevity Penalty (BP)
    # BP = 1 if c > r else e^(1 - r/c)
    if c > r:
        bp = 1.0
    else:
        bp = math.exp(1 - r / c)
        
    if n_max == 1:
        # BLEU-1 = p_1 * BP
        return precisions[0] * bp
    elif n_max == 2:
        # BLEU-2 = exp(0.5 ln(p_1) + 0.5 ln(p_2)) * BP
        p1, p2 = precisions
        if p1 <= 0 or p2 <= 0:
            return 0.0
        return math.exp(0.5 * math.log(p1) + 0.5 * math.log(p2)) * bp
    
    return 0.0

def compute_rouge_1(reference, hypothesis):
    """
    ROUGE-1: Precision, Recall, and F1 based on unigrams.
    """
    ref_tokens = _tokenize(reference)
    hyp_tokens = _tokenize(hypothesis)
    
    if not ref_tokens or not hyp_tokens:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0}
    
    ref_counts = collections.Counter(ref_tokens)
    hyp_counts = collections.Counter(hyp_tokens)
    
    matches = 0
    for token, count in hyp_counts.items():
        if token in ref_counts:
            # Overlap(1-grams)
            matches += min(count, ref_counts[token])
            
    precision = matches / len(hyp_tokens)
    recall = matches / len(ref_tokens)
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    
    return {"precision": precision, "recall": recall, "f1": f1}

def compute_rouge_l(reference, hypothesis, beta=1.0):
    """
    ROUGE-L: Longest Common Subsequence.
    Strictly follows provided mathematical specifications.
    """
    X = _tokenize(reference)
    Y = _tokenize(hypothesis)
    
    n, m = len(X), len(Y)
    if n == 0 or m == 0:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0}
    
    # Dynamic programming for LCS length
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if X[i-1] == Y[j-1]:
                dp[i][j] = dp[i-1][j-1] + 1
            else:
                dp[i][j] = max(dp[i-1][j], dp[i][j-1])
                
    lcs_len = dp[n][m]
    
    # R_L = LCS(X, Y) / n
    # P_L = LCS(X, Y) / m
    recall = lcs_len / n
    precision = lcs_len / m
    
    # F_L = (1 + beta^2) * R_L * P_L / (R_L + beta^2 * P_L)
    denom = (recall + (beta**2) * precision)
    if denom > 0:
        f1 = (1 + beta**2) * recall * precision / denom
    else:
        f1 = 0.0
    
    return {"precision": precision, "recall": recall, "f1": f1}


# ── Synthetic benchmark corpus ────────────────────────────────────────────────

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

    rag = RAGPipeline(contextual_headers=contextual_headers)
    rag.index.reset()
    rag.documents = []

    print(f"\n  Ingesting {len(CORPUS)} synthetic chunks...")
    for source, text in CORPUS:
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

    # Load local LLM
    print("\n  Loading local LLM for generation scoring...")
    llm = ModelLoader.get_instance()
    if not llm:
        print("  Error: No model loaded in ModelLoader. Please load a model first.")
        return
    print(f"  Model active: {ModelLoader.model_name()}\n")
    
    # Build a fresh in-memory RAG index
    rag = RAGPipeline(contextual_headers=False)
    rag.index.reset()
    rag.documents = []
    
    # Ingest contexts
    print(f"  Ingesting {len(cases)} code contexts...")
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
        reference_answer = str(case.get("expected", ""))
        
        case_info = {
            "case_id": case.get("id", f"code_{i:03d}"),
            "query": query_text,
            "expected_chunk_ids": expected_ids,
            "reference": reference_answer
        }
        
        print(f"  [{i+1}/{len(cases)}] Query: {textwrap.shorten(query_text, 50)}")
        
        for mode in modes:
            retrieved = rag.retrieve_with_metadata(query_text, top_k=top_k, mode=mode)
            retrieved_ids = [r["chunk_id"] for r in retrieved]
            
            # Retrieval metrics
            retr_metrics = calculate_metrics(retrieved_ids, expected_ids, top_k)
            
            # Generation
            context_text = "\n\n".join([r["text"] for r in retrieved])
            sys_prompt = (
                "You are Karl, a precise and thoughtful code review assistant. "
                "Use the following retrieved context chunks to answer the user's request. "
                "If the context is insufficient, explain what is missing. "
                "Always respond in English."
            )
            prompt = build_prompt(
                sys_prompt + "\n\nRetrieved Context:\n" + context_text,
                [{"role": "user", "content": query_text}]
            )
            
            # Inference (Temperature 0.0 for deterministic benchmark results)
            res = llm(prompt, max_tokens=256, temperature=0.0, stop=["<|im_end|>", "User:"])
            raw_text = res["choices"][0]["text"]
            _, final_response = parse_thought_stream(raw_text)
            if not final_response: final_response = raw_text
            
            # Compute NLP Scores (strictly following math specs)
            b1 = compute_bleu(reference_answer, final_response, n_max=1)
            b2 = compute_bleu(reference_answer, final_response, n_max=2)
            r1 = compute_rouge_1(reference_answer, final_response)
            rl = compute_rouge_l(reference_answer, final_response)
            
            mode_metrics = {
                "hit_at_1": retr_metrics["hit_at_1"],
                "hit_at_3": retr_metrics["hit_at_3"],
                "mrr": retr_metrics["reciprocal_rank"],
                "bleu_1": round(b1, 4),
                "bleu_2": round(b2, 4),
                "rouge_1": round(r1["f1"], 4),
                "rouge_l": round(rl["f1"], 4)
            }
            results_by_mode[mode].append(mode_metrics)
            
            case_info[mode] = {
                "retrieved_ids": retrieved_ids,
                "response": final_response,
                **mode_metrics
            }
        
        query_details.append(case_info)
        
    # Aggregate metrics using NumPy
    summary = {}
    for mode in modes:
        mode_results = results_by_mode[mode]
        n = len(mode_results)
        if n == 0: continue
        
        summary[mode] = {
            "hit_at_1": round(float(np.mean([r["hit_at_1"] for r in mode_results])), 4),
            "hit_at_3": round(float(np.mean([r["hit_at_3"] for r in mode_results])), 4),
            "mrr": round(float(np.mean([r["mrr"] for r in mode_results])), 4),
            "bleu_1": round(float(np.mean([r["bleu_1"] for r in mode_results])), 4),
            "bleu_2": round(float(np.mean([r["bleu_2"] for r in mode_results])), 4),
            "rouge_1": round(float(np.mean([r["rouge_1"] for r in mode_results])), 4),
            "rouge_l": round(float(np.mean([r["rouge_l"] for r in mode_results])), 4),
        }
        
    # Print the aggregate summary table
    print(f"\n  Aggregate ({len(cases)} queries):")
    print(f"    {'Mode':<10} Hit@1    Hit@3    MRR     B-1     B-2     R-1     R-L")
    print(f"    {'─'*10} ─────    ─────    ───     ───     ───     ───     ───")
    for mode in modes:
        s = summary[mode]
        print(f"    {mode:<10} {s['hit_at_1']:<8.1%} {s['hit_at_3']:<8.1%} {s['mrr']:<7.3f} "
              f"{s['bleu_1']:<7.3f} {s['bleu_2']:<7.3f} {s['rouge_1']:<7.3f} {s['rouge_l']:<7.3f}")
    print(f"  {'─'*70}\n")
    
    # Save to JSON
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    output_data = summary # Request specified matching this schema
    
    # Also save full details for audit, but wrap the summary as the root keys
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    
    # Save extended details separately
    ext_path = output_path.replace(".json", "_detailed.json")
    with open(ext_path, "w", encoding="utf-8") as f:
        json.dump({
            "dataset": "code_review.jsonl",
            "top_k": top_k,
            "modes": summary,
            "queries": query_details
        }, f, indent=2)
        
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
