#!/usr/bin/env python3
"""Evaluate embedding model performance for prompt injection detection.

This script compares embedding models and tunes the similarity threshold by
measuring precision, recall, and F1 score against held-out test data.

Usage:
    python scripts/evaluate_embeddings.py                    # Evaluate current model
    python scripts/evaluate_embeddings.py --compare          # Compare small vs large
    python scripts/evaluate_embeddings.py --thresholds 0.7 0.75 0.8 0.85 0.9
"""

import argparse
import asyncio
import sys
from dataclasses import dataclass
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from datasets import load_dataset

from app.core.clients import get_openai_client, get_supabase_client
from app.core.config import get_settings
from app.detection.seed_data import load_deepset_attacks
from app.detection.seeder import clear_embeddings, embed_attacks, insert_embeddings


@dataclass
class EvaluationResult:
    """Results for a single threshold evaluation."""

    threshold: float
    true_positives: int
    false_positives: int
    true_negatives: int
    false_negatives: int

    @property
    def precision(self) -> float:
        """Precision: TP / (TP + FP)"""
        denom = self.true_positives + self.false_positives
        return self.true_positives / denom if denom > 0 else 0.0

    @property
    def recall(self) -> float:
        """Recall: TP / (TP + FN)"""
        denom = self.true_positives + self.false_negatives
        return self.true_positives / denom if denom > 0 else 0.0

    @property
    def f1(self) -> float:
        """F1 score: 2 * (P * R) / (P + R)"""
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) > 0 else 0.0

    @property
    def false_positive_rate(self) -> float:
        """FPR: FP / (FP + TN)"""
        denom = self.false_positives + self.true_negatives
        return self.false_positives / denom if denom > 0 else 0.0


@dataclass
class ModelEvaluation:
    """Full evaluation results for a model."""

    model: str
    results: list[EvaluationResult]

    def best_by_f1(self) -> EvaluationResult:
        """Get result with highest F1 score."""
        return max(self.results, key=lambda r: r.f1)


async def get_max_similarity(
    supabase_client,
    embedding: list[float],
) -> float:
    """Get maximum similarity score for an embedding against the database."""
    result = await supabase_client.rpc(
        "match_attack_embeddings",
        {
            "query_embedding": embedding,
            "match_threshold": 0.0,  # Get all matches
            "match_count": 1,
        },
    ).execute()

    if result.data:
        return result.data[0]["similarity"]
    return 0.0


async def evaluate_model(
    openai_client,
    supabase_client,
    model: str,
    thresholds: list[float],
    test_attacks: list,
    benign_samples: list[str],
    progress_callback=None,
) -> ModelEvaluation:
    """
    Evaluate a model at multiple thresholds.

    Args:
        openai_client: OpenAI client for embeddings.
        supabase_client: Supabase client for similarity search.
        model: Model name to evaluate.
        thresholds: List of thresholds to test.
        test_attacks: Held-out attack samples (should be detected).
        benign_samples: Benign text samples (should NOT be detected).
        progress_callback: Optional callback(stage, completed, total).

    Returns:
        ModelEvaluation with results for each threshold.
    """
    # Embed test attacks
    if progress_callback:
        progress_callback("embedding_attacks", 0, len(test_attacks))

    attack_embeddings = await embed_attacks(
        openai_client,
        test_attacks,
        model=model,
        progress_callback=lambda c, t: progress_callback("embedding_attacks", c, t) if progress_callback else None,
    )

    # Embed benign samples
    if progress_callback:
        progress_callback("embedding_benign", 0, len(benign_samples))

    # Create temporary AttackSample objects for benign texts
    from app.detection.seed_data import AttackSample
    benign_as_samples = [
        AttackSample(text=t, category="benign", subcategory=None, severity=0, source="test")
        for t in benign_samples
    ]
    benign_embeddings = await embed_attacks(
        openai_client,
        benign_as_samples,
        model=model,
        progress_callback=lambda c, t: progress_callback("embedding_benign", c, t) if progress_callback else None,
    )

    # Get similarity scores for all samples
    if progress_callback:
        progress_callback("scoring", 0, len(attack_embeddings) + len(benign_embeddings))

    attack_similarities = []
    for i, ea in enumerate(attack_embeddings):
        sim = await get_max_similarity(supabase_client, ea.embedding)
        attack_similarities.append(sim)
        if progress_callback:
            progress_callback("scoring", i + 1, len(attack_embeddings) + len(benign_embeddings))

    benign_similarities = []
    for i, ea in enumerate(benign_embeddings):
        sim = await get_max_similarity(supabase_client, ea.embedding)
        benign_similarities.append(sim)
        if progress_callback:
            progress_callback("scoring", len(attack_embeddings) + i + 1, len(attack_embeddings) + len(benign_embeddings))

    # Evaluate at each threshold
    results = []
    for threshold in thresholds:
        tp = sum(1 for s in attack_similarities if s >= threshold)
        fn = sum(1 for s in attack_similarities if s < threshold)
        fp = sum(1 for s in benign_similarities if s >= threshold)
        tn = sum(1 for s in benign_similarities if s < threshold)

        results.append(EvaluationResult(
            threshold=threshold,
            true_positives=tp,
            false_positives=fp,
            true_negatives=tn,
            false_negatives=fn,
        ))

    return ModelEvaluation(model=model, results=results)


def print_evaluation(eval_result: ModelEvaluation) -> None:
    """Print evaluation results in a formatted table."""
    print(f"\n=== {eval_result.model} ===")
    print(f"{'Threshold':<10} | {'Recall':<8} | {'Precision':<10} | {'F1':<8} | {'FP Rate':<8}")
    print("-" * 55)

    for r in eval_result.results:
        print(f"{r.threshold:<10.2f} | {r.recall:<8.2f} | {r.precision:<10.2f} | {r.f1:<8.2f} | {r.false_positive_rate * 100:<7.1f}%")

    best = eval_result.best_by_f1()
    print(f"\nBest threshold: {best.threshold} (F1={best.f1:.2f})")


async def run_evaluation(
    models: list[str],
    thresholds: list[float],
    seed_model: str | None = None,
) -> list[ModelEvaluation]:
    """
    Run full evaluation pipeline.

    Args:
        models: List of models to evaluate.
        thresholds: Thresholds to test.
        seed_model: Model to use for seeding (defaults to first model).

    Returns:
        List of ModelEvaluation results.
    """
    settings = get_settings()
    openai_client = await get_openai_client()
    supabase_client = await get_supabase_client()

    # Load datasets
    print("Loading datasets...")
    train_attacks = list(load_deepset_attacks(split="train"))
    test_attacks = list(load_deepset_attacks(split="test"))

    # Load benign samples (label=0) from test split
    raw_dataset = load_dataset("deepset/prompt-injections", split="test")
    benign_samples = [row["text"] for row in raw_dataset if row["label"] == 0]

    print(f"  Train attacks: {len(train_attacks)}")
    print(f"  Test attacks: {len(test_attacks)}")
    print(f"  Benign samples: {len(benign_samples)}")

    results = []

    for model in models:
        print(f"\n{'=' * 60}")
        print(f"Evaluating: {model}")
        print('=' * 60)

        # Clear and re-seed with current model
        print("\nSeeding database...")
        await clear_embeddings(supabase_client)

        embedded = await embed_attacks(
            openai_client,
            train_attacks,
            model=model,
            progress_callback=lambda c, t: print(f"\r  Embedding: {c}/{t}", end=""),
        )
        print()

        await insert_embeddings(
            supabase_client,
            embedded,
            progress_callback=lambda c, t: print(f"\r  Inserting: {c}/{t}", end=""),
        )
        print()

        # Evaluate
        print("\nEvaluating...")
        eval_result = await evaluate_model(
            openai_client=openai_client,
            supabase_client=supabase_client,
            model=model,
            thresholds=thresholds,
            test_attacks=test_attacks,
            benign_samples=benign_samples,
            progress_callback=lambda s, c, t: print(f"\r  {s}: {c}/{t}", end=""),
        )
        print()

        print_evaluation(eval_result)
        results.append(eval_result)

    return results


async def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Evaluate embedding models for prompt injection detection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Compare text-embedding-3-small vs text-embedding-3-large",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Specific model to evaluate (default: from config)",
    )
    parser.add_argument(
        "--thresholds",
        type=float,
        nargs="+",
        default=[0.75, 0.80, 0.85, 0.90],
        help="Thresholds to evaluate (default: 0.75 0.80 0.85 0.90)",
    )

    args = parser.parse_args()
    settings = get_settings()

    if args.compare:
        models = ["text-embedding-3-small", "text-embedding-3-large"]
    elif args.model:
        models = [args.model]
    else:
        models = [settings.embedding_model]

    results = await run_evaluation(models, args.thresholds)

    # Print recommendation
    print("\n" + "=" * 60)
    print("RECOMMENDATION")
    print("=" * 60)

    best_overall = max(
        [(eval_result.model, eval_result.best_by_f1()) for eval_result in results],
        key=lambda x: x[1].f1,
    )
    model_name, best_result = best_overall
    print(f"\nUse {model_name} at threshold {best_result.threshold}")
    print(f"  Recall: {best_result.recall:.2f}")
    print(f"  Precision: {best_result.precision:.2f}")
    print(f"  F1: {best_result.f1:.2f}")
    print(f"  FP Rate: {best_result.false_positive_rate * 100:.1f}%")

    print(f"\nUpdate app/core/config.py:")
    print(f'  embedding_model: str = "{model_name}"')
    print(f"  embedding_threshold: float = {best_result.threshold}")


if __name__ == "__main__":
    asyncio.run(main())
