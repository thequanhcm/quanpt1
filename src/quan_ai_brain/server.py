"""QUAN AI BRAIN - Main API Server (V38).

Flask server providing:
- /api/chat - Main chat endpoint
- /api/knowledge/* - Knowledge base endpoints (V38)
- /api/health - Health check
- /api/memory/* - Memory endpoints
- /api/tasks/* - Task management

Run:
    python -m quan_ai_brain.server
    or
    python tools/server.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from flask import Flask, request, jsonify
from flask_cors import CORS

# Add project root to path (handle both module and script execution)
if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent.parent.parent
else:
    project_root = Path(__file__).parent.parent.parent

if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Ensure src directory is in path
src_dir = project_root / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from quan_ai_brain.llm.llm_service import LLMService
from quan_ai_brain.memory.memory_service import MemoryService
from quan_ai_brain.knowledge.knowledge_query import KnowledgeQueryEngine

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Initialize services
llm_service = LLMService()
memory_service = MemoryService()
knowledge_engine = KnowledgeQueryEngine()

# Register knowledge base routes
from quan_ai_brain.api.knowledge_routes import knowledge_bp
app.register_blueprint(knowledge_bp)


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'service': 'QUAN AI BRAIN',
        'version': 'V38',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'components': {
            'llm': 'ready',
            'memory': 'ready',
            'knowledge_base': 'ready' if knowledge_engine.collection.count() > 0 else 'empty'
        }
    })


@app.route('/api/chat', methods=['POST'])
def chat():
    """Main chat endpoint.
    
    Request JSON:
    {
        "query": "User's question or message",
        "session_id": "Optional session ID for context",
        "model": "Optional model name (default: zai-org/GLM-5.3-Flash)",
        "reasoning_effort": "low|medium|high (default: low)"
    }
    
    Response JSON:
    {
        "answer": "AI's response",
        "session_id": "Session ID used",
        "timestamp": "ISO timestamp"
    }
    """
    try:
        data = request.get_json() or {}
        query = data.get('query', '').strip()
        session_id = data.get('session_id', 'default')
        model = data.get('model', 'zai-org/GLM-5.3-Flash')
        reasoning_effort = data.get('reasoning_effort', 'low')
        
        if not query:
            return jsonify({
                'error': 'Query is required',
                'answer': 'Xin vui lòng nhập câu hỏi của anh.'
            }), 400
        
        # Check if query is about knowledge base
        knowledge_keywords = ['tìm trong kho', 'tra cứu', 'tài liệu', 'kiến thức', 
                            'kho dữ liệu', 'document', 'knowledge base']
        is_knowledge_query = any(kw in query.lower() for kw in knowledge_keywords)
        
        if is_knowledge_query:
            # Use knowledge base to answer
            answer = knowledge_engine.answer_question(query, top_k=5)
        else:
            # Use LLM with memory context
            # Get relevant memories
            memories = memory_service.search_memories(query, top_k=3)
            
            # Build context
            context = ""
            if memories:
                context = "Dựa trên trí nhớ:\n"
                for i, mem in enumerate(memories, 1):
                    context += f"{i}. {mem.get('content', '')[:200]}\n"
            
            # Build prompt
            prompt = f"""Anh là TONY - Trợ lý số thông minh.
            
Câu hỏi của chủ nhân: {query}

{context if context else ""}Hãy trả lời ngắn gọn, chính xác và hữu ích."""
            
            # Call LLM
            response = llm_service.generate(
                prompt=prompt,
                model=model,
                reasoning_effort=reasoning_effort,
                max_tokens=1000
            )
            
            answer = response.get('answer', 'Xin lỗi, em không thể trả lời câu hỏi này.')
        
        return jsonify({
            'answer': answer,
            'session_id': session_id,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'source': 'knowledge_base' if is_knowledge_query else 'llm'
        })
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': str(e),
            'answer': f'⚠️ Lỗi hệ thống: {str(e)}'
        }), 500


@app.route('/api/memory/search', methods=['GET'])
def search_memory():
    """Search memory service."""
    try:
        query = request.args.get('q', '')
        top_k = int(request.args.get('top_k', 5))
        
        if not query:
            return jsonify({'error': 'Query required'}), 400
        
        results = memory_service.search_memories(query, top_k=top_k)
        
        return jsonify({
            'success': True,
            'query': query,
            'results': results,
            'count': len(results)
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/memory/add', methods=['POST'])
def add_memory():
    """Add new memory."""
    try:
        data = request.get_json() or {}
        content = data.get('content', '')
        memory_type = data.get('memory_type', 'semantic')
        
        if not content:
            return jsonify({'error': 'Content required'}), 400
        
        result = memory_service.add_memory(content, memory_type)
        
        return jsonify({
            'success': True,
            'memory_id': result.get('id'),
            'message': 'Memory added successfully'
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({
        'error': 'Endpoint not found',
        'message': 'URL không tồn tại. Vui lòng kiểm tra lại.'
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    return jsonify({
        'error': 'Internal server error',
        'message': 'Có lỗi xảy ra trong hệ thống.'
    }), 500


def main():
    """Run the server."""
    import argparse
    
    parser = argparse.ArgumentParser(description='QUAN AI BRAIN API Server')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Host to bind')
    parser.add_argument('--port', type=int, default=8765, help='Port to listen')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    
    args = parser.parse_args()
    
    print("\n" + "="*70)
    print("🚀 QUAN AI BRAIN - API Server V38")
    print("="*70)
    print(f"Host: {args.host}")
    print(f"Port: {args.port}")
    print(f"Debug: {args.debug}")
    print("="*70)
    print("\nEndpoints:")
    print("  • GET  /api/health          - Health check")
    print("  • POST /api/chat            - Main chat endpoint")
    print("  • GET  /api/memory/search   - Search memory")
    print("  • POST /api/memory/add      - Add memory")
    print("  • GET  /api/knowledge/search    - Search knowledge base")
    print("  • GET  /api/knowledge/question  - Answer question")
    print("  • GET  /api/knowledge/stats     - Get statistics")
    print("  • POST /api/knowledge/ingest    - Ingest knowledge")
    print("="*70)
    print("\n🌐 Server starting...")
    print("="*70 + "\n")
    
    app.run(
        host=args.host,
        port=args.port,
        debug=args.debug,
        threaded=True
    )


if __name__ == '__main__':
    main()