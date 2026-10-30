"""V38 Knowledge Base API Endpoints.

Endpoints:
- POST /api/knowledge/ingest - Ingest knowledge base
- GET /api/knowledge/search - Search with filters
- GET /api/knowledge/question - Answer question
- GET /api/knowledge/stats - Get statistics
- GET /api/knowledge/industries - List industries
- GET /api/knowledge/categories - List categories
"""

from flask import Blueprint, request, jsonify
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from quan_ai_brain.knowledge.knowledge_query import KnowledgeQueryEngine
from quan_ai_brain.knowledge.knowledge_ingestion import KnowledgeIngestionPipeline

# Initialize query engine
query_engine = KnowledgeQueryEngine()

knowledge_bp = Blueprint('knowledge', __name__, url_prefix='/api/knowledge')


@knowledge_bp.route('/ingest', methods=['POST'])
def ingest_knowledge():
    """Ingest knowledge base from source directory."""
    try:
        data = request.get_json() or {}
        source_path = Path(data.get('source', 'E:/AI/QUAN AI BRAIN/kho_tai_lieu'))
        max_workers = data.get('workers', 4)
        
        if not source_path.exists():
            return jsonify({
                'success': False,
                'error': f'Source path does not exist: {source_path}'
            }), 400
        
        # Run ingestion
        pipeline = KnowledgeIngestionPipeline(source_path, query_engine)
        stats = pipeline.ingest(max_workers=max_workers)
        
        return jsonify({
            'success': True,
            'message': 'Ingestion complete',
            'stats': stats
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@knowledge_bp.route('/search', methods=['GET'])
def search_knowledge():
    """Search knowledge base with filters."""
    try:
        query = request.args.get('q', '')
        industry = request.args.get('industry', None)
        category = request.args.get('category', None)
        subcategory = request.args.get('subcategory', None)
        file_types = request.args.get('file_types', None)
        min_score = float(request.args.get('min_score', 0.5))
        top_k = int(request.args.get('top_k', 10))
        
        if not query:
            return jsonify({
                'success': False,
                'error': 'Query parameter "q" is required'
            }), 400
        
        # Parse file_types
        if file_types:
            file_types = file_types.split(',')
        
        # Search
        results = query_engine.search(
            query=query,
            industry=industry,
            category=category,
            subcategory=subcategory,
            file_types=file_types,
            min_score=min_score,
            top_k=top_k
        )
        
        return jsonify({
            'success': True,
            'query': query,
            'filters': {
                'industry': industry,
                'category': category,
                'subcategory': subcategory,
                'file_types': file_types
            },
            'results': [r.to_dict() for r in results],
            'count': len(results)
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@knowledge_bp.route('/question', methods=['GET'])
def answer_question():
    """Answer question using knowledge base."""
    try:
        question = request.args.get('question', '')
        industry = request.args.get('industry', None)
        category = request.args.get('category', None)
        top_k = int(request.args.get('top_k', 5))
        
        if not question:
            return jsonify({
                'success': False,
                'error': 'Question parameter is required'
            }), 400
        
        # Answer
        answer = query_engine.answer_question(
            question=question,
            industry=industry,
            category=category,
            top_k=top_k
        )
        
        return jsonify({
            'success': True,
            'question': question,
            'answer': answer
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@knowledge_bp.route('/stats', methods=['GET'])
def get_statistics():
    """Get knowledge base statistics."""
    try:
        stats = query_engine.get_statistics()
        
        return jsonify({
            'success': True,
            'stats': stats
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@knowledge_bp.route('/industries', methods=['GET'])
def list_industries():
    """List all industries."""
    try:
        industries = query_engine.list_industries()
        
        return jsonify({
            'success': True,
            'industries': industries
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@knowledge_bp.route('/categories', methods=['GET'])
def list_categories():
    """List all categories."""
    try:
        categories = query_engine.list_categories()
        
        return jsonify({
            'success': True,
            'categories': categories
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500