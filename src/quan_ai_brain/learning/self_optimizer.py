"""Self-Optimizer - Automatic parameter tuning and optimization.

Provides:
- Parameter optimization based on feedback
- Performance-based tuning
- A/B testing support
- Optimization history tracking
"""
from __future__ import annotations

import json
import sqlite3
import random
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable
from pathlib import Path


@dataclass
class ParameterConfig:
    """Parameter configuration."""
    name: str
    value: Any
    min_value: float | None = None
    max_value: float | None = None
    step: float | None = None
    description: str = ""
    category: str = "general"
    
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'ParameterConfig':
        return cls(**data)


@dataclass
class OptimizationRun:
    """Optimization run record."""
    id: str
    start_time: str
    end_time: str | None
    parameters_json: str
    metric_name: str
    initial_value: float
    best_value: float | None = None
    improvement: float | None = None
    status: str = 'running'  # running, completed, failed
    metadata_json: str = '{}'
    
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'OptimizationRun':
        return cls(**data)


class SelfOptimizer:
    """Self-optimizing system."""
    
    def __init__(self, db_path: str = "data/brain.db"):
        self.db_path = Path(db_path)
        self._init_schema()
        self._current_config: dict[str, Any] = {}
        self._optimization_history: list[OptimizationRun] = []
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_schema(self):
        """Initialize optimization tables."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Parameter configurations
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS parameter_configs (
                name TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                min_value REAL,
                max_value REAL,
                step REAL,
                description TEXT,
                category TEXT NOT NULL DEFAULT 'general',
                updated_at TEXT NOT NULL
            )
        """)
        
        # Optimization runs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS optimization_runs (
                id TEXT PRIMARY KEY,
                start_time TEXT NOT NULL,
                end_time TEXT,
                parameters_json TEXT NOT NULL,
                metric_name TEXT NOT NULL,
                initial_value REAL NOT NULL,
                best_value REAL,
                improvement REAL,
                status TEXT NOT NULL,
                metadata_json TEXT NOT NULL DEFAULT '{}'
            )
        """)
        
        # Optimization results
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS optimization_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                iteration INTEGER NOT NULL,
                parameters_json TEXT NOT NULL,
                metric_value REAL NOT NULL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (run_id) REFERENCES optimization_runs(id)
            )
        """)
        
        # Indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_results_run 
            ON optimization_results(run_id)
        """)
        
        conn.commit()
        conn.close()
    
    def register_parameter(self, name: str, value: Any,
                          min_value: float | None = None,
                          max_value: float | None = None,
                          step: float | None = None,
                          description: str = "",
                          category: str = "general"):
        """Register a tunable parameter."""
        now = datetime.now(timezone.utc).isoformat()
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO parameter_configs 
            (name, value, min_value, max_value, step, description, category, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            name,
            json.dumps(value),
            min_value,
            max_value,
            step,
            description,
            category,
            now
        ))
        
        # Update current config
        self._current_config[name] = value
        
        conn.commit()
        conn.close()
    
    def get_parameter(self, name: str) -> Any:
        """Get current parameter value."""
        if name in self._current_config:
            return self._current_config[name]
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT value FROM parameter_configs WHERE name = ?", (name,))
        row = cursor.fetchone()
        
        conn.close()
        
        if row:
            value = json.loads(row['value'])
            self._current_config[name] = value
            return value
        
        return None
    
    def set_parameter(self, name: str, value: Any):
        """Set parameter value."""
        now = datetime.now(timezone.utc).isoformat()
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE parameter_configs SET value = ?, updated_at = ? WHERE name = ?
        """, (json.dumps(value), now, name))
        
        self._current_config[name] = value
        
        conn.commit()
        conn.close()
    
    def start_optimization(self, metric_name: str,
                          parameters: dict[str, Any]) -> str:
        """Start an optimization run."""
        import uuid
        now = datetime.now(timezone.utc).isoformat()
        run_id = str(uuid.uuid4())
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO optimization_runs 
            (id, start_time, parameters_json, metric_name, initial_value, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            run_id,
            now,
            json.dumps(parameters),
            metric_name,
            0.0,  # Will be updated
            'running'
        ))
        
        conn.commit()
        conn.close()
        
        return run_id
    
    def record_iteration(self, run_id: str, iteration: int,
                        parameters: dict[str, Any], metric_value: float):
        """Record optimization iteration result."""
        now = datetime.now(timezone.utc).isoformat()
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Insert result
        cursor.execute("""
            INSERT INTO optimization_results 
            (run_id, iteration, parameters_json, metric_value, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (
            run_id,
            iteration,
            json.dumps(parameters),
            metric_value,
            now
        ))
        
        # Update best value
        cursor.execute("""
            SELECT MIN(metric_value) as best, MAX(metric_value) as worst
            FROM optimization_results WHERE run_id = ?
        """, (run_id,))
        
        row = cursor.fetchone()
        best = row['best']
        
        if best is not None:
            cursor.execute("""
                UPDATE optimization_runs 
                SET best_value = ?
                WHERE id = ?
            """, (best, run_id))
        
        conn.commit()
        conn.close()
    
    def complete_optimization(self, run_id: str, improvement: float):
        """Complete optimization run."""
        now = datetime.now(timezone.utc).isoformat()
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE optimization_runs 
            SET end_time = ?, status = ?, improvement = ?
            WHERE id = ?
        """, (now, 'completed', improvement, run_id))
        
        conn.commit()
        conn.close()
    
    def optimize_parameter(self, name: str, metric_function: Callable[[dict], float],
                          iterations: int = 10,
                          direction: str = 'minimize') -> dict[str, Any]:
        """Optimize a single parameter."""
        # Get parameter constraints
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM parameter_configs WHERE name = ?
        """, (name,))
        
        row = cursor.fetchone()
        
        if not row:
            raise ValueError(f"Parameter {name} not registered")
        
        min_val = row['min_value'] or 0
        max_val = row['max_value'] or 1
        step = row['step'] or (max_val - min_val) / 100
        
        conn.close()
        
        # Start optimization
        run_id = self.start_optimization(
            f"{name}_optimization",
            {name: self.get_parameter(name)}
        )
        
        best_value = float('inf') if direction == 'minimize' else float('-inf')
        best_params = {}
        
        for i in range(iterations):
            # Generate random parameter value
            value = random.uniform(min_val, max_val)
            params = {name: value}
            
            # Evaluate metric
            metric_value = metric_function(params)
            
            # Record iteration
            self.record_iteration(run_id, i, params, metric_value)
            
            # Update best
            if direction == 'minimize':
                if metric_value < best_value:
                    best_value = metric_value
                    best_params = params.copy()
            else:
                if metric_value > best_value:
                    best_value = metric_value
                    best_params = params.copy()
        
        # Calculate improvement
        current_value = self.get_parameter(name)
        if isinstance(current_value, (int, float)):
            improvement = abs(float(current_value) - best_value)
        else:
            improvement = 0.0
        
        # Complete optimization
        self.complete_optimization(run_id, improvement)
        
        # Update parameter if improved
        if best_params:
            self.set_parameter(name, best_params[name])
        
        return {
            'run_id': run_id,
            'best_value': best_value,
            'best_params': best_params,
            'improvement': improvement,
            'iterations': iterations
        }
    
    def get_optimization_history(self, limit: int = 50) -> list[OptimizationRun]:
        """Get optimization history."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM optimization_runs 
            ORDER BY start_time DESC 
            LIMIT ?
        """, (limit,))
        
        runs = []
        for row in cursor.fetchall():
            runs.append(OptimizationRun(
                id=row['id'],
                start_time=row['start_time'],
                end_time=row['end_time'],
                parameters_json=row['parameters_json'],
                metric_name=row['metric_name'],
                initial_value=row['initial_value'],
                best_value=row['best_value'],
                improvement=row['improvement'],
                status=row['status'],
                metadata_json=row['metadata_json']
            ))
        
        conn.close()
        return runs
    
    def get_optimization_results(self, run_id: str) -> list[dict[str, Any]]:
        """Get results for optimization run."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM optimization_results 
            WHERE run_id = ?
            ORDER BY iteration ASC
        """, (run_id,))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'iteration': row['iteration'],
                'parameters': json.loads(row['parameters_json']),
                'metric_value': row['metric_value'],
                'timestamp': row['timestamp']
            })
        
        conn.close()
        return results
    
    def get_statistics(self) -> dict[str, Any]:
        """Get optimization statistics."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        stats = {}
        
        # Total runs
        cursor.execute("SELECT COUNT(*) FROM optimization_runs")
        stats['total_runs'] = cursor.fetchone()[0]
        
        # Completed runs
        cursor.execute("SELECT COUNT(*) FROM optimization_runs WHERE status = 'completed'")
        stats['completed_runs'] = cursor.fetchone()[0]
        
        # Average improvement
        cursor.execute("SELECT AVG(improvement) FROM optimization_runs WHERE improvement IS NOT NULL")
        stats['avg_improvement'] = cursor.fetchone()[0] or 0
        
        # Total parameters
        cursor.execute("SELECT COUNT(*) FROM parameter_configs")
        stats['total_parameters'] = cursor.fetchone()[0]
        
        conn.close()
        return stats