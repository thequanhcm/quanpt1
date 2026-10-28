"""V18 — Federated Learning & Privacy-Preserving Memory.

Học phân tán (federated learning) giữa nhiều instance + privacy-preserving techniques
(differential privacy, secure aggregation, local processing).
"""
from __future__ import annotations

import hashlib
import json
import random
import sqlite3
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class FederatedNode:
    """Node in federated network."""
    node_id: str
    role: str  # 'aggregator', 'client', 'both'
    capabilities: list[str]
    last_sync: str | None = None
    status: str = 'active'


@dataclass
class ModelUpdate:
    """Model update from client."""
    update_id: str
    node_id: str
    model_version: int
    weights: dict[str, Any]
    gradients: dict[str, Any] | None
    loss: float | None
    accuracy: float | None
    samples: int
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class TrainingSession:
    """Federated training session."""
    session_id: str
    rounds: int
    clients_per_round: int
    current_round: int
    global_model_version: int
    loss_history: list[float]
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: str | None = None


class FederatedAggregator:
    """Federated learning aggregator."""
    
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self._conn = sqlite3.connect(str(self.db_path))
        self._create_schema()
        self._global_model: dict[str, Any] = {}
        self._model_version = 0
    
    def _create_schema(self):
        """Create federated learning schema."""
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS federated_nodes (
                node_id TEXT PRIMARY KEY,
                role TEXT NOT NULL,
                capabilities TEXT NOT NULL,
                last_sync TEXT,
                status TEXT NOT NULL
            );
            
            CREATE TABLE IF NOT EXISTS training_sessions (
                session_id TEXT PRIMARY KEY,
                rounds INTEGER NOT NULL,
                clients_per_round INTEGER NOT NULL,
                current_round INTEGER NOT NULL,
                global_model_version INTEGER NOT NULL,
                loss_history TEXT,
                started_at TEXT NOT NULL,
                completed_at TEXT
            );
            
            CREATE TABLE IF NOT EXISTS model_updates (
                update_id TEXT PRIMARY KEY,
                node_id TEXT NOT NULL,
                model_version INTEGER NOT NULL,
                weights TEXT NOT NULL,
                gradients TEXT,
                loss REAL,
                accuracy REAL,
                samples INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (node_id) REFERENCES federated_nodes(node_id)
            );
            
            CREATE INDEX IF NOT EXISTS idx_updates_node ON model_updates(node_id);
            CREATE INDEX IF NOT EXISTS idx_updates_version ON model_updates(model_version);
        """)
        self._conn.commit()
    
    def register_node(self, node: FederatedNode) -> bool:
        """Register a federated node."""
        try:
            self._conn.execute(
                """INSERT INTO federated_nodes (node_id, role, capabilities, last_sync, status)
                   VALUES (?, ?, ?, ?, ?)""",
                (node.node_id, node.role, json.dumps(node.capabilities), 
                 node.last_sync, node.status)
            )
            self._conn.commit()
            return True
        except Exception:
            return False
    
    def get_active_clients(self, limit: int | None = None) -> list[FederatedNode]:
        """Get active client nodes."""
        rows = self._conn.execute(
            """SELECT node_id, role, capabilities, last_sync, status 
               FROM federated_nodes 
               WHERE status = 'active' AND role IN ('client', 'both')"""
        ).fetchall()
        
        clients = []
        for row in rows:
            clients.append(FederatedNode(
                node_id=row[0],
                role=row[1],
                capabilities=json.loads(row[2]),
                last_sync=row[3],
                status=row[4]
            ))
        
        if limit:
            return random.sample(clients, min(limit, len(clients)))
        return clients
    
    def start_training(self, rounds: int, clients_per_round: int) -> TrainingSession:
        """Start federated training session."""
        session_id = f"fl_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        
        session = TrainingSession(
            session_id=session_id,
            rounds=rounds,
            clients_per_round=clients_per_round,
            current_round=0,
            global_model_version=self._model_version,
            loss_history=[]
        )
        
        self._conn.execute(
            """INSERT INTO training_sessions 
               (session_id, rounds, clients_per_round, current_round, global_model_version, loss_history, started_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (session.session_id, session.rounds, session.clients_per_round,
             session.current_round, session.global_model_version, 
             json.dumps(session.loss_history), session.started_at)
        )
        self._conn.commit()
        
        return session
    
    def local_train(self, node_id: str, model: dict[str, Any], 
                   epochs: int = 5, batch_size: int = 32) -> ModelUpdate:
        """Simulate local training on a client node."""
        # In real implementation, this would train on local data
        # Here we simulate with random updates
        
        update_id = f"update_{node_id}_{datetime.now(timezone.utc).timestamp()}"
        
        # Simulate weight updates
        updated_weights = {}
        for key, value in model.items():
            if isinstance(value, (int, float)):
                updated_weights[key] = value + random.gauss(0, 0.01)
            else:
                updated_weights[key] = value
        
        update = ModelUpdate(
            update_id=update_id,
            node_id=node_id,
            model_version=self._model_version,
            weights=updated_weights,
            gradients=None,  # Would be computed in real training
            loss=random.uniform(0.1, 0.5),
            accuracy=random.uniform(0.7, 0.95),
            samples=random.randint(100, 1000)
        )
        
        self._conn.execute(
            """INSERT INTO model_updates 
               (update_id, node_id, model_version, weights, gradients, loss, accuracy, samples, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (update.update_id, update.node_id, update.model_version,
             json.dumps(update.weights), None, update.loss, update.accuracy,
             update.samples, update.timestamp)
        )
        self._conn.commit()
        
        return update
    
    def aggregate_updates(self, updates: list[ModelUpdate], 
                         strategy: str = 'fedavg') -> dict[str, Any]:
        """Aggregate model updates from clients."""
        if not updates:
            return self._global_model
        
        if strategy == 'fedavg':
            return self._fedavg_aggregate(updates)
        elif strategy == 'fedprox':
            return self._fedprox_aggregate(updates)
        else:
            return self._fedavg_aggregate(updates)
    
    def _fedavg_aggregate(self, updates: list[ModelUpdate]) -> dict[str, Any]:
        """FedAvg aggregation (weighted average by samples)."""
        total_samples = sum(u.samples for u in updates)
        if total_samples == 0:
            return self._global_model
        
        # Initialize aggregated weights
        aggregated = {}
        for key in updates[0].weights.keys():
            aggregated[key] = 0.0
        
        # Weighted average
        for update in updates:
            weight = update.samples / total_samples
            for key in aggregated.keys():
                val = update.weights.get(key, 0)
                if isinstance(val, (int, float)):
                    aggregated[key] += val * weight
        
        self._global_model = aggregated
        self._model_version += 1
        
        return aggregated
    
    def _fedprox_aggregate(self, updates: list[ModelUpdate]) -> dict[str, Any]:
        """FedProx aggregation (with proximal term)."""
        # Simplified FedProx - same as FedAvg for now
        # In real implementation, would add proximal term
        return self._fedavg_aggregate(updates)
    
    def distribute_global_model(self, node_ids: list[str]) -> bool:
        """Distribute global model to nodes."""
        for node_id in node_ids:
            self._conn.execute(
                "UPDATE federated_nodes SET last_sync = ? WHERE node_id = ?",
                (datetime.now(timezone.utc).isoformat(), node_id)
            )
        self._conn.commit()
        return True
    
    def evaluate_global_model(self, node_ids: list[str]) -> dict:
        """Evaluate global model on all nodes."""
        evaluations = []
        
        for node_id in node_ids:
            # Simulate evaluation
            evaluations.append({
                'node_id': node_id,
                'loss': random.uniform(0.1, 0.5),
                'accuracy': random.uniform(0.7, 0.95)
            })
        
        avg_loss = sum(e['loss'] for e in evaluations) / len(evaluations)
        avg_accuracy = sum(e['accuracy'] for e in evaluations) / len(evaluations)
        
        return {
            'evaluations': evaluations,
            'avg_loss': avg_loss,
            'avg_accuracy': avg_accuracy
        }
    
    def check_convergence(self, loss_history: list[float], threshold: float = 0.01) -> bool:
        """Check if training has converged."""
        if len(loss_history) < 2:
            return False
        
        recent_losses = loss_history[-5:] if len(loss_history) >= 5 else loss_history
        loss_change = max(recent_losses) - min(recent_losses)
        
        return loss_change < threshold
    
    def handle_stragglers(self, node_ids: list[str], timeout: int = 300) -> list[str]:
        """Handle slow/straggler nodes."""
        stragglers = []
        current_time = datetime.now(timezone.utc)
        
        for node_id in node_ids:
            row = self._conn.execute(
                "SELECT last_sync FROM federated_nodes WHERE node_id = ?",
                (node_id,)
            ).fetchone()
            
            if row and row[0]:
                last_sync = datetime.fromisoformat(row[0])
                if (current_time - last_sync).total_seconds() > timeout:
                    stragglers.append(node_id)
        
        return stragglers
    
    def detect_poisoning(self, updates: list[ModelUpdate], 
                        method: str = 'krum') -> list[str]:
        """Detect malicious/poisoned updates."""
        # Simplified poisoning detection
        # In real implementation, would use Krum, Median, Trimmed Mean, etc.
        
        poisoned = []
        if len(updates) < 3:
            return poisoned
        
        # Check for outliers in loss/accuracy
        losses = [u.loss for u in updates if u.loss is not None]
        if losses:
            avg_loss = sum(losses) / len(losses)
            std_loss = (sum((l - avg_loss) ** 2 for l in losses) / len(losses)) ** 0.5
            
            for update in updates:
                if update.loss and abs(update.loss - avg_loss) > 3 * std_loss:
                    poisoned.append(update.node_id)
        
        return poisoned
    
    def get_global_model(self) -> dict[str, Any]:
        """Get current global model."""
        return self._global_model.copy()
    
    def close(self):
        """Close database connection."""
        self._conn.close()


class DifferentialPrivacy:
    """Differential privacy mechanisms."""
    
    def __init__(self, epsilon: float = 1.0, delta: float = 1e-5):
        self.epsilon = epsilon
        self.delta = delta
        self.privacy_budget_used = 0.0
        self.operations = []
    
    def add_laplace_noise(self, value: float, sensitivity: float) -> float:
        """Add Laplace noise for differential privacy."""
        scale = sensitivity / self.epsilon
        noise = random.laplace(0, scale)
        return value + noise
    
    def add_gaussian_noise(self, value: float, sensitivity: float) -> float:
        """Add Gaussian noise for (epsilon, delta)-DP."""
        sigma = sensitivity * (2 * math.log(1.25 / self.delta)) ** 0.5 / self.epsilon
        noise = random.gauss(0, sigma)
        return value + value
    
    def clip_gradients(self, gradients: dict[str, float], max_norm: float) -> dict[str, float]:
        """Clip gradients to bound sensitivity."""
        # Calculate gradient norm
        norm = sum(g ** 2 for g in gradients.values()) ** 0.5
        
        if norm > max_norm:
            scale = max_norm / norm
            return {k: v * scale for k, v in gradients.items()}
        
        return gradients
    
    def track_privacy_budget(self, epsilon_cost: float):
        """Track privacy budget consumption."""
        self.privacy_budget_used += epsilon_cost
        self.operations.append({
            'epsilon_cost': epsilon_cost,
            'total_used': self.privacy_budget_used,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
    
    def remaining_budget(self) -> float:
        """Get remaining privacy budget."""
        return max(0, self.epsilon - self.privacy_budget_used)
    
    def privacy_report(self) -> dict:
        """Generate privacy budget report."""
        return {
            'total_epsilon': self.epsilon,
            'used': self.privacy_budget_used,
            'remaining': self.remaining_budget(),
            'delta': self.delta,
            'operations': self.operations
        }


import math

# Fix: Move math import to top