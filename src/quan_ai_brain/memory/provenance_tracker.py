"""V31 Provenance Tracker - Full lineage tracking for knowledge units.

Tracks:
- Source information (type, ref, version)
- Ingestion metadata (when, who)
- Verification trail (when, who, notes)
- Temporal information (effective_from/until, observed_at)
- Lineage (derived_from, supersedes)
- Conflict history

All provenance events are immutable and logged for audit.
"""
from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Optional
import uuid

from quan_ai_brain.memory.models_v31 import (
    KnowledgeUnit,
    KnowledgeProvenanceV31,
    VersionEntry,
    KnowledgeType,
)

logger = logging.getLogger(__name__)


class ProvenanceTracker:
    """Tracks and manages provenance for knowledge units."""
    
    def __init__(self, db_connection):
        """Initialize with database connection.
        
        Args:
            db_connection: SQLite connection to brain.db
        """
        self.db = db_connection
        self._ensure_tables()
    
    def _ensure_tables(self):
        """Create provenance tracking tables if they don't exist."""
        cursor = self.db.cursor()
        
        # Provenance events log (immutable)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS provenance_events (
                id TEXT PRIMARY KEY,
                knowledge_unit_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                event_data TEXT NOT NULL,
                occurred_at TEXT NOT NULL,
                occurred_by TEXT NOT NULL,
                FOREIGN KEY (knowledge_unit_id) REFERENCES knowledge_units(id)
            )
        """)
        
        # Version history
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_version_history (
                id TEXT PRIMARY KEY,
                knowledge_unit_id TEXT NOT NULL,
                version INTEGER NOT NULL,
                content_hash TEXT NOT NULL,
                changed_fields TEXT NOT NULL,
                changed_by TEXT NOT NULL,
                changed_at TEXT NOT NULL,
                reason TEXT,
                FOREIGN KEY (knowledge_unit_id) REFERENCES knowledge_units(id)
            )
        """)
        
        # Conflict records
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_conflicts (
                id TEXT PRIMARY KEY,
                knowledge_unit_1_id TEXT NOT NULL,
                knowledge_unit_2_id TEXT NOT NULL,
                conflict_type TEXT NOT NULL,
                conflict_description TEXT,
                detected_at TEXT NOT NULL,
                resolution_status TEXT NOT NULL,
                resolution_decision TEXT,
                resolved_by TEXT,
                resolved_at TEXT,
                FOREIGN KEY (knowledge_unit_1_id) REFERENCES knowledge_units(id),
                FOREIGN KEY (knowledge_unit_2_id) REFERENCES knowledge_units(id)
            )
        """)
        
        # Create indexes for performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_provenance_events_ku 
            ON provenance_events(knowledge_unit_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_version_history_ku 
            ON knowledge_version_history(knowledge_unit_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_conflicts_ku1 
            ON knowledge_conflicts(knowledge_unit_1_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_conflicts_ku2 
            ON knowledge_conflicts(knowledge_unit_2_id)
        """)
        
        self.db.commit()
        logger.info("Provenance tracking tables initialized")
    
    def _now(self) -> str:
        """Get current UTC timestamp in ISO format."""
        return datetime.now(timezone.utc).isoformat()
    
    def _generate_id(self) -> str:
        """Generate unique ID."""
        return str(uuid.uuid4())
    
    def _compute_content_hash(self, content: str) -> str:
        """Compute SHA-256 hash of content."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def log_event(
        self,
        knowledge_unit_id: str,
        event_type: str,
        event_data: dict[str, Any],
        occurred_by: str,
    ) -> str:
        """Log a provenance event.
        
        Args:
            knowledge_unit_id: ID of knowledge unit
            event_type: Type of event (INGESTED, VERIFIED, SUPERSEDED, etc.)
            event_data: JSON-serializable event payload
            occurred_by: Who/what triggered the event
            
        Returns:
            Event ID
        """
        event_id = self._generate_id()
        timestamp = self._now()
        
        cursor = self.db.cursor()
        cursor.execute("""
            INSERT INTO provenance_events 
            (id, knowledge_unit_id, event_type, event_data, occurred_at, occurred_by)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            event_id,
            knowledge_unit_id,
            event_type,
            json.dumps(event_data),
            timestamp,
            occurred_by,
        ))
        self.db.commit()
        
        logger.debug(f"Logged provenance event {event_id}: {event_type} for KU {knowledge_unit_id}")
        return event_id
    
    def get_provenance_chain(self, knowledge_unit_id: str) -> list[dict[str, Any]]:
        """Get full provenance chain for a knowledge unit.
        
        Args:
            knowledge_unit_id: ID of knowledge unit
            
        Returns:
            List of events in chronological order
        """
        cursor = self.db.cursor()
        cursor.execute("""
            SELECT id, event_type, event_data, occurred_at, occurred_by
            FROM provenance_events
            WHERE knowledge_unit_id = ?
            ORDER BY occurred_at ASC
        """, (knowledge_unit_id,))
        
        events = []
        for row in cursor.fetchall():
            events.append({
                "id": row[0],
                "event_type": row[1],
                "event_data": json.loads(row[2]),
                "occurred_at": row[3],
                "occurred_by": row[4],
            })
        
        return events
    
    def create_version_entry(
        self,
        knowledge_unit_id: str,
        version: int,
        changed_fields: list[str],
        changed_by: str,
        reason: str,
        content: str,
    ) -> VersionEntry:
        """Create and log a version entry.
        
        Args:
            knowledge_unit_id: ID of knowledge unit
            version: Version number
            changed_fields: List of fields that changed
            changed_by: Who made the change
            reason: Reason for change
            content: Current content (for hash)
            
        Returns:
            VersionEntry object
        """
        entry_id = self._generate_id()
        timestamp = self._now()
        content_hash = self._compute_content_hash(content)
        
        entry = VersionEntry(
            version=version,
            changed_fields=changed_fields,
            changed_by=changed_by,
            changed_at=timestamp,
            reason=reason,
            content_hash=content_hash,
        )
        
        cursor = self.db.cursor()
        cursor.execute("""
            INSERT INTO knowledge_version_history
            (id, knowledge_unit_id, version, content_hash, changed_fields, changed_by, changed_at, reason)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            entry_id,
            knowledge_unit_id,
            version,
            content_hash,
            json.dumps(changed_fields),
            changed_by,
            timestamp,
            reason,
        ))
        self.db.commit()
        
        logger.debug(f"Created version entry {entry_id} v{version} for KU {knowledge_unit_id}")
        return entry
    
    def get_version_history(self, knowledge_unit_id: str) -> list[VersionEntry]:
        """Get version history for a knowledge unit.
        
        Args:
            knowledge_unit_id: ID of knowledge unit
            
        Returns:
            List of VersionEntry objects in chronological order
        """
        cursor = self.db.cursor()
        cursor.execute("""
            SELECT id, version, content_hash, changed_fields, changed_by, changed_at, reason
            FROM knowledge_version_history
            WHERE knowledge_unit_id = ?
            ORDER BY version ASC
        """, (knowledge_unit_id,))
        
        history = []
        for row in cursor.fetchall():
            history.append(VersionEntry(
                version=row[1],
                changed_fields=json.loads(row[3]),
                changed_by=row[4],
                changed_at=row[5],
                reason=row[6],
                content_hash=row[2],
            ))
        
        return history
    
    def create_conflict_record(
        self,
        ku1_id: str,
        ku2_id: str,
        conflict_type: str,
        conflict_description: str,
        detected_by: str,
    ) -> str:
        """Create a conflict record.
        
        Args:
            ku1_id: First knowledge unit ID
            ku2_id: Second knowledge unit ID
            conflict_type: Type of conflict (SEMANTIC, TEMPORAL, LOGICAL, SOURCE)
            conflict_description: Description of the conflict
            detected_by: Who/what detected the conflict
            
        Returns:
            Conflict ID
        """
        conflict_id = self._generate_id()
        timestamp = self._now()
        
        cursor = self.db.cursor()
        cursor.execute("""
            INSERT INTO knowledge_conflicts
            (id, knowledge_unit_1_id, knowledge_unit_2_id, conflict_type, 
             conflict_description, detected_at, resolution_status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            conflict_id,
            ku1_id,
            ku2_id,
            conflict_type,
            conflict_description,
            timestamp,
            "unresolved",
        ))
        self.db.commit()
        
        # Update conflict_ids in both knowledge units' provenance
        self._add_conflict_to_provenance(ku1_id, conflict_id)
        self._add_conflict_to_provenance(ku2_id, conflict_id)
        
        logger.info(f"Created conflict record {conflict_id}: {conflict_type} between {ku1_id} and {ku2_id}")
        return conflict_id
    
    def _add_conflict_to_provenance(self, knowledge_unit_id: str, conflict_id: str):
        """Add conflict ID to knowledge unit's provenance."""
        cursor = self.db.cursor()
        cursor.execute("""
            SELECT conflict_ids FROM knowledge_units WHERE id = ?
        """, (knowledge_unit_id,))
        
        row = cursor.fetchone()
        if row:
            conflict_ids = json.loads(row[0]) if row[0] else []
            if conflict_id not in conflict_ids:
                conflict_ids.append(conflict_id)
                cursor.execute("""
                    UPDATE knowledge_units SET conflict_ids = ? WHERE id = ?
                """, (json.dumps(conflict_ids), knowledge_unit_id))
                self.db.commit()
    
    def resolve_conflict(
        self,
        conflict_id: str,
        resolution_decision: str,
        resolved_by: str,
    ):
        """Mark a conflict as resolved.
        
        Args:
            conflict_id: Conflict ID
            resolution_decision: How it was resolved
            resolved_by: Who resolved it
        """
        timestamp = self._now()
        
        cursor = self.db.cursor()
        cursor.execute("""
            UPDATE knowledge_conflicts
            SET resolution_status = 'resolved',
                resolution_decision = ?,
                resolved_by = ?,
                resolved_at = ?
            WHERE id = ?
        """, (resolution_decision, resolved_by, timestamp, conflict_id))
        self.db.commit()
        
        logger.info(f"Resolved conflict {conflict_id}: {resolution_decision}")
    
    def get_conflicts_for_ku(self, knowledge_unit_id: str) -> list[dict[str, Any]]:
        """Get all conflicts involving a knowledge unit.
        
        Args:
            knowledge_unit_id: ID of knowledge unit
            
        Returns:
            List of conflict records
        """
        cursor = self.db.cursor()
        cursor.execute("""
            SELECT id, knowledge_unit_1_id, knowledge_unit_2_id, conflict_type,
                   conflict_description, detected_at, resolution_status,
                   resolution_decision, resolved_by, resolved_at
            FROM knowledge_conflicts
            WHERE knowledge_unit_1_id = ? OR knowledge_unit_2_id = ?
            ORDER BY detected_at DESC
        """, (knowledge_unit_id, knowledge_unit_id))
        
        conflicts = []
        for row in cursor.fetchall():
            conflicts.append({
                "id": row[0],
                "ku1_id": row[1],
                "ku2_id": row[2],
                "conflict_type": row[3],
                "conflict_description": row[4],
                "detected_at": row[5],
                "resolution_status": row[6],
                "resolution_decision": row[7],
                "resolved_by": row[8],
                "resolved_at": row[9],
            })
        
        return conflicts
    
    def build_provenance(
        self,
        source_type: str,
        source_ref: str,
        source_version: str,
        ingested_by: str,
        verification_state: str = "unverified",
        effective_from: str | None = None,
        effective_until: str | None = None,
        observed_at: str | None = None,
        derived_from: list[str] | None = None,
        supersedes: list[str] | None = None,
    ) -> KnowledgeProvenanceV31:
        """Build a new provenance record.
        
        Args:
            source_type: Type of source
            source_ref: Reference to source
            source_version: Version of source
            ingested_by: Who/what ingested
            verification_state: Initial verification state
            effective_from: When knowledge became effective
            effective_until: When knowledge expired
            observed_at: When event was observed
            derived_from: Parent knowledge IDs
            supersedes: IDs this replaces
            
        Returns:
            KnowledgeProvenanceV31 object
        """
        return KnowledgeProvenanceV31(
            source_type=source_type,
            source_ref=source_ref,
            source_version=source_version,
            ingested_at=self._now(),
            ingested_by=ingested_by,
            verification_state=verification_state,
            verified_at=None,
            verified_by=None,
            review_notes="",
            effective_from=effective_from,
            effective_until=effective_until,
            observed_at=observed_at,
            expires_at=None,
            conflict_ids=[],
            derived_from=derived_from or [],
            supersedes=supersedes or [],
        )
    
    def verify_knowledge(
        self,
        knowledge_unit_id: str,
        verified_by: str,
        verification_state: str = "verified",
        review_notes: str = "",
    ):
        """Mark knowledge as verified.
        
        Args:
            knowledge_unit_id: ID of knowledge unit
            verified_by: Who verified
            verification_state: Verification state
            review_notes: Notes about verification
        """
        timestamp = self._now()
        
        # Update provenance
        cursor = self.db.cursor()
        cursor.execute("""
            UPDATE knowledge_units
            SET provenance_json = json_set(
                provenance_json,
                '$.verification_state', ?,
                '$.verified_at', ?,
                '$.verified_by', ?,
                '$.review_notes', ?
            )
            WHERE id = ?
        """, (verification_state, timestamp, verified_by, review_notes, knowledge_unit_id))
        self.db.commit()
        
        # Log event
        self.log_event(
            knowledge_unit_id,
            "VERIFIED",
            {
                "verification_state": verification_state,
                "verified_by": verified_by,
                "review_notes": review_notes,
            },
            verified_by,
        )
        
        logger.info(f"Verified knowledge unit {knowledge_unit_id} by {verified_by}")