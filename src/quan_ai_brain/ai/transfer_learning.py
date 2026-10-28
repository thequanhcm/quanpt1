"""V29.4 — Transfer Learning (toy, stdlib-only).

HONESTY NOTE
------------
The "models" here are tiny linear regressors trained with hand-written
gradient descent over `list[float]`. There is no PyTorch, no real
pretrained network. The module demonstrates the *mechanics* of transfer
learning: source training, layer freezing, few-shot fine-tuning,
forgetting measurement, and soft-target distillation — on toy data only.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any, Optional, Sequence

__version__ = "V29.4"


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


# ---------------------------------------------------------------------------
# Toy linear model on list[float] with hand-written gradient descent
# ---------------------------------------------------------------------------

@dataclass
class TrainingReport:
    task: str
    epochs: int
    initial_loss: float
    final_loss: float
    loss_curve: list[float] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task": self.task,
            "epochs": self.epochs,
            "initial_loss": self.initial_loss,
            "final_loss": self.final_loss,
        }


class LinearModel:
    """y = w . x + b (with an optional frozen mask over the weights)."""

    def __init__(self, dim: int, weights: Optional[Sequence[float]] = None,
                 bias: float = 0.0) -> None:
        self.dim = dim
        if weights is None:
            weights = [0.01 * ((i % 7) - 3) for i in range(dim)]
        if len(weights) != dim:
            raise ValueError("weights length mismatch")
        self.weights: list[float] = [float(w) for w in weights]
        self.bias = float(bias)
        self.frozen: list[bool] = [False] * dim

    def predict(self, x: Sequence[float]) -> float:
        if len(x) != self.dim:
            raise ValueError(f"expected {self.dim} features, got {len(x)}")
        return sum(w * v for w, v in zip(self.weights, x)) + self.bias

    def predict_one(self, x: Sequence[float]) -> float:
        return self.predict(x)

    def mse(self, X: Sequence[Sequence[float]],
            y: Sequence[float]) -> float:
        if len(X) != len(y) or not X:
            raise ValueError("empty or mismatched data")
        preds = [self.predict(x) for x in X]
        return sum((p - t) ** 2 for p, t in zip(preds, y)) / len(y)

    def copy(self) -> "LinearModel":
        clone = LinearModel(self.dim, weights=list(self.weights),
                            bias=self.bias)
        clone.frozen = list(self.frozen)
        return clone

    def freeze_layer(self, indices: Optional[Sequence[int]] = None) -> None:
        """Freeze weights (all if indices is None); bias stays trainable."""
        if indices is None:
            self.frozen = [True] * self.dim
        else:
            for i in indices:
                if not 0 <= i < self.dim:
                    raise IndexError(f"weight index {i} out of range")
                self.frozen[i] = True

    def unfreeze_all(self) -> None:
        self.frozen = [False] * self.dim

    def to_dict(self) -> dict[str, Any]:
        return {"dim": self.dim, "weights": list(self.weights),
                "bias": self.bias,
                "frozen": [i for i, f in enumerate(self.frozen) if f]}


class GradientDescentTrainer:
    """Full-batch gradient descent for the toy linear model.

    The frozen mask is respected: frozen weights never receive updates.
    """

    def __init__(self, lr: float = 0.05, epochs: int = 200) -> None:
        self.lr = lr
        self.epochs = epochs

    def train(self, model: LinearModel, X: Sequence[Sequence[float]],
              y: Sequence[float], task: str = "train") -> TrainingReport:
        n = len(X)
        if n == 0 or len(y) != n:
            raise ValueError("empty or mismatched training data")
        initial_loss = model.mse(X, y)
        loss_curve: list[float] = []
        for _ in range(self.epochs):
            grad_w = [0.0] * model.dim
            grad_b = 0.0
            for x, target in zip(X, y):
                err = model.predict(x) - target
                for j in range(model.dim):
                    grad_w[j] += err * x[j]
                grad_b += err
            for j in range(model.dim):
                if not model.frozen[j]:
                    model.weights[j] -= self.lr * 2.0 * grad_w[j] / n
            model.bias -= self.lr * 2.0 * grad_b / n
            loss_curve.append(model.mse(X, y))
        return TrainingReport(
            task=task, epochs=self.epochs, initial_loss=initial_loss,
            final_loss=model.mse(X, y), loss_curve=loss_curve,
        )


# ---------------------------------------------------------------------------
# Transfer engine
# ---------------------------------------------------------------------------

@dataclass
class FewShotResult:
    k_samples: int
    target_mse_before: float
    target_mse_after: float
    source_mse_before: float
    source_mse_after: float
    forgetting: float  # normalized drop on source after fine-tune

    def to_dict(self) -> dict[str, Any]:
        return {
            "k_samples": self.k_samples,
            "target_mse_before": self.target_mse_before,
            "target_mse_after": self.target_mse_after,
            "source_mse_before": self.source_mse_before,
            "source_mse_after": self.source_mse_after,
            "forgetting": self.forgetting,
        }


@dataclass
class DistillationResult:
    student_initial_mse_vs_teacher: float
    student_final_mse_vs_teacher: float
    teacher_agreement: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "student_initial_mse_vs_teacher": self.student_initial_mse_vs_teacher,
            "student_final_mse_vs_teacher": self.student_final_mse_vs_teacher,
            "teacher_agreement": self.teacher_agreement,
        }


class TransferLearningEngine:
    """Toy transfer-learning pipeline on linear models:

    train_source -> freeze_layer -> few_shot_fine_tune -> forgetting_metric
    plus teacher -> student distillation.
    """

    def __init__(self, lr: float = 0.05, epochs: int = 200,
                 fine_tune_epochs: int = 100, seed: int = 7) -> None:
        self.trainer = GradientDescentTrainer(lr=lr, epochs=epochs)
        self.fine_tune_trainer = GradientDescentTrainer(
            lr=lr, epochs=fine_tune_epochs)
        self.rng = random.Random(seed)

    def train_source(self, X_source: Sequence[Sequence[float]],
                     y_source: Sequence[float],
                     dim: int = 4) -> LinearModel:
        model = LinearModel(dim)
        self.trainer.train(model, X_source, y_source, task="source")
        return model

    def freeze_layer(self, model: LinearModel,
                     indices: Optional[Sequence[int]] = None) -> None:
        model.freeze_layer(indices)

    def few_shot_fine_tune(self, model: LinearModel,
                           X_target: Sequence[Sequence[float]],
                           y_target: Sequence[float],
                           k: int = 10,
                           X_source_eval: Optional[Sequence[Sequence[float]]] = None,
                           y_source_eval: Optional[Sequence[float]] = None) -> FewShotResult:
        """Fine-tune on the first k target samples; report target improvement
        and source forgetting (source metrics optional)."""
        if k <= 0:
            raise ValueError("k must be > 0")
        X_t = [list(x) for x in X_target[:k]]
        y_t = list(y_target[:k])
        if not X_t:
            raise ValueError("no target data")

        target_mse_before = model.mse(X_t, y_t)
        has_source = X_source_eval is not None and y_source_eval is not None
        source_mse_before = model.mse(X_source_eval, y_source_eval) if has_source else 0.0

        self.fine_tune_trainer.train(model, X_t, y_t, task="target_fine_tune")

        target_mse_after = model.mse(X_t, y_t)
        source_mse_after = model.mse(X_source_eval, y_source_eval) if has_source else 0.0

        forgetting = 0.0
        if has_source:
            if source_mse_before > 0:
                forgetting = _clamp01(
                    (source_mse_after - source_mse_before) / source_mse_before)
            elif source_mse_after > 0:
                forgetting = 1.0

        return FewShotResult(
            k_samples=len(X_t),
            target_mse_before=target_mse_before,
            target_mse_after=target_mse_after,
            source_mse_before=source_mse_before,
            source_mse_after=source_mse_after,
            forgetting=forgetting,
        )

    def forgetting_metric(self, model: LinearModel,
                          X_source_eval: Sequence[Sequence[float]],
                          y_source_eval: Sequence[float],
                          reference_model: Optional[LinearModel] = None) -> float:
        """Current source MSE, or the normalized increase vs a reference
        (pre-fine-tune) model when one is supplied."""
        after = model.mse(X_source_eval, y_source_eval)
        if reference_model is None:
            return after
        before = reference_model.mse(X_source_eval, y_source_eval)
        if before <= 0:
            return 0.0 if after <= 0 else 1.0
        return _clamp01((after - before) / before)

    def distill(self, teacher: LinearModel,
                X_transfer: Sequence[Sequence[float]],
                epochs: int = 150, lr: float = 0.05) -> DistillationResult:
        """Teacher soft targets (teacher outputs) -> student training."""
        student = LinearModel(teacher.dim)
        soft_targets = [teacher.predict(x) for x in X_transfer]
        trainer = GradientDescentTrainer(lr=lr, epochs=epochs)
        initial = student.mse(X_transfer, soft_targets)
        trainer.train(student, X_transfer, soft_targets, task="distill")
        final = student.mse(X_transfer, soft_targets)
        scale = max((abs(t) for t in soft_targets), default=1.0) or 1.0
        tolerance = 0.1 * scale
        agreement = (sum(1 for x, t in zip(X_transfer, soft_targets)
                         if abs(student.predict(x) - t) <= tolerance)
                     / len(X_transfer))
        return DistillationResult(
            student_initial_mse_vs_teacher=initial,
            student_final_mse_vs_teacher=final,
            teacher_agreement=agreement,
        )
