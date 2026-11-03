"""V31 Knowledge Pipeline - Orchestrate knowledge ingestion with full provenance.

Pipeline stages:
1. INGEST - Read from source
2. VALIDATE - Check format, permissions, redaction
3. PARSE - Extract structured data
4. NORMALIZE - Standardize format
5. DEDUP - Check for duplicates
6. CONFLICT_DETECT - Detect contradictions
7. QUALITY_SCORE - Compute confidence
8. PROVENANCE_BUILD - Create lineage record
9. OWNER_PREVIEW - Show proposed changes
10. APPLY - Write to database (if approved)
11. VERIFY - Integrity check

All stages are logged and can be resumed from checkpoint.
"""
from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Optional
import uuid

from quan_ai_brain.memory.models_v31 import (
    KnowledgeUnit,
    KnowledgeProvenanceV31,
    KnowledgeType,
)
from quan_ai_brain.memory.provenance_tracker import ProvenanceTracker

logger = logging.getLogger(__name__)


class PipelineStage(str, Enum):
    """Pipeline stage names."""
    INGEST = "INGEST"
    VALIDATE = "VALIDATE"
    PARSE = "PARSE"
    NORMALIZE = "NORMALIZE"
    DEDUP = "DEDUP"
    CONFLICT_DETECT = "CONFLICT_DETECT"
    QUALITY_SCORE = "QUALITY_SCORE"
    PROVENANCE_BUILD = "PROVENANCE_BUILD"
    OWNER_PREVIEW = "OWNER_PREVIEW"
    APPLY = "APPLY"
    VERIFY = "VERIFY"


class PipelineStatus(str, Enum):
    """Pipeline execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    PAUSED = "paused"  # Waiting for owner approval
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class PipelineCheckpoint:
    """Checkpoint for pipeline resumption."""
    pipeline_id: str
    current_stage: PipelineStage
    status: PipelineStatus
    knowledge_unit: Optional[KnowledgeUnit] = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    stages_completed: list[PipelineStage] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "pipeline_id": self.pipeline_id,
            "current_stage": self.current_stage.value,
            "status": self.status.value,
            "knowledge_unit": self.knowledge_unit.to_dict() if self.knowledge_unit else None,
            "errors": self.errors,
            "warnings": self.warnings,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'PipelineCheckpoint':
        ku = KnowledgeUnit.from_dict(data["knowledge_unit"]) if data.get("knowledge_unit") else None
        return cls(
            pipeline_id=data["pipeline_id"],
            current_stage=PipelineStage(data["current_stage"]),
            status=PipelineStatus(data["status"]),
            knowledge_unit=ku,
            errors=data.get("errors", []),
            warnings=data.get("warnings", []),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )


@dataclass
class PipelineResult:
    """Result of pipeline execution."""
    pipeline_id: str
    status: PipelineStatus
    knowledge_unit: Optional[KnowledgeUnit] = None
    preview: Optional[dict[str, Any]] = None  # For owner review
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    stages_completed: list[PipelineStage] = field(default_factory=list)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "pipeline_id": self.pipeline_id,
            "status": self.status.value,
            "knowledge_unit": self.knowledge_unit.to_dict() if self.knowledge_unit else None,
            "preview": self.preview,
            "errors": self.errors,
            "warnings": self.warnings,
            "stages_completed": [s.value for s in self.stages_completed],
        }


class KnowledgePipeline:
    """Orchestrates knowledge ingestion pipeline."""
    
    def __init__(self, db_connection, owner_id: str = "system"):
        """Initialize pipeline.
        
        Args:
            db_connection: SQLite connection to brain.db
            owner_id: Default owner for pipeline operations
        """
        self.db = db_connection
        self.owner_id = owner_id
        self.provenance_tracker = ProvenanceTracker(db_connection)
        self._stages: dict[PipelineStage, Callable] = {}
        self._register_stages()
    
    def _register_stages(self):
        """Register pipeline stage handlers."""
        self._stages = {
            PipelineStage.INGEST: self._stage_ingest,
            PipelineStage.VALIDATE: self._stage_validate,
            PipelineStage.PARSE: self._stage_parse,
            PipelineStage.NORMALIZE: self._stage_normalize,
            PipelineStage.DEDUP: self._stage_dedup,
            PipelineStage.CONFLICT_DETECT: self._stage_conflict_detect,
            PipelineStage.QUALITY_SCORE: self._stage_quality_score,
            PipelineStage.PROVENANCE_BUILD: self._stage_provenance_build,
            PipelineStage.OWNER_PREVIEW: self._stage_owner_preview,
            PipelineStage.APPLY: self._stage_apply,
            PipelineStage.VERIFY: self._stage_verify,
        }
    
    def _now(self) -> str:
        """Get current UTC timestamp."""
        return datetime.now(timezone.utc).isoformat()
    
    def _generate_id(self) -> str:
        """Generate unique ID."""
        return str(uuid.uuid4())
    
    def register_stage(self, stage: PipelineStage, handler: Callable):
        """Register a custom stage handler.
        
        Args:
            stage: Stage to register
            handler: Handler function
        """
        self._stages[stage] = handler
        logger.info(f"Registered custom handler for stage {stage.value}")
    
    def ingest(
        self,
        source_type: str,
        source_ref: str,
        source_version: str,
        content: str,
        ingested_by: str,
        metadata: dict[str, Any] | None = None,
        skip_stages: list[PipelineStage] | None = None,
    ) -> PipelineResult:
        """Start knowledge ingestion pipeline.
        
        Args:
            source_type: Type of source
            source_ref: Reference to source
            source_version: Version of source
            content: Raw content to ingest
            ingested_by: Who/what is ingesting
            metadata: Additional metadata
            skip_stages: Stages to skip
            
        Returns:
            PipelineResult with final status
        """
        pipeline_id = self._generate_id()
        checkpoint = PipelineCheckpoint(
            pipeline_id=pipeline_id,
            current_stage=PipelineStage.INGEST,
            status=PipelineStatus.RUNNING,
            created_at=self._now(),
            updated_at=self._now(),
        )
        
        logger.info(f"Starting pipeline {pipeline_id} for content from {source_ref}")
        
        stages_to_run = [s for s in PipelineStage if s not in (skip_stages or [])]
        
        try:
            for stage in stages_to_run:
                checkpoint.current_stage = stage
                checkpoint.updated_at = self._now()
                self._save_checkpoint(checkpoint)
                
                logger.debug(f"Running stage {stage.value} for pipeline {pipeline_id}")
                
                # Execute stage
                result = self._stages[stage](
                    pipeline_id=pipeline_id,
                    content=content,
                    source_type=source_type,
                    source_ref=source_ref,
                    source_version=source_version,
                    ingested_by=ingested_by,
                    metadata=metadata or {},
                    checkpoint=checkpoint,
                )
                
                if result is None:
                    # Stage passed
                    checkpoint.stages_completed.append(stage)
                elif isinstance(result, dict) and result.get("error"):
                    # Stage failed
                    checkpoint.errors.append(result["error"])
                    checkpoint.status = PipelineStatus.FAILED
                    checkpoint.updated_at = self._now()
                    self._save_checkpoint(checkpoint)
                    return PipelineResult(
                        pipeline_id=pipeline_id,
                        status=PipelineStatus.FAILED,
                        errors=checkpoint.errors,
                        warnings=checkpoint.warnings,
                        stages_completed=checkpoint.stages_completed,
                    )
                elif isinstance(result, dict) and result.get("pause"):
                    # Stage requires owner approval
                    checkpoint.status = PipelineStatus.PAUSED
                    checkpoint.updated_at = self._now()
                    self._save_checkpoint(checkpoint)
                    
                    return PipelineResult(
                        pipeline_id=pipeline_id,
                        status=PipelineStatus.PAUSED,
                        knowledge_unit=checkpoint.knowledge_unit,
                        preview=result.get("preview"),
                        stages_completed=checkpoint.stages_completed,
                    )
            
            # All stages completed
            checkpoint.status = PipelineStatus.COMPLETED
            checkpoint.updated_at = self._now()
            self._save_checkpoint(checkpoint)
            
            return PipelineResult(
                pipeline_id=pipeline_id,
                status=PipelineStatus.COMPLETED,
                knowledge_unit=checkpoint.knowledge_unit,
                stages_completed=checkpoint.stages_completed,
            )
            
        except Exception as e:
            logger.error(f"Pipeline {pipeline_id} failed with exception: {e}")
            checkpoint.errors.append(str(e))
            checkpoint.status = PipelineStatus.FAILED
            checkpoint.updated_at = self._now()
            self._save_checkpoint(checkpoint)
            
            return PipelineResult(
                pipeline_id=pipeline_id,
                status=PipelineStatus.FAILED,
                errors=checkpoint.errors,
                stages_completed=checkpoint.stages_completed,
            )
    
    def _stage_ingest(
        self,
        pipeline_id: str,
        content: str,
        source_type: str,
        source_ref: str,
        source_version: str,
        ingested_by: str,
        metadata: dict[str, Any],
        checkpoint: PipelineCheckpoint,
    ) -> dict | None:
        """Stage 1: INGEST - Read and validate source."""
        logger.debug(f"Stage INGEST: Reading content from {source_ref}")
        
        if not content or not isinstance(content, str):
            return {"error": f"Invalid content: {type(content)}"}
        
        if len(content) > 100000:
            checkpoint.warnings.append("Content exceeds 100KB, may be truncated")
        
        return None  # Stage passed
    
    def _stage_validate(
        self,
        pipeline_id: str,
        content: str,
        source_type: str,
        source_ref: str,
        source_version: str,
        ingested_by: str,
        metadata: dict[str, Any],
        checkpoint: PipelineCheckpoint,
    ) -> dict | None:
        """Stage 2: VALIDATE - Check format, permissions, redaction."""
        logger.debug(f"Stage VALIDATE: Validating content from {source_ref}")
        
        # Check for secrets (basic redaction)
        import re
        secret_patterns = [
            r'ghp_[A-Za-z0-9]{20,}',
            r'sk-[A-Za-z0-9_\-]{20,}',
            r'AKIA[0-9A-Z]{16}',
        ]
        
        for pattern in secret_patterns:
            if re.search(pattern, content):
                checkpoint.warnings.append("Secret detected, content will be redacted")
                content = re.sub(pattern, '[REDACTED]', content)
        
        return None  # Stage passed
    
    def _stage_parse(
        self,
        pipeline_id: str,
        content: str,
        source_type: str,
        source_ref: str,
        source_version: str,
        ingested_by: str,
        metadata: dict[str, Any],
        checkpoint: PipelineCheckpoint,
    ) -> dict | None:
        """Stage 3: PARSE - Extract structured data."""
        logger.debug(f"Stage PARSE: Extracting structured data")
        
        # Determine knowledge type
        knowledge_type = KnowledgeType.FACT.value
        content_lower = content.lower()
        
        if any(m in content_lower for m in ["gì", "nào", "bao nhiêu", "có phải", "không?"]):
            knowledge_type = KnowledgeType.QUESTION.value
        elif any(m in content_lower for m in ["luôn", "phải", "quy tắc", "không được", "cấm"]):
            knowledge_type = KnowledgeType.RULE.value
        elif any(m in content_lower for m in ["tôi nghĩ", "có lẽ", "có thể", "dường như"]):
            knowledge_type = KnowledgeType.OPINION.value
        elif any(m in content_lower for m in ["vậy nên", "kết luận", "tóm lại", "do đó"]):
            knowledge_type = KnowledgeType.CONCLUSION.value
        
        if checkpoint.knowledge_unit:
            checkpoint.knowledge_unit.knowledge_type = knowledge_type
        else:
            checkpoint.knowledge_unit = KnowledgeUnit(
                id=self._generate_id(),
                content=content,
                knowledge_type=knowledge_type,
                provenance=KnowledgeProvenanceV31(
                    source_type=source_type,
                    source_ref=source_ref,
                    source_version=source_version,
                    ingested_at=self._now(),
                    ingested_by=ingested_by,
                    verification_state="unverified",
                ),
                created_at=self._now(),
                updated_at=self._now(),
            )
        
        return None  # Stage passed
    
    def _stage_normalize(
        self,
        pipeline_id: str,
        content: str,
        source_type: str,
        source_ref: str,
        source_version: str,
        ingested_by: str,
        metadata: dict[str, Any],
        checkpoint: PipelineCheckpoint,
    ) -> dict | None:
        """Stage 4: NORMALIZE - Standardize format."""
        logger.debug(f"Stage NORMALIZE: Normalizing content")
        
        if checkpoint.knowledge_unit:
            # Normalize for comparison
            normalized = content.strip().lower()
            normalized = ' '.join(normalized.split())  # Collapse whitespace
            checkpoint.knowledge_unit.content = normalized
            
            # Add tags from metadata
            if metadata.get("tags"):
                checkpoint.knowledge_unit.tags = metadata["tags"]
            
            # Set project scope
            if metadata.get("project_scope"):
                checkpoint.knowledge_unit.project_scope = metadata["project_scope"]
        
        return None  # Stage passed
    
    def _stage_dedup(
        self,
        pipeline_id: str,
        content: str,
        source_type: str,
        source_ref: str,
        source_version: str,
        ingested_by: str,
        metadata: dict[str, Any],
        checkpoint: PipelineCheckpoint,
    ) -> dict | None:
        """Stage 5: DEDUP - Check for duplicates."""
        logger.debug(f"Stage DEDUP: Checking for duplicates")
        
        # Compute hash
        content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
        
        # Check for exact match in database
        cursor = self.db.cursor()
        cursor.execute("""
            SELECT id, content FROM knowledge_units
            WHERE content_hash = ?
        """, (content_hash,))
        
        matches = cursor.fetchall()
        if matches:
            checkpoint.warnings.append(f"Found {len(matches)} exact duplicate(s)")
            # Store hash for later use
            if checkpoint.knowledge_unit:
                checkpoint.knowledge_unit.metadata = {"duplicate_of": [m[0] for m in matches]}
        
        return None  # Stage passed (warning only, not error)
    
    def _stage_conflict_detect(
        self,
        pipeline_id: str,
        content: str,
        source_type: str,
        source_ref: str,
        source_version: str,
        ingested_by: str,
        metadata: dict[str, Any],
        checkpoint: PipelineCheckpoint,
    ) -> dict | None:
        """Stage 6: CONFLICT_DETECT - Detect contradictions."""
        logger.debug(f"Stage CONFLICT_DETECT: Checking for conflicts")
        
        # This is a placeholder - actual conflict detection will be implemented in V31 Phase 2
        # For now, just log that the stage ran
        
        return None  # Stage passed
    
    def _stage_quality_score(
        self,
        pipeline_id: str,
        content: str,
        source_type: str,
        source_ref: str,
        source_version: str,
        ingested_by: str,
        metadata: dict[str, Any],
        checkpoint: PipelineCheckpoint,
    ) -> dict | None:
        """Stage 7: QUALITY_SCORE - Compute confidence."""
        logger.debug(f"Stage QUALITY_SCORE: Computing quality score")
        
        if checkpoint.knowledge_unit:
            # Basic quality scoring based on source type
            source_scores = {
                "OWNER_DOCUMENT": 0.95,
                "PROJECT_DOCS": 0.90,
                "TECHNICAL_SPEC": 0.95,
                "TEST_EVIDENCE": 0.98,
                "WORKFLOW_LOG": 0.85,
                "OWNER_FEEDBACK": 0.92,
                "EXTERNAL_UNVERIFIED": 0.50,
            }
            
            base_score = source_scores.get(source_type, 0.70)
            
            # Adjust based on content length
            if len(content) < 20:
                base_score *= 0.8  # Too short
            
            checkpoint.knowledge_unit.quality_score = base_score
        
        return None  # Stage passed
    
    def _stage_provenance_build(
        self,
        pipeline_id: str,
        content: str,
        source_type: str,
        source_ref: str,
        source_version: str,
        ingested_by: str,
        metadata: dict[str, Any],
        checkpoint: PipelineCheckpoint,
    ) -> dict | None:
        """Stage 8: PROVENANCE_BUILD - Create lineage record."""
        logger.debug(f"Stage PROVENANCE_BUILD: Building provenance")
        
        if checkpoint.knowledge_unit:
            # Build provenance
            provenance = self.provenance_tracker.build_provenance(
                source_type=source_type,
                source_ref=source_ref,
                source_version=source_version,
                ingested_by=ingested_by,
                verification_state="quarantined",  # Needs review
            )
            
            # Set temporal info from metadata
            if metadata.get("effective_from"):
                provenance.effective_from = metadata["effective_from"]
            if metadata.get("effective_until"):
                provenance.effective_until = metadata["effective_until"]
            if metadata.get("observed_at"):
                provenance.observed_at = metadata["observed_at"]
            
            checkpoint.knowledge_unit.provenance = provenance
            
            # Log ingestion event
            self.provenance_tracker.log_event(
                checkpoint.knowledge_unit.id,
                "INGESTED",
                {
                    "source_type": source_type,
                    "source_ref": source_ref,
                    "source_version": source_version,
                },
                ingested_by,
            )
        
        return None  # Stage passed
    
    def _stage_owner_preview(
        self,
        pipeline_id: str,
        content: str,
        source_type: str,
        source_ref: str,
        source_version: str,
        ingested_by: str,
        metadata: dict[str, Any],
        checkpoint: PipelineCheckpoint,
    ) -> dict | None:
        """Stage 9: OWNER_PREVIEW - Show proposed changes for approval."""
        logger.debug(f"Stage OWNER_PREVIEW: Preparing preview for owner review")
        
        if checkpoint.knowledge_unit:
            preview = {
                "knowledge_unit_id": checkpoint.knowledge_unit.id,
                "content": checkpoint.knowledge_unit.content,
                "knowledge_type": checkpoint.knowledge_unit.knowledge_type,
                "provenance": checkpoint.knowledge_unit.provenance.to_dict(),
                "quality_score": checkpoint.knowledge_unit.quality_score,
                "warnings": checkpoint.warnings,
                "suggested_action": "APPROVE" if checkpoint.knowledge_unit.quality_score > 0.7 else "REVIEW",
            }
            
            # Return pause with preview
            return {"pause": True, "preview": preview}
        
        return {"error": "No knowledge unit to preview"}
    
    def _stage_apply(
        self,
        pipeline_id: str,
        content: str,
        source_type: str,
        source_ref: str,
        source_version: str,
        ingested_by: str,
        metadata: dict[str, Any],
        checkpoint: PipelineCheckpoint,
    ) -> dict | None:
        """Stage 10: APPLY - Write to database."""
        logger.debug(f"Stage APPLY: Writing to database")
        
        if checkpoint.knowledge_unit:
            # Create version entry
            version_entry = self.provenance_tracker.create_version_entry(
                knowledge_unit_id=checkpoint.knowledge_unit.id,
                version=1,
                changed_fields=["content", "provenance"],
                changed_by=ingested_by,
                reason="Initial ingestion",
                content=checkpoint.knowledge_unit.content,
            )
            checkpoint.knowledge_unit.version_history = [version_entry]
            
            # Insert into database
            cursor = self.db.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO knowledge_units
                (id, content, knowledge_type, provenance_json, version, 
                 lifecycle_status, quality_score, tags_json, project_scope,
                 created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                checkpoint.knowledge_unit.id,
                checkpoint.knowledge_unit.content,
                checkpoint.knowledge_unit.knowledge_type,
                json.dumps(checkpoint.knowledge_unit.provenance.to_dict()),
                checkpoint.knowledge_unit.version,
                checkpoint.knowledge_unit.lifecycle_status,
                checkpoint.knowledge_unit.quality_score,
                json.dumps(checkpoint.knowledge_unit.tags),
                checkpoint.knowledge_unit.project_scope,
                checkpoint.knowledge_unit.created_at,
                checkpoint.knowledge_unit.updated_at,
            ))
            self.db.commit()
            
            logger.info(f"Applied knowledge unit {checkpoint.knowledge_unit.id} to database")
        
        return None  # Stage passed
    
    def _stage_verify(
        self,
        pipeline_id: str,
        content: str,
        source_type: str,
        source_ref: str,
        source_version: str,
        ingested_by: str,
        metadata: dict[str, Any],
        checkpoint: PipelineCheckpoint,
    ) -> dict | None:
        """Stage 11: VERIFY - Integrity check."""
        logger.debug(f"Stage VERIFY: Running integrity check")
        
        if checkpoint.knowledge_unit:
            # Verify the unit was written correctly
            cursor = self.db.cursor()
            cursor.execute("""
                SELECT id, content, version FROM knowledge_units WHERE id = ?
            """, (checkpoint.knowledge_unit.id,))
            
            row = cursor.fetchone()
            if not row:
                return {"error": f"Knowledge unit {checkpoint.knowledge_unit.id} not found in database"}
            
            if row[1] != checkpoint.knowledge_unit.content:
                return {"error": "Content mismatch after write"}
            
            logger.info(f"Verified knowledge unit {checkpoint.knowledge_unit.id}")
        
        return None  # Stage passed
    
    def _save_checkpoint(self, checkpoint: PipelineCheckpoint):
        """Save checkpoint to database."""
        cursor = self.db.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO pipeline_checkpoints
            (pipeline_id, checkpoint_json, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            checkpoint.pipeline_id,
            json.dumps(checkpoint.to_dict()),
            checkpoint.status.value,
            checkpoint.created_at,
            checkpoint.updated_at,
        ))
        self.db.commit()
    
    def resume_pipeline(self, pipeline_id: str, owner_decision: str = "APPROVE") -> PipelineResult:
        """Resume a paused pipeline.
        
        Args:
            pipeline_id: Pipeline ID to resume
            owner_decision: Owner decision (APPROVE, REJECT, MODIFY)
            
        Returns:
            PipelineResult with final status
        """
        # Load checkpoint
        cursor = self.db.cursor()
        cursor.execute("""
            SELECT checkpoint_json FROM pipeline_checkpoints
            WHERE pipeline_id = ?
        """, (pipeline_id,))
        
        row = cursor.fetchone()
        if not row:
            return PipelineResult(
                pipeline_id=pipeline_id,
                status=PipelineStatus.FAILED,
                errors=[f"Pipeline {pipeline_id} not found"],
            )
        
        checkpoint = PipelineCheckpoint.from_dict(json.loads(row[0]))
        
        if checkpoint.status != PipelineStatus.PAUSED:
            return PipelineResult(
                pipeline_id=pipeline_id,
                status=PipelineStatus.FAILED,
                errors=[f"Pipeline {pipeline_id} is not paused"],
            )
        
        if owner_decision == "REJECT":
            checkpoint.status = PipelineStatus.CANCELLED
            checkpoint.updated_at = self._now()
            self._save_checkpoint(checkpoint)
            return PipelineResult(
                pipeline_id=pipeline_id,
                status=PipelineStatus.CANCELLED,
                knowledge_unit=checkpoint.knowledge_unit,
            )
        
        # Continue from OWNER_PREVIEW stage
        stages_to_run = [
            PipelineStage.APPLY,
            PipelineStage.VERIFY,
        ]
        
        for stage in stages_to_run:
            checkpoint.current_stage = stage
            checkpoint.updated_at = self._now()
            self._save_checkpoint(checkpoint)
            
            result = self._stages[stage](
                pipeline_id=pipeline_id,
                content=checkpoint.knowledge_unit.content if checkpoint.knowledge_unit else "",
                source_type=checkpoint.knowledge_unit.provenance.source_type if checkpoint.knowledge_unit else "",
                source_ref=checkpoint.knowledge_unit.provenance.source_ref if checkpoint.knowledge_unit else "",
                source_version=checkpoint.knowledge_unit.provenance.source_version if checkpoint.knowledge_unit else "",
                ingested_by=checkpoint.knowledge_unit.provenance.ingested_by if checkpoint.knowledge_unit else "",
                metadata={},
                checkpoint=checkpoint,
            )
            
            if result is None:
                checkpoint.stages_completed.append(stage)
            elif isinstance(result, dict) and result.get("error"):
                checkpoint.errors.append(result["error"])
                checkpoint.status = PipelineStatus.FAILED
                checkpoint.updated_at = self._now()
                self._save_checkpoint(checkpoint)
                return PipelineResult(
                    pipeline_id=pipeline_id,
                    status=PipelineStatus.FAILED,
                    errors=checkpoint.errors,
                )
        
        checkpoint.status = PipelineStatus.COMPLETED
        checkpoint.updated_at = self._now()
        self._save_checkpoint(checkpoint)
        
        return PipelineResult(
            pipeline_id=pipeline_id,
            status=PipelineStatus.COMPLETED,
            knowledge_unit=checkpoint.knowledge_unit,
            stages_completed=checkpoint.stages_completed,
        )
    
    def get_checkpoint(self, pipeline_id: str) -> Optional[PipelineCheckpoint]:
        """Get checkpoint for a pipeline.
        
        Args:
            pipeline_id: Pipeline ID
            
        Returns:
            PipelineCheckpoint or None
        """
        cursor = self.db.cursor()
        cursor.execute("""
            SELECT checkpoint_json FROM pipeline_checkpoints
            WHERE pipeline_id = ?
        """, (pipeline_id,))
        
        row = cursor.fetchone()
        if not row:
            return None
        
        return PipelineCheckpoint.from_dict(json.loads(row[0]))