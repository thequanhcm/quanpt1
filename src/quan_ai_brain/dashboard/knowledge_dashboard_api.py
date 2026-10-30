"""Knowledge Dashboard API for V37.1 - Knowledge Management & Approval Workflow.

Provides endpoints for:
- GET /api/knowledge/overview - Summary metrics
- GET /api/knowledge/user-provided - List USER_PROVIDED knowledge
- GET /api/knowledge/quarantine - List pending approval knowledge
- GET /api/knowledge/approved - List approved knowledge
- POST /api/knowledge/approve/{id} - Approve knowledge
- POST /api/knowledge/reject/{id} - Reject knowledge
- GET /api/knowledge/growth-chart - Growth data for chart
- GET /api/knowledge/weekly-report - Weekly auto-summary
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
import sqlite3

from quan_ai_brain.memory.models import KnowledgeSource


class KnowledgeDashboardAPI:
    """API for knowledge dashboard V37.1."""
    
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn
    
    def get_overview(self) -> dict[str, Any]:
        """Get knowledge overview metrics."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # Total knowledge
            cursor.execute("SELECT COUNT(*) as total FROM knowledge_units")
            total = cursor.fetchone()["total"]
            
            # User-provided count
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM knowledge_units 
                WHERE provenance_json LIKE '%USER_PROVIDED%'
            """)
            user_provided = cursor.fetchone()["count"]
            
            # Quarantine (pending approval)
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM knowledge_units 
                WHERE verification_state = 'PENDING_REVIEW'
            """)
            pending = cursor.fetchone()["count"]
            
            # Approved this week
            week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM knowledge_units 
                WHERE verification_state = 'VERIFIED' 
                AND verified_at IS NOT NULL
                AND verified_at > ?
            """, (week_ago,))
            approved_week = cursor.fetchone()["count"]
            
            # Approved this month
            month_ago = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM knowledge_units 
                WHERE verification_state = 'VERIFIED' 
                AND verified_at IS NOT NULL
                AND verified_at > ?
            """, (month_ago,))
            approved_month = cursor.fetchone()["count"]
            
            return {
                "total_knowledge": total,
                "user_provided": user_provided,
                "pending_approval": pending,
                "approved_this_week": approved_week,
                "approved_this_month": approved_month,
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
        finally:
            conn.close()
    
    def get_user_provided(self, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
        """Get USER_PROVIDED knowledge units."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT id, content, knowledge_type, provenance_json, 
                       created_at, updated_at
                FROM knowledge_units
                WHERE provenance_json LIKE '%USER_PROVIDED%'
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """, (limit, offset))
            
            rows = cursor.fetchall()
            result = []
            
            for row in rows:
                provenance = json.loads(row["provenance_json"] or "{}")
                result.append({
                    "id": row["id"],
                    "content": row["content"],
                    "knowledge_type": row["knowledge_type"],
                    "source": provenance.get("source_ref", "Unknown"),
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"]
                })
            
            return result
        finally:
            conn.close()
    
    def get_quarantine(self, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
        """Get pending approval (quarantine) knowledge units."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT id, content, knowledge_type, provenance_json, 
                       created_at, updated_at, verification_state
                FROM knowledge_units
                WHERE verification_state = 'PENDING_REVIEW'
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """, (limit, offset))
            
            rows = cursor.fetchall()
            result = []
            
            for row in rows:
                provenance = json.loads(row["provenance_json"] or "{}")
                result.append({
                    "id": row["id"],
                    "content": row["content"],
                    "knowledge_type": row["knowledge_type"],
                    "source": provenance.get("source_ref", "Unknown"),
                    "references": provenance.get("references", []),
                    "created_at": row["created_at"],
                    "verification_state": row["verification_state"]
                })
            
            return result
        finally:
            conn.close()
    
    def get_approved(self, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
        """Get approved knowledge units."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT id, content, knowledge_type, provenance_json, 
                       created_at, updated_at, verified_at, verified_by
                FROM knowledge_units
                WHERE verification_state = 'VERIFIED'
                ORDER BY verified_at DESC
                LIMIT ? OFFSET ?
            """, (limit, offset))
            
            rows = cursor.fetchall()
            result = []
            
            for row in rows:
                provenance = json.loads(row["provenance_json"] or "{}")
                result.append({
                    "id": row["id"],
                    "content": row["content"],
                    "knowledge_type": row["knowledge_type"],
                    "source": provenance.get("source_ref", "Unknown"),
                    "verified_at": row["verified_at"],
                    "verified_by": row["verified_by"],
                    "created_at": row["created_at"]
                })
            
            return result
        finally:
            conn.close()
    
    def approve_knowledge(self, ku_id: int, approved_by: str, notes: str = "") -> dict[str, Any]:
        """Approve a knowledge unit."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            now = datetime.now(timezone.utc).isoformat()
            
            # Update verification state
            cursor.execute("""
                UPDATE knowledge_units
                SET verification_state = 'VERIFIED',
                    verified_at = ?,
                    verified_by = ?,
                    review_notes = ?,
                    updated_at = ?
                WHERE id = ?
            """, (now, approved_by, notes, now, ku_id))
            
            if cursor.rowcount == 0:
                return {"success": False, "error": "Knowledge unit not found"}
            
            conn.commit()
            return {
                "success": True,
                "message": f"Knowledge unit {ku_id} approved",
                "approved_at": now,
                "approved_by": approved_by
            }
        except Exception as e:
            conn.rollback()
            return {"success": False, "error": str(e)}
        finally:
            conn.close()
    
    def reject_knowledge(self, ku_id: int, rejected_by: str, reason: str = "") -> dict[str, Any]:
        """Reject a knowledge unit."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            now = datetime.now(timezone.utc).isoformat()
            
            # Update verification state
            cursor.execute("""
                UPDATE knowledge_units
                SET verification_state = 'REJECTED',
                    verified_at = ?,
                    verified_by = ?,
                    review_notes = ?,
                    updated_at = ?
                WHERE id = ?
            """, (now, rejected_by, reason, now, ku_id))
            
            if cursor.rowcount == 0:
                return {"success": False, "error": "Knowledge unit not found"}
            
            conn.commit()
            return {
                "success": True,
                "message": f"Knowledge unit {ku_id} rejected",
                "rejected_at": now,
                "rejected_by": rejected_by
            }
        except Exception as e:
            conn.rollback()
            return {"success": False, "error": str(e)}
        finally:
            conn.close()
    
    def get_growth_chart(self, days: int = 90) -> list[dict[str, Any]]:
        """Get knowledge growth data for chart."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # Get daily counts for each type
            cursor.execute("""
                SELECT 
                    DATE(created_at) as date,
                    knowledge_type,
                    COUNT(*) as count
                FROM knowledge_units
                WHERE created_at > datetime('now', '-' || ? || ' days')
                GROUP BY DATE(created_at), knowledge_type
                ORDER BY date ASC
            """, (days,))
            
            rows = cursor.fetchall()
            
            # Aggregate by date
            daily_data = {}
            for row in rows:
                date = row["date"]
                if date not in daily_data:
                    daily_data[date] = {"date": date, "total": 0, "USER_PROVIDED": 0, "SELF_RESEARCH": 0, "DERIVED": 0}
                
                daily_data[date]["total"] += row["count"]
                kt = row["knowledge_type"]
                if kt in daily_data[date]:
                    daily_data[date][kt] += row["count"]
            
            return list(daily_data.values())
        finally:
            conn.close()
    
    def get_weekly_report(self) -> dict[str, Any]:
        """Generate weekly knowledge report (DIR-04)."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
            
            # New knowledge this week
            cursor.execute("""
                SELECT COUNT(*) as count, knowledge_type
                FROM knowledge_units
                WHERE created_at > ?
                GROUP BY knowledge_type
            """, (week_ago,))
            
            new_by_type = {row["knowledge_type"]: row["count"] for row in cursor.fetchall()}
            
            # Approved this week
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM knowledge_units
                WHERE verification_state = 'VERIFIED'
                AND verified_at > ?
            """, (week_ago,))
            approved_count = cursor.fetchone()["count"]
            
            # Top sources
            cursor.execute("""
                SELECT 
                    json_extract(provenance_json, '$.source_ref') as source,
                    COUNT(*) as count
                FROM knowledge_units
                WHERE created_at > ?
                GROUP BY source
                ORDER BY count DESC
                LIMIT 5
            """, (week_ago,))
            
            top_sources = [{"source": row["source"], "count": row["count"]} for row in cursor.fetchall()]
            
            return {
                "period": f"Last 7 days (until {datetime.now(timezone.utc).strftime('%Y-%m-%d')})",
                "new_knowledge": {
                    "total": sum(new_by_type.values()),
                    "by_type": new_by_type
                },
                "approved": approved_count,
                "top_sources": top_sources,
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
        finally:
            conn.close()