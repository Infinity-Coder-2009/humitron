#!/usr/bin/env python3
"""Benchmark script for Humitron."""

import argparse
import time
import statistics
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from humitron.agent import ReActAgent
from humitron.config.loader import Config


def run_benchmark(
    model: str = "llama3.2",
    num_queries: int = 10,
    max_steps: int = 5
) -> dict:
    """Run benchmark on agent.

    Args:
        model: Model to benchmark.
        num_queries: Number of test queries.
        max_steps: Max steps per query.

    Returns:
        Dictionary with benchmark results.
    """
    agent = ReActAgent(model=model, max_steps=max_steps)

    test_queries = [
        "What is 2+2?",
        "Read the README.md file",
        "List files in current directory",
        "Search for Python tutorials",
        "Create a simple Python script",
        "Explain what a ReAct agent is",
        "What is the capital of France?",
        "Write a haiku about coding",
        "Check if Ollama is running",
        "Show current configuration",
    ]

    latencies = []
    successes = 0
    errors = 0

    for i, query in enumerate(test_queries[:num_queries]):
        print(f"Query {i+1}/{num_queries}: {query[:50]}...")

        start = time.time()
        try:
            result = agent.run(query)
            elapsed = time.time() - start
            latencies.append(elapsed)
            successes += 1
            print(f"  ✓ Completed in {elapsed:.2f}s")
        except Exception as e:
            elapsed = time.time() - start
            errors += 1
            print(f"  ✗ Failed after {elapsed:.2f}s: {e}")

    if latencies:
        return {
            "model": model,
            "num_queries": num_queries,
            "successes": successes,
            "errors": errors,
            "avg_latency": statistics.mean(latencies),
            "median_latency": statistics.median(latencies),
            "min_latency": min(latencies),
            "max_latency": max(latencies),
            "stdev_latency": statistics.stdev(latencies) if len(latencies) > 1 else 0,
        }
    else:
        return {
            "model": model,
            "num_queries": num_queries,
            "successes": 0,
            "errors": errors,
            "avg_latency": 0,
        }


def main():
    parser = argparse.ArgumentParser(description="Benchmark Humitron agent")
    parser.add_argument("--model", default="llama3.2", help="Model to benchmark")
    parser.add_argument("--queries", type=int, default=10, help="Number of queries")
    parser.add_argument("--steps", type=int, default=5, help="Max steps per query")
    parser.add_argument("--output", help="Output JSON file")

    args = parser.parse_args()

    print(f"Starting benchmark: model={args.model}, queries={args.queries}")
    print("-" * 50)

    results = run_benchmark(args.model, args.queries, args.steps)

    print("-" * 50)
    print("BENCHMARK RESULTS")
    print("-" * 50)
    print(f"Model: {results['model']}")
    print(f"Queries: {results['num_queries']}")
    print(f"Successes: {results['successes']}")
    print(f"Errors: {results['errors']}")
    print(f"Avg Latency: {results['avg_latency']:.2f}s")
    print(f"Median Latency: {results['median_latency']:.2f}s")
    print(f"Min Latency: {results['min_latency']:.2f}s")
    print(f"Max Latency: {results['max_latency']:.2f}s")
    print(f"Std Dev: {results['stdev_latency']:.2f}s")

    if args.output:
        import json
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to {args.output}")


if __name__ == "__main__":
    main()