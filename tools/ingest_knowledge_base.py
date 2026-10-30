#!/usr/bin/env python3
"""
V38 Knowledge Base Ingestion Script

Usage:
    python tools/ingest_knowledge_base.py --source "E:/AI/QUAN AI BRAIN/kho_tai_lieu"
    python tools/ingest_knowledge_base.py --source "E:/AI/QUAN AI BRAIN/kho_tai_lieu" --industry engineering
    python tools/ingest_knowledge_base.py --status
"""

import sys
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from quan_ai_brain.knowledge.knowledge_ingestion import KnowledgeIngestionPipeline
from quan_ai_brain.knowledge.knowledge_query import KnowledgeQueryEngine


def main():
    parser = argparse.ArgumentParser(description="Ingest knowledge base into vector database")
    parser.add_argument(
        "--source",
        type=str,
        default="E:/AI/QUAN AI BRAIN/kho_tai_lieu",
        help="Source directory containing knowledge files"
    )
    parser.add_argument(
        "--industry",
        type=str,
        choices=["engineering", "ai", "telecom", "business", "training", "general"],
        help="Filter by industry (optional)"
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show knowledge base statistics"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Number of parallel workers (default: 4)"
    )
    
    args = parser.parse_args()
    
    source_path = Path(args.source)
    
    if not source_path.exists():
        print(f"❌ Error: Source path does not exist: {source_path}")
        sys.exit(1)
    
    # Initialize query engine
    print("Initializing knowledge base...")
    query_engine = KnowledgeQueryEngine()
    
    if args.status:
        # Show statistics
        stats = query_engine.get_statistics()
        print("\n" + "="*70)
        print("📊 KNOWLEDGE BASE STATISTICS")
        print("="*70)
        print(f"Total documents: {stats['total_documents']}")
        print(f"Total chunks: {stats['total_chunks']}")
        print("\nBy Industry:")
        for ind, count in sorted(stats['industries'].items()):
            print(f"  • {ind}: {count}")
        print("\nBy Category:")
        for cat, count in sorted(stats['categories'].items()):
            print(f"  • {cat}: {count}")
        print("\nBy Subcategory:")
        for subcat, count in sorted(stats['subcategories'].items()):
            print(f"  • {subcat}: {count}")
        print("\nBy File Type:")
        for ftype, count in sorted(stats['file_types'].items()):
            print(f"  • {ftype}: {count}")
        print("="*70)
        return
    
    # Run ingestion
    pipeline = KnowledgeIngestionPipeline(source_path, query_engine)
    stats = pipeline.ingest(max_workers=args.workers)
    
    print("\n✅ Ingestion complete!")
    print(f"   Processed: {stats['processed']} files")
    print(f"   Created: {stats['total_chunks']} chunks")
    print(f"   Failed: {stats['failed']} files")
    
    # Show updated statistics
    updated_stats = query_engine.get_statistics()
    print(f"\n📊 Total in database: {updated_stats['total_chunks']} chunks from {updated_stats['total_documents']} documents")


if __name__ == "__main__":
    main()