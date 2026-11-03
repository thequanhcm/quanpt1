# V37.1 Knowledge Dashboard - Integration Guide

## Overview
Knowledge Dashboard V37.1 provides a visual interface for managing 3 knowledge sources:
1. **USER_PROVIDED** - "Anh dạy" (owner-provided knowledge)
2. **QUARANTINE** - "Chờ duyệt" (self-researched, pending approval)
3. **APPROVED** - "Đã duyệt" (official approved knowledge)

## Files Created

### Backend API
- `src/quan_ai_brain/dashboard/knowledge_dashboard_api.py` - API endpoints

### Frontend
- `edge_client/static/knowledge_dashboard.js` - JavaScript logic
- `edge_client/templates/knowledge_dashboard_tab.html` - HTML template with CSS

## Integration Steps

### Step 1: Add API Routes to Edge Client

Edit `edge_client/main.py` and add these routes after line ~50:

```python
from quan_ai_brain.dashboard.knowledge_dashboard_api import KnowledgeDashboardAPI

# Initialize API (in the app initialization section)
knowledge_api = KnowledgeDashboardAPI(db_path="data/brain.db")

# Add routes (in the routes section)

@app.route('/api/knowledge/overview', methods=['GET'])
def knowledge_overview():
    return jsonify(knowledge_api.get_overview())

@app.route('/api/knowledge/user-provided', methods=['GET'])
def knowledge_user_provided():
    limit = int(request.args.get('limit', 50))
    offset = int(request.args.get('offset', 0))
    return jsonify(knowledge_api.get_user_provided(limit, offset))

@app.route('/api/knowledge/quarantine', methods=['GET'])
def knowledge_quarantine():
    limit = int(request.args.get('limit', 50))
    offset = int(request.args.get('offset', 0))
    return jsonify(knowledge_api.get_quarantine(limit, offset))

@app.route('/api/knowledge/approved', methods=['GET'])
def knowledge_approved():
    limit = int(request.args.get('limit', 50))
    offset = int(request.args.get('offset', 0))
    return jsonify(knowledge_api.get_approved(limit, offset))

@app.route('/api/knowledge/approve/<int:ku_id>', methods=['POST'])
def knowledge_approve(ku_id):
    data = request.get_json()
    return jsonify(knowledge_api.approve_knowledge(
        ku_id,
        approved_by=data.get('approved_by', 'System'),
        notes=data.get('notes', '')
    ))

@app.route('/api/knowledge/reject/<int:ku_id>', methods=['POST'])
def knowledge_reject(ku_id):
    data = request.get_json()
    return jsonify(knowledge_api.reject_knowledge(
        ku_id,
        rejected_by=data.get('rejected_by', 'System'),
        reason=data.get('reason', '')
    ))

@app.route('/api/knowledge/growth-chart', methods=['GET'])
def knowledge_growth():
    days = int(request.args.get('days', 90))
    return jsonify(knowledge_api.get_growth_chart(days))

@app.route('/api/knowledge/weekly-report', methods=['GET'])
def knowledge_weekly_report():
    return jsonify(knowledge_api.get_weekly_report())
```

### Step 2: Add Tab to Dashboard HTML

Edit `edge_client/main.py` or the main dashboard HTML template and add:

**In the navigation tabs section:**
```html
<button class="nav-tab" data-tab="tab-knowledge" onclick="switchTab('tab-knowledge')">
    📚 Kiến Thức
</button>
```

**In the tab contents section (after other tabs):**
```html
<!-- Include the knowledge dashboard tab content -->
{% include 'templates/knowledge_dashboard_tab.html' %}
```

**Or copy the content from `templates/knowledge_dashboard_tab.html` directly.**

### Step 3: Load JavaScript

Add to the dashboard HTML `<head>` or at the end of `<body>`:

```html
<script src="/static/knowledge_dashboard.js"></script>
```

And call `loadKnowledgeDashboard()` when the tab is activated:

```javascript
if (tabId === 'tab-knowledge' && window.loadKnowledgeDashboard) {
    window.loadKnowledgeDashboard();
}
```

### Step 4: Restart Edge Client

```bash
# Stop current process
# Then restart:
python -m edge_client.main
```

## Features

### Overview Metrics
- Total knowledge count
- USER_PROVIDED count
- Pending approval count
- Approved this week/month

### Tab "Anh Dạy"
- List all USER_PROVIDED knowledge
- Shows source, date, type
- Read-only view

### Tab "Chờ Duyệt"
- List quarantine (PENDING_REVIEW) knowledge
- Shows references and sources
- **Approve/Reject buttons inline**
- No need to go to separate consultation forms

### Tab "Đã Duyệt"
- List VERIFIED knowledge
- Shows approval date and approver
- Historical record

### Growth Chart
- 90-day knowledge growth visualization
- Bar chart showing daily additions
- Helps track learning speed

### Weekly Report (DIR-04)
- Auto-generated weekly summary
- New knowledge by type
- Approved count
- Top sources

## Testing

### Test API Endpoints

```bash
# Overview
curl http://127.0.0.1:8766/api/knowledge/overview

# User-provided
curl http://127.0.0.1:8766/api/knowledge/user-provided?limit=10

# Quarantine
curl http://127.0.0.1:8766/api/knowledge/quarantine

# Approve
curl -X POST http://127.0.0.1:8766/api/knowledge/approve/123 \
  -H "Content-Type: application/json" \
  -d '{"approved_by": "Quanpt1", "notes": "Đã kiểm tra"}'

# Growth chart
curl http://127.0.0.1:8766/api/knowledge/growth-chart?days=30
```

### Test UI

1. Open `http://127.0.0.1:8766/`
2. Click "📚 Kiến Thức" tab
3. Verify metrics display correctly
4. Switch between tabs
5. Test approve/reject buttons
6. Check growth chart renders
7. View weekly report

## Database Schema Requirements

The dashboard assumes `knowledge_units` table has:
- `id` (INTEGER PRIMARY KEY)
- `content` (TEXT)
- `knowledge_type` (TEXT)
- `provenance_json` (TEXT) - JSON with source_type, source_ref
- `verification_state` (TEXT) - PENDING_REVIEW, VERIFIED, REJECTED
- `verified_at` (TEXT) - ISO timestamp
- `verified_by` (TEXT)
- `review_notes` (TEXT)
- `created_at` (TEXT)
- `updated_at` (TEXT)

## Next Steps

After integration:
1. ✅ Test all API endpoints
2. ✅ Verify UI renders correctly
3. ✅ Test approve/reject workflow
4. ✅ Check growth chart with real data
5. ✅ Generate weekly report
6. ✅ Get owner approval for deployment

## Owner Decision Required

The dashboard includes a section "Cần anh quyết" for priority learning topics.

**Question for Quanpt1:**
> Anh muốn em tự đề xuất nội dung học theo chủ đề nào ưu tiên?
> 
> Ví dụ: Tài liệu đào tạo AI 5 module anh nhắc trước đó?
> 
> Các lựa chọn:
> 1. **AI Module 1-5** - Tài liệu đào tạo AI cơ bản
> 2. **Technical Documentation** - Tài liệu kỹ thuật hệ thống
> 3. **Business Processes** - Quy trình nghiệp vụ
> 4. **Industry Best Practices** - Thực tiễn tốt nhất ngành
> 5. **Custom Topics** - Anh đề xuất chủ đề cụ thể

Please specify priority topics for self-learning recommendations.

---

**Status:** Ready for integration  
**Files:** 3 created (API, JS, HTML template)  
**Next:** Integrate into edge_client/main.py and test