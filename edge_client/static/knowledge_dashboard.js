/**
 * Knowledge Dashboard V37.1 - Frontend for Edge Client
 * 
 * Features:
 * - Overview metrics
 * - Tab "Anh dạy" - USER_PROVIDED knowledge
 * - Tab "Chờ duyệt" - Quarantine with approve/reject
 * - Tab "Đã duyệt" - Approved knowledge
 * - Growth chart
 * - Weekly report
 */

// ==================== KNOWLEDGE DASHBOARD STATE ====================

let knowledgeState = {
    overview: null,
    userProvided: [],
    quarantine: [],
    approved: [],
    growthData: [],
    weeklyReport: null,
    loading: false
};

// ==================== API CALLS ====================

async function fetchKnowledgeOverview() {
    try {
        const response = await fetch('/api/knowledge/overview');
        const data = await response.json();
        knowledgeState.overview = data;
        updateOverviewUI(data);
    } catch (error) {
        console.error('Failed to fetch overview:', error);
        showError('Không thể tải tổng quan kiến thức');
    }
}

async function fetchUserProvided(limit = 50, offset = 0) {
    try {
        const response = await fetch(`/api/knowledge/user-provided?limit=${limit}&offset=${offset}`);
        const data = await response.json();
        knowledgeState.userProvided = data;
        renderUserProvidedTable(data);
    } catch (error) {
        console.error('Failed to fetch user-provided:', error);
        showError('Không thể tải kiến thức "Anh dạy"');
    }
}

async function fetchQuarantine(limit = 50, offset = 0) {
    try {
        const response = await fetch(`/api/knowledge/quarantine?limit=${limit}&offset=${offset}`);
        const data = await response.json();
        knowledgeState.quarantine = data;
        renderQuarantineTable(data);
    } catch (error) {
        console.error('Failed to fetch quarantine:', error);
        showError('Không thể tải kiến thức chờ duyệt');
    }
}

async function fetchApproved(limit = 50, offset = 0) {
    try {
        const response = await fetch(`/api/knowledge/approved?limit=${limit}&offset=${offset}`);
        const data = await response.json();
        knowledgeState.approved = data;
        renderApprovedTable(data);
    } catch (error) {
        console.error('Failed to fetch approved:', error);
        showError('Không thể tải kiến thức đã duyệt');
    }
}

async function fetchGrowthChart(days = 90) {
    try {
        const response = await fetch(`/api/knowledge/growth-chart?days=${days}`);
        const data = await response.json();
        knowledgeState.growthData = data;
        renderGrowthChart(data);
    } catch (error) {
        console.error('Failed to fetch growth chart:', error);
        console.warn('Growth chart not available yet');
    }
}

async function fetchWeeklyReport() {
    try {
        const response = await fetch('/api/knowledge/weekly-report');
        const data = await response.json();
        knowledgeState.weeklyReport = data;
        renderWeeklyReport(data);
    } catch (error) {
        console.error('Failed to fetch weekly report:', error);
        showError('Không thể tải báo cáo tuần');
    }
}

async function approveKnowledge(kuId, notes = '') {
    if (!confirm('Duyệt mục kiến thức này?')) return;
    
    try {
        const response = await fetch(`/api/knowledge/approve/${kuId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                approved_by: 'Quanpt1',
                notes: notes
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            showSuccess('Đã duyệt kiến thức');
            // Refresh quarantine list
            await fetchQuarantine();
            await fetchKnowledgeOverview();
        } else {
            showError(result.error || 'Không thể duyệt kiến thức');
        }
    } catch (error) {
        console.error('Failed to approve:', error);
        showError('Lỗi khi duyệt kiến thức');
    }
}

async function rejectKnowledge(kuId, reason = '') {
    const reasonInput = prompt('Lý do từ chối:');
    if (!reasonInput) return;
    
    try {
        const response = await fetch(`/api/knowledge/reject/${kuId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                rejected_by: 'Quanpt1',
                reason: reasonInput
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            showSuccess('Đã từ chối kiến thức');
            await fetchQuarantine();
            await fetchKnowledgeOverview();
        } else {
            showError(result.error || 'Không thể từ chối kiến thức');
        }
    } catch (error) {
        console.error('Failed to reject:', error);
        showError('Lỗi khi từ chối kiến thức');
    }
}

// ==================== UI RENDERING ====================

function updateOverviewUI(data) {
    document.getElementById('overview-total').textContent = data.total_knowledge || 0;
    document.getElementById('overview-user-provided').textContent = data.user_provided || 0;
    document.getElementById('overview-pending').textContent = data.pending_approval || 0;
    document.getElementById('overview-approved-week').textContent = data.approved_this_week || 0;
    document.getElementById('overview-approved-month').textContent = data.approved_this_month || 0;
    
    // Update notification badge
    const badge = document.getElementById('knowledge-pending-badge');
    if (badge) {
        badge.textContent = data.pending_approval || 0;
        badge.style.display = data.pending_approval > 0 ? 'inline-block' : 'none';
    }
}

function renderUserProvidedTable(data) {
    const container = document.getElementById('user-provided-list');
    if (!container) return;
    
    if (data.length === 0) {
        container.innerHTML = '<div class="empty-state">Chưa có kiến thức từ "Anh dạy"</div>';
        return;
    }
    
    const html = data.map(item => `
        <div class="knowledge-card">
            <div class="knowledge-header">
                <span class="knowledge-type-badge">${item.knowledge_type}</span>
                <span class="knowledge-source">${item.source}</span>
            </div>
            <div class="knowledge-content">${escapeHtml(item.content)}</div>
            <div class="knowledge-meta">
                <span>📅 ${formatDate(item.created_at)}</span>
                <span>🔄 ${formatDate(item.updated_at)}</span>
            </div>
        </div>
    `).join('');
    
    container.innerHTML = html;
}

function renderQuarantineTable(data) {
    const container = document.getElementById('quarantine-list');
    if (!container) return;
    
    if (data.length === 0) {
        container.innerHTML = '<div class="empty-state">Không có kiến thức nào chờ duyệt ✅</div>';
        return;
    }
    
    const html = data.map(item => `
        <div class="knowledge-card quarantine-card">
            <div class="knowledge-header">
                <span class="knowledge-type-badge">${item.knowledge_type}</span>
                <span class="knowledge-source">${item.source}</span>
                <span class="status-badge pending">CHỜ DUYỆT</span>
            </div>
            <div class="knowledge-content">${escapeHtml(item.content)}</div>
            ${item.references && item.references.length > 0 ? `
                <div class="knowledge-references">
                    <strong>📚 Tham khảo:</strong>
                    <ul>
                        ${item.references.map(ref => `<li>${escapeHtml(ref)}</li>`).join('')}
                    </ul>
                </div>
            ` : ''}
            <div class="knowledge-meta">
                <span>📅 Thêm: ${formatDate(item.created_at)}</span>
            </div>
            <div class="knowledge-actions">
                <button class="btn btn-approve" onclick="approveKnowledge(${item.id})">
                    ✅ Duyệt
                </button>
                <button class="btn btn-reject" onclick="rejectKnowledge(${item.id})">
                    ❌ Từ chối
                </button>
            </div>
        </div>
    `).join('');
    
    container.innerHTML = html;
}

function renderApprovedTable(data) {
    const container = document.getElementById('approved-list');
    if (!container) return;
    
    if (data.length === 0) {
        container.innerHTML = '<div class="empty-state">Chưa có kiến thức đã duyệt</div>';
        return;
    }
    
    const html = data.map(item => `
        <div class="knowledge-card approved-card">
            <div class="knowledge-header">
                <span class="knowledge-type-badge">${item.knowledge_type}</span>
                <span class="knowledge-source">${item.source}</span>
                <span class="status-badge approved">ĐÃ DUYỆT</span>
            </div>
            <div class="knowledge-content">${escapeHtml(item.content)}</div>
            <div class="knowledge-meta">
                <span>📅 Thêm: ${formatDate(item.created_at)}</span>
                <span>✅ Duyệt: ${formatDate(item.verified_at)} bởi ${item.verified_by || 'System'}</span>
            </div>
        </div>
    `).join('');
    
    container.innerHTML = html;
}

function renderGrowthChart(data) {
    const canvas = document.getElementById('growth-chart-canvas');
    if (!canvas || data.length === 0) return;
    
    // Simple bar chart using Canvas
    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;
    
    // Clear canvas
    ctx.clearRect(0, 0, width, height);
    
    // Chart parameters
    const padding = 40;
    const chartWidth = width - padding * 2;
    const chartHeight = height - padding * 2;
    
    // Find max value
    const maxValue = Math.max(...data.map(d => d.total));
    
    // Draw bars
    const barWidth = Math.max(5, (chartWidth / data.length) - 2);
    
    data.forEach((point, index) => {
        const x = padding + (index * (chartWidth / data.length));
        const barHeight = (point.total / maxValue) * chartHeight;
        const y = height - padding - barHeight;
        
        // Draw bar
        ctx.fillStyle = '#3b82f6';
        ctx.fillRect(x, y, barWidth, barHeight);
        
        // Draw date label (every 5th day)
        if (index % 5 === 0) {
            ctx.fillStyle = '#666';
            ctx.font = '10px Inter';
            ctx.textAlign = 'center';
            ctx.fillText(point.date.substring(5), x + barWidth/2, height - padding + 15);
        }
        
        // Draw value on top
        if (point.total > 0) {
            ctx.fillStyle = '#333';
            ctx.font = '10px Inter';
            ctx.textAlign = 'center';
            ctx.fillText(point.total, x + barWidth/2, y - 5);
        }
    });
    
    // Draw title
    ctx.fillStyle = '#333';
    ctx.font = 'bold 12px Inter';
    ctx.textAlign = 'center';
    ctx.fillText('Tăng trưởng kiến thức (90 ngày)', width/2, 20);
}

function renderWeeklyReport(data) {
    const container = document.getElementById('weekly-report-content');
    if (!container) return;
    
    const html = `
        <div class="weekly-report">
            <h3>📊 Báo Cáo Tuần: ${data.period}</h3>
            
            <div class="report-section">
                <h4>🆕 Kiến Thức Mới</h4>
                <p><strong>Tổng cộng:</strong> ${data.new_knowledge.total}</p>
                <ul>
                    ${Object.entries(data.new_knowledge.by_type).map(([type, count]) => 
                        `<li>${type}: ${count}</li>`
                    ).join('')}
                </ul>
            </div>
            
            <div class="report-section">
                <h4>✅ Đã Duyệt</h4>
                <p><strong>${data.approved}</strong> kiến thức được phê duyệt</p>
            </div>
            
            <div class="report-section">
                <h4>📚 Nguồn Hàng Đầu</h4>
                <ul>
                    ${data.top_sources.map(s => `<li>${s.source}: ${s.count}</li>`).join('')}
                </ul>
            </div>
            
            <div class="report-footer">
                <small>Generated: ${formatDate(data.generated_at)}</small>
            </div>
        </div>
    `;
    
    container.innerHTML = html;
}

// ==================== UTILITY FUNCTIONS ====================

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatDate(isoString) {
    if (!isoString) return 'N/A';
    const date = new Date(isoString);
    return date.toLocaleDateString('vi-VN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function showSuccess(message) {
    // Reuse existing notification system if available
    alert('✅ ' + message);
}

function showError(message) {
    alert('❌ ' + message);
}

// ==================== INITIALIZATION ====================

function loadKnowledgeDashboard() {
    console.log('Loading Knowledge Dashboard...');
    
    // Load all data in parallel
    Promise.all([
        fetchKnowledgeOverview(),
        fetchUserProvided(),
        fetchQuarantine(),
        fetchApproved(),
        fetchGrowthChart(),
        fetchWeeklyReport()
    ]).then(() => {
        console.log('Knowledge Dashboard loaded successfully');
    }).catch(error => {
        console.error('Failed to load Knowledge Dashboard:', error);
    });
}

// Export for global access
window.loadKnowledgeDashboard = loadKnowledgeDashboard;
window.approveKnowledge = approveKnowledge;
window.rejectKnowledge = rejectKnowledge;