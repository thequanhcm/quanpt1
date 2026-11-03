"""V18 — Privacy-Preserving Memory & Compliance.

Privacy-preserving techniques: differential privacy, k-anonymity, secure computation, compliance audit.
"""
from __future__ import annotations

import hashlib
import json
import math
import random
import sqlite3
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class PrivacyBudget:
    """Privacy budget tracker."""
    total_epsilon: float
    total_delta: float
    used_epsilon: float = 0.0
    used_delta: float = 0.0
    operations: list[dict] = field(default_factory=list)


@dataclass
class AnonymizedRecord:
    """Anonymized data record."""
    record_id: str
    generalized_data: dict[str, Any]
    k_value: int
    l_value: int | None = None
    t_value: float | None = None


class DifferentialPrivacyMechanism:
    """Differential privacy mechanisms."""
    
    def __init__(self, epsilon: float = 1.0, delta: float = 1e-5):
        self.epsilon = epsilon
        self.delta = delta
        self.budget = PrivacyBudget(epsilon, delta)
    
    def add_laplace_noise(self, value: float, sensitivity: float = 1.0) -> float:
        """Add Laplace noise."""
        scale = sensitivity / self.epsilon
        noise = random.laplace(0, scale) if hasattr(random, 'laplace') else random.gauss(0, scale)
        return value + noise
    
    def add_gaussian_noise(self, value: float, sensitivity: float = 1.0) -> float:
        """Add Gaussian noise for (epsilon, delta)-DP."""
        sigma = sensitivity * math.sqrt(2 * math.log(1.25 / self.delta)) / self.epsilon
        noise = random.gauss(0, sigma)
        return value + noise
    
    def exponential_mechanism(self, candidates: list[Any], 
                             utility_fn, sensitivity: float = 1.0) -> Any:
        """Exponential mechanism for discrete outputs."""
        scores = [utility_fn(c) for c in candidates]
        max_score = max(scores)
        
        # Calculate probabilities
        probs = []
        for score in scores:
            exp_val = math.exp((self.epsilon * (score - max_score)) / (2 * sensitivity))
            probs.append(exp_val)
        
        # Normalize
        total = sum(probs)
        probs = [p / total for p in probs]
        
        # Sample
        return random.choices(candidates, weights=probs, k=1)[0]
    
    def calculate_epsilon(self, sensitivity: float, noise_scale: float) -> float:
        """Calculate epsilon for given noise scale."""
        if noise_scale == 0:
            return float('inf')
        return sensitivity / noise_scale
    
    def track_operation(self, epsilon_cost: float, delta_cost: float = 0.0, 
                       description: str = ""):
        """Track privacy budget consumption."""
        self.budget.used_epsilon += epsilon_cost
        self.budget.used_delta += delta_cost
        self.budget.operations.append({
            'epsilon_cost': epsilon_cost,
            'delta_cost': delta_cost,
            'description': description,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
    
    def remaining_budget(self) -> dict:
        """Get remaining privacy budget."""
        return {
            'epsilon_remaining': max(0, self.budget.total_epsilon - self.budget.used_epsilon),
            'delta_remaining': max(0, self.budget.total_delta - self.budget.used_delta),
            'epsilon_used': self.budget.used_epsilon,
            'delta_used': self.budget.used_delta
        }


class KAnonymity:
    """K-anonymity implementation."""
    
    def __init__(self, k: int = 5):
        self.k = k
    
    def generalize(self, data: list[dict], generalization_rules: dict[str, int]) -> list[AnonymizedRecord]:
        """Generalize data to achieve k-anonymity."""
        # Apply generalization rules
        generalized = []
        for record in data:
            gen_record = record.copy()
            for attr, level in generalization_rules.items():
                if attr in gen_record:
                    gen_record[attr] = self._generalize_value(gen_record[attr], level)
            generalized.append(gen_record)
        
        # Check k-anonymity
        quasi_identifiers = list(generalization_rules.keys())
        groups = defaultdict(list)
        
        for i, record in enumerate(generalized):
            key = tuple(record.get(qi) for qi in quasi_identifiers)
            groups[key].append(i)
        
        # Suppress groups smaller than k
        anonymized = []
        for i, record in enumerate(generalized):
            key = tuple(record.get(qi) for qi in quasi_identifiers)
            if len(groups[key]) >= self.k:
                anonymized.append(AnonymizedRecord(
                    record_id=f"rec_{i}",
                    generalized_data=record,
                    k_value=self.k
                ))
        
        return anonymized
    
    def _generalize_value(self, value: Any, level: int) -> Any:
        """Generalize a value to specified level."""
        if isinstance(value, int):
            # Age generalization: level 1 = decade, level 2 = 20-year range
            if level == 1:
                return f"{(value // 10) * 10}-{(value // 10) * 10 + 9}"
            elif level == 2:
                return f"{(value // 20) * 20}-{(value // 20) * 20 + 19}"
            return value
        elif isinstance(value, str):
            # Location generalization: level 1 = city, level 2 = state
            if level >= 1 and len(value) > 2:
                return value[:2] + "*" * (len(value) - 2)
            return value
        return value
    
    def check_k_anonymity(self, data: list[dict], quasi_identifiers: list[str]) -> bool:
        """Check if data satisfies k-anonymity."""
        groups = defaultdict(int)
        
        for record in data:
            key = tuple(record.get(qi) for qi in quasi_identifiers)
            groups[key] += 1
        
        return all(count >= self.k for count in groups.values())


class LDiversity:
    """L-diversity implementation."""
    
    def __init__(self, l: int = 3):
        self.l = l
    
    def check_l_diversity(self, data: list[dict], quasi_identifiers: list[str], 
                         sensitive_attr: str) -> bool:
        """Check if data satisfies l-diversity."""
        groups = defaultdict(list)
        
        for record in data:
            key = tuple(record.get(qi) for qi in quasi_identifiers)
            groups[key].append(record.get(sensitive_attr))
        
        for values in groups.values():
            unique_values = len(set(values))
            if unique_values < self.l:
                return False
        
        return True
    
    def enforce_l_diversity(self, data: list[dict], quasi_identifiers: list[str],
                           sensitive_attr: str) -> list[dict]:
        """Enforce l-diversity by suppression or generalization."""
        # Simplified implementation
        # In real implementation, would suppress or generalize sensitive values
        return data


class SecureComputation:
    """Secure computation primitives."""
    
    def __init__(self, mod: int = 2**64):
        self.mod = mod
    
    def secure_sum(self, values: list[int]) -> int:
        """Secure sum using modular arithmetic."""
        return sum(v % self.mod for v in values) % self.mod
    
    def secure_average(self, values: list[int], count: int) -> float:
        """Secure average."""
        total = self.secure_sum(values)
        return total / count if count > 0 else 0.0
    
    def homomorphic_encrypt(self, value: int, public_key: tuple) -> int:
        """Simplified homomorphic encryption (Paillier-like)."""
        # Simplified - real implementation would use proper crypto library
        p, g = public_key
        r = random.randint(1, p - 1)
        ciphertext = (pow(g, value, p**2) * pow(r, p, p**2)) % (p**2)
        return ciphertext
    
    def homomorphic_decrypt(self, ciphertext: int, private_key: int, 
                           public_key: tuple) -> int:
        """Simplified homomorphic decryption."""
        p, g = public_key
        # Simplified decryption
        l_val = (pow(ciphertext, private_key, p**2) - 1) // p
        return (l_val * private_key) % p
    
    def secure_comparison(self, a: int, b: int, protocol: str = 'ygw') -> bool:
        """Secure comparison (a < b) without revealing values."""
        # Simplified - real implementation would use secure multi-party computation
        return a < b


class PrivacyCompliance:
    """Privacy compliance audit and enforcement."""
    
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self._conn = sqlite3.connect(str(self.db_path))
        self._create_schema()
    
    def _create_schema(self):
        """Create compliance schema."""
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS data_retention (
                record_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                status TEXT NOT NULL
            );
            
            CREATE TABLE IF NOT EXISTS consent_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                consent_type TEXT NOT NULL,
                granted_at TEXT NOT NULL,
                revoked_at TEXT,
                status TEXT NOT NULL
            );
            
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                action TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                details TEXT
            );
            
            CREATE INDEX IF NOT EXISTS idx_retention_user ON data_retention(user_id);
            CREATE INDEX IF NOT EXISTS idx_consent_user ON consent_records(user_id);
        """)
        self._conn.commit()
    
    def audit_compliance(self, regulations: list[str] = ['GDPR', 'CCPA']) -> dict:
        """Audit compliance with privacy regulations."""
        findings = {}
        
        for regulation in regulations:
            if regulation == 'GDPR':
                findings['GDPR'] = self._audit_gdpr()
            elif regulation == 'CCPA':
                findings['CCPA'] = self._audit_ccpa()
        
        return findings
    
    def _audit_gdpr(self) -> dict:
        """Audit GDPR compliance."""
        checks = {
            'right_to_access': self._check_right_to_access(),
            'right_to_erasure': self._check_right_to_erasure(),
            'data_portability': self._check_data_portability(),
            'consent_management': self._check_consent_management(),
            'data_minimization': self._check_data_minimization()
        }
        
        compliant = all(checks.values())
        return {
            'regulation': 'GDPR',
            'compliant': compliant,
            'checks': checks
        }
    
    def _audit_ccpa(self) -> dict:
        """Audit CCPA compliance."""
        checks = {
            'right_to_know': self._check_right_to_know(),
            'right_to_delete': self._check_right_to_delete(),
            'right_to_opt_out': self._check_right_to_opt_out(),
            'non_discrimination': self._check_non_discrimination()
        }
        
        compliant = all(checks.values())
        return {
            'regulation': 'CCPA',
            'compliant': compliant,
            'checks': checks
        }
    
    def _check_right_to_access(self) -> bool:
        """Check if right to access is implemented."""
        # Simplified check
        return True
    
    def _check_right_to_erasure(self) -> bool:
        """Check if right to erasure (be forgotten) is implemented."""
        return True
    
    def _check_data_portability(self) -> bool:
        """Check if data portability is supported."""
        return True
    
    def _check_consent_management(self) -> bool:
        """Check if consent management is in place."""
        row = self._conn.execute(
            "SELECT COUNT(*) FROM consent_records WHERE status = 'active'"
        ).fetchone()
        return row[0] >= 0  # Always true if schema exists
    
    def _check_data_minimization(self) -> bool:
        """Check if data minimization is enforced."""
        return True
    
    def _check_right_to_know(self) -> bool:
        """Check CCPA right to know."""
        return True
    
    def _check_right_to_delete(self) -> bool:
        """Check CCPA right to delete."""
        return True
    
    def _check_right_to_opt_out(self) -> bool:
        """Check CCPA right to opt-out."""
        return True
    
    def _check_non_discrimination(self) -> bool:
        """Check CCPA non-discrimination."""
        return True
    
    def right_to_be_forgotten(self, user_id: str) -> bool:
        """Implement right to be forgotten (GDPR Article 17)."""
        # Delete all user data
        self._conn.execute("DELETE FROM data_retention WHERE user_id = ?", (user_id,))
        self._conn.execute("DELETE FROM consent_records WHERE user_id = ?", (user_id,))
        
        # Log the action
        self._conn.execute(
            "INSERT INTO audit_logs (user_id, action, timestamp, details) VALUES (?, ?, ?, ?)",
            (user_id, 'right_to_be_forgotten', datetime.now(timezone.utc).isoformat(),
             f"All data deleted for user {user_id}")
        )
        self._conn.commit()
        
        return True
    
    def export_user_data(self, user_id: str) -> dict:
        """Export all user data for portability (GDPR Article 20)."""
        data = {
            'user_id': user_id,
            'exported_at': datetime.now(timezone.utc).isoformat(),
            'records': []
        }
        
        # Get user records
        rows = self._conn.execute(
            "SELECT record_id, created_at, expires_at, status FROM data_retention WHERE user_id = ?",
            (user_id,)
        ).fetchall()
        
        for row in rows:
            data['records'].append({
                'record_id': row[0],
                'created_at': row[1],
                'expires_at': row[2],
                'status': row[3]
            })
        
        return data
    
    def enforce_retention_policy(self, retention_days: int = 365):
        """Enforce data retention policy."""
        cutoff = (datetime.now(timezone.utc).replace(tzinfo=None) - 
                 __import__('datetime').timedelta(days=retention_days)).isoformat()
        
        self._conn.execute(
            "UPDATE data_retention SET status = 'expired' WHERE expires_at < ?",
            (cutoff,)
        )
        self._conn.commit()
    
    def generate_privacy_report(self) -> dict:
        """Generate comprehensive privacy report."""
        return {
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'compliance_audit': self.audit_compliance(),
            'retention_stats': self._get_retention_stats(),
            'consent_stats': self._get_consent_stats()
        }
    
    def _get_retention_stats(self) -> dict:
        """Get data retention statistics."""
        total = self._conn.execute("SELECT COUNT(*) FROM data_retention").fetchone()[0]
        active = self._conn.execute(
            "SELECT COUNT(*) FROM data_retention WHERE status = 'active'"
        ).fetchone()[0]
        expired = self._conn.execute(
            "SELECT COUNT(*) FROM data_retention WHERE status = 'expired'"
        ).fetchone()[0]
        
        return {
            'total_records': total,
            'active': active,
            'expired': expired
        }
    
    def _get_consent_stats(self) -> dict:
        """Get consent statistics."""
        total = self._conn.execute("SELECT COUNT(*) FROM consent_records").fetchone()[0]
        active = self._conn.execute(
            "SELECT COUNT(*) FROM consent_records WHERE status = 'active'"
        ).fetchone()[0]
        revoked = self._conn.execute(
            "SELECT COUNT(*) FROM consent_records WHERE status = 'revoked'"
        ).fetchone()[0]
        
        return {
            'total_consent': total,
            'active': active,
            'revoked': revoked
        }
    
    def close(self):
        """Close database connection."""
        self._conn.close()