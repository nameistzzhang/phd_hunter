// PhD Hunter Frontend - Light theme, English UI

let professors = [];
let selectedProfessor = null;
let chatLoading = false;

const ACTIVE_PAGE_KEY = 'phd_hunter_active_page';

// Toast notification helper (non-blocking)
function showToast(message, type = 'info', duration = 3000) {
    const toast = document.getElementById('toast');
    const toastMsg = document.getElementById('toast-message');
    if (!toast || !toastMsg) return;

    toastMsg.textContent = message;
    toast.className = 'toast toast-' + type;

    // Clear any existing timeout
    if (toast._timeout) {
        clearTimeout(toast._timeout);
    }

    toast._timeout = setTimeout(() => {
        toast.classList.add('hidden');
    }, duration);
}

// Direct initialization (script is at end of body, DOM is ready)
initPageNavigation();

// Async initialization for data-dependent functions
(async function initData() {
    await loadHuntConfig();      // Restore hunt config from server first
    await loadStats();
    await loadProfessors();
    initFilters();
    // Restore hunt progress if a hunt is still running
    await restoreHuntProgress();
})();

// Stop Hunt button handler
document.getElementById('stop-hunt-btn').addEventListener('click', async () => {
    if (!confirm('Are you sure you want to stop the current hunt?')) {
        return;
    }

    try {
        const response = await fetch('/api/stop-hunt', { method: 'POST' });
        if (!response.ok) {
            const error = await response.json();
            showToast('Failed to stop: ' + (error.message || 'Unknown error'), 'error');
            return;
        }

        showToast('Hunting stopped.', 'info');
        // Stop polling and reset UI immediately (no reload needed)
        if (huntPollingInterval) {
            clearInterval(huntPollingInterval);
            huntPollingInterval = null;
        }
        resetHuntButton();
        // Refresh professor list to show newly fetched data
        await loadProfessors();
    } catch (error) {
        showToast('Error stopping hunt: ' + error.message, 'error');
    }
});

// ============ Page Navigation ============

function initPageNavigation() {
    const navButtons = document.querySelectorAll('.nav-button');
    navButtons.forEach(button => {
        button.addEventListener('click', (e) => {
            e.preventDefault();
            const page = button.dataset.page;
            switchPage(page);
        });
    });
}

function switchPage(pageName) {
    console.log('Switching to page:', pageName);

    // Save active page to localStorage so refresh restores it
    localStorage.setItem(ACTIVE_PAGE_KEY, pageName);

    // Update nav button states
    document.querySelectorAll('.nav-button').forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.page === pageName) {
            btn.classList.add('active');
        }
    });

    // Hide all pages (remove active class AND force hide)
    document.querySelectorAll('.page-container').forEach(page => {
        page.classList.remove('active');
        page.style.display = 'none';
    });

    // Show target page (add active class AND force display)
    const targetPage = document.getElementById(`page-${pageName}`);
    if (targetPage) {
        targetPage.classList.add('active');
        targetPage.style.display = 'flex';
        console.log('Showing page:', pageName);
    } else {
        console.error('Page not found:', `page-${pageName}`);
    }
}

function restoreActivePage() {
    const savedPage = localStorage.getItem(ACTIVE_PAGE_KEY);
    if (savedPage) {
        switchPage(savedPage);
    }
}

// ============ End Page Navigation ============

// Load statistics
async function loadStats() {
    try {
        const response = await fetch('/api/stats');
        const stats = await response.json();

        document.getElementById('stats').innerHTML = `
            <div class="stat"><span class="stat-value">${stats.universities}</span> Univ</div>
            <div class="stat"><span class="stat-value">${stats.professors}</span> Profs</div>
            <div class="stat"><span class="stat-value">${stats.papers}</span> Papers</div>
            <div class="stat"><span class="stat-value">${stats.avg_direction_match || '-'}</span> Avg Match</div>
            <div class="stat"><span class="stat-value">${stats.avg_admission_difficulty || '-'}</span> Avg Diff</div>
        `;
    } catch (error) {
        console.error('Failed to load stats:', error);
    }
}

// Load professor list
let allProfessors = [];  // Store all professors for filtering

async function loadProfessors() {
    try {
        const response = await fetch('/api/professors');
        const data = await response.json();

        allProfessors = data.professors;
        professors = data.professors;  // Also update professors for openProfessor
        applyFilters();  // Initial render with current filter settings
    } catch (error) {
        console.error('Failed to load professors:', error);
        document.getElementById('professor-list').innerHTML =
            '<div class="empty-state"><h3>Load failed</h3><p>Check server connection</p></div>';
    }
}

// ============ Filter functionality ============

// Initialize filter dropdowns with options
function initFilters() {
    const areas = new Set();
    const universities = new Set();

    // Collect unique areas and universities from all professors
    allProfessors.forEach(prof => {
        if (prof.research_interests && Array.isArray(prof.research_interests)) {
            prof.research_interests.forEach(area => areas.add(area));
        }
        if (prof.university_name) {
            universities.add(prof.university_name);
        }
    });

    // Populate area filter
    const areaSelect = document.getElementById('filter-area');
    Array.from(areas).sort().forEach(area => {
        const option = document.createElement('option');
        option.value = area;
        option.textContent = area;
        areaSelect.appendChild(option);
    });

    // Populate university filter
    const uniSelect = document.getElementById('filter-university');
    Array.from(universities).sort().forEach(uni => {
        const option = document.createElement('option');
        option.value = uni;
        option.textContent = uni;
        uniSelect.appendChild(option);
    });

    // Attach event listeners
    document.getElementById('filter-priority').addEventListener('change', applyFilters);
    document.getElementById('filter-area').addEventListener('change', applyFilters);
    document.getElementById('filter-university').addEventListener('change', applyFilters);
    document.getElementById('filter-sort').addEventListener('change', applyFilters);
}

// Apply all active filters and render
function applyFilters() {
    const priorityFilter = document.getElementById('filter-priority').value;
    const areaFilter = document.getElementById('filter-area').value;
    const universityFilter = document.getElementById('filter-university').value;

    console.log('Filters:', { priorityFilter, areaFilter, universityFilter });
    console.log('Sample professor:', allProfessors[0]);

    const filtered = allProfessors.filter(prof => {
        // Priority filter - convert both to same type
        if (priorityFilter !== 'all') {
            const filterPriority = parseInt(priorityFilter, 10);
            if (prof.priority !== filterPriority) {
                return false;
            }
        }
        // Area filter - case-insensitive
        if (areaFilter !== 'all') {
            if (!prof.research_interests || !prof.research_interests.some(area =>
                area.toLowerCase() === areaFilter.toLowerCase()
            )) {
                return false;
            }
        }
        // University filter
        if (universityFilter !== 'all' && prof.university_name !== universityFilter) {
            return false;
        }
        return true;
    });

    // Sort
    const sortValue = document.getElementById('filter-sort').value;
    if (sortValue === 'match-desc') {
        filtered.sort((a, b) => {
            const aScore = a.direction_match_score === null || a.direction_match_score === undefined ? -Infinity : a.direction_match_score;
            const bScore = b.direction_match_score === null || b.direction_match_score === undefined ? -Infinity : b.direction_match_score;
            return bScore - aScore;
        });
    } else if (sortValue === 'diff-asc') {
        filtered.sort((a, b) => {
            const aScore = a.admission_difficulty_score === null || a.admission_difficulty_score === undefined ? Infinity : a.admission_difficulty_score;
            const bScore = b.admission_difficulty_score === null || b.admission_difficulty_score === undefined ? Infinity : b.admission_difficulty_score;
            return aScore - bScore;
        });
    }

    console.log('Filtered count:', filtered.length);
    renderProfessors(filtered);
}

// ============ End Filter functionality ============
function renderProfessors(profList) {
    const container = document.getElementById('professor-list');

    if (profList.length === 0) {
        container.innerHTML = '<div class="loading">No professors</div>';
        return;
    }

    container.innerHTML = profList.map(prof => `
        <div class="professor-card" data-id="${prof.id}" onclick="switchToChat(${prof.id})">
            <div class="priority-strip priority-strip-${prof.priority === -1 ? 'neg1' : prof.priority}"></div>
            <div class="card-top">
                <div class="card-name-wrapper">
                    <div class="card-name" onclick="event.stopPropagation(); openProfessor(${prof.id})">${escapeHtml(prof.name)}</div>
                    <select class="priority-select" data-id="${prof.id}" data-priority="${prof.priority}" onclick="event.stopPropagation()">
                        <option value="-1" ${prof.priority === -1 ? 'selected' : ''}>Not Considered</option>
                        <option value="0" ${prof.priority === 0 ? 'selected' : ''}>Reach</option>
                        <option value="1" ${prof.priority === 1 ? 'selected' : ''}>Good Match</option>
                        <option value="2" ${prof.priority === 2 ? 'selected' : ''}>Safe</option>
                        <option value="3" ${prof.priority === 3 ? 'selected' : ''}>Backup</option>
                    </select>
                </div>
                <div class="card-scores">
                    <div class="score-pill match" title="Direction Match: how well your research aligns with this professor">
                        <span class="score-pill-label">Match</span>
                        <span class="score-pill-value">${prof.direction_match_score || '-'}</span>
                    </div>
                    <div class="score-pill diff" title="Admission Difficulty: how hard it is to get admitted to this professor">
                        <span class="score-pill-label">Diff</span>
                        <span class="score-pill-value">${prof.admission_difficulty_score || '-'}</span>
                    </div>
                </div>
            </div>

            <div class="card-meta">
                <span>📄 ${prof.total_papers || 0} papers</span>
                <span>🔗 ${(prof.papers || []).length} with links</span>
                <span class="card-university">${escapeHtml(prof.university_name)}</span>
                <div class="tag-area">
                    ${(prof.research_interests || []).slice(0, 3).map(interest =>
                        `<span class="tag" title="${escapeHtml(interest)}">${escapeHtml(interest.toUpperCase())}</span>`
                    ).join('')}
                </div>
            </div>
        </div>
    `).join('');

    // Attach change listeners to priority selects
    document.querySelectorAll('.priority-select').forEach(select => {
        select.addEventListener('change', updatePriority);
    });
}

// Simple markdown to HTML converter for chat messages
function simpleMarkdownToHtml(text) {
    if (!text) return '';
    let html = escapeHtml(text);
    // Code blocks
    html = html.replace(/```(\w+)?\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>');
    // Inline code
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
    // Bold
    html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/__([^_]+)__/g, '<strong>$1</strong>');
    // Italic
    html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');
    html = html.replace(/_([^_]+)_/g, '<em>$1</em>');
    // Headers
    html = html.replace(/^#### (.*$)/gim, '<h4>$1</h4>');
    html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');
    html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>');
    html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>');
    // Lists
    html = html.replace(/^\s*[-*] (.*$)/gim, '<li>$1</li>');
    html = html.replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>');
    html = html.replace(/<\/ul>\s*<ul>/g, '');
    // Line breaks
    html = html.replace(/\n/g, '<br>');
    return html;
}

// Load chat messages for a professor
async function loadChatMessages(profId) {
    const container = document.getElementById('chat-messages');
    container.innerHTML = '';

    try {
        const response = await fetch(`/api/chat/${profId}`);
        if (!response.ok) return;
        const data = await response.json();

        if (data.messages && data.messages.length > 0) {
            // Render existing messages
            for (let i = 0; i < data.messages.length; i++) {
                const msg = data.messages[i];
                addChatMessage(msg.content, msg.role === 'user' ? 'user' : 'assistant', null, false, i);
            }
        } else {
            // No messages yet — trigger first-time analysis
            container.innerHTML = '';
            const loadingId = 'loading-init-' + profId;
            addChatMessage('', 'assistant', loadingId, true);
            // Update the loading text to be more descriptive
            const loadingMsg = document.getElementById(loadingId);
            if (loadingMsg) {
                const textSpan = loadingMsg.querySelector('.analyzing-text');
                if (textSpan) textSpan.textContent = 'Analyzing professor and generating cold email draft';
            }
            chatLoading = true;

            try {
                const postResp = await fetch(`/api/chat/${profId}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({})
                });
                const postData = await postResp.json();
                container.innerHTML = '';
                if (postData.success && postData.response) {
                    addChatMessage(postData.response, 'assistant', null, false, 0);
                } else {
                    addChatMessage('Failed to generate analysis. Please try again.', 'assistant', null, false, 0);
                }
            } catch (err) {
                container.innerHTML = '';
                addChatMessage('Failed to generate analysis. Please try again.', 'assistant', null, false, 0);
            } finally {
                chatLoading = false;
            }
        }
    } catch (error) {
        console.error('Failed to load chat messages:', error);
    }
}

// Switch to Chat page for a specific professor
async function switchToChat(profId) {
    const prof = professors.find(p => p.id === profId);
    if (!prof) return;

    // Switch to Chat page
    document.querySelectorAll('.nav-button').forEach(btn => btn.classList.remove('active'));
    document.querySelector('[data-page="chat"]').classList.add('active');
    document.querySelectorAll('.page-container').forEach(page => page.classList.remove('active'));
    document.getElementById('page-chat').classList.add('active');

    // Update chat header
    document.getElementById('chat-prof-name').textContent = prof.name;
    document.getElementById('chat-prof-uni').textContent = prof.university_name;

    // Highlight the professor card
    document.querySelectorAll('.professor-card').forEach(card => card.classList.remove('active'));
    document.querySelector(`[data-id="${profId}"]`)?.classList.add('active');

    selectedProfessor = prof;

    // Load messages (and trigger first analysis if empty)
    await loadChatMessages(profId);
}

// Open professor detail modal
function openProfessor(profId) {
    // Update active state
    document.querySelectorAll('.professor-card').forEach(card => card.classList.remove('active'));
    document.querySelector(`[data-id="${profId}"]`)?.classList.add('active');

    const prof = professors.find(p => p.id === profId);
    if (!prof) return;

    selectedProfessor = prof;

    document.getElementById('modal-title').textContent = `${prof.name}`;

    document.getElementById('modal-body').innerHTML = `
        <div class="section">
            <div class="section-title">Basic Info</div>
            <div class="info-grid">
                <div class="info-item">
                    <div class="info-label">University</div>
                    <div class="info-value">${prof.university_name} ${prof.university_rank ? `(#${prof.university_rank})` : ''}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Research Interests</div>
                    <div class="tags">
                        ${(prof.research_interests || []).map(interest =>
                            `<span class="tag">${escapeHtml(interest)}</span>`
                        ).join('')}
                    </div>
                </div>
            </div>
        </div>

        <div class="section">
            <div class="section-title" style="display:flex;align-items:center;justify-content:space-between;">
                Metrics
                <button class="btn-rescore" onclick="rescoreProfessor(${prof.id})" id="rescore-btn-${prof.id}">
                    <span class="btn-text">&#x21bb; Rescore</span>
                </button>
            </div>
            <div class="metrics-grid">
                <div class="metric-box">
                    <div class="metric-label">Direction Match</div>
                    <div class="metric-value" id="metric-dm-${prof.id}">${prof.direction_match_score || '-'}/5</div>
                </div>
                <div class="metric-box">
                    <div class="metric-label">Admission Difficulty</div>
                    <div class="metric-value" id="metric-ad-${prof.id}">${prof.admission_difficulty_score || '-'}/5</div>
                </div>
            </div>
        </div>

        <div class="section">
            <div class="section-title">Homepage Content</div>
            ${prof.homepage_summary ? `
                <div class="homepage-summary">
                    ${prof.homepage_summary.split('\n').map(line => {
                        if (line.startsWith('Research Focus:')) {
                            return `<div class="homepage-line"><span class="homepage-label">Research Focus</span><span class="homepage-text">${escapeHtml(line.replace('Research Focus:', '').trim())}</span></div>`;
                        } else if (line.startsWith('Recruiting:')) {
                            const status = line.replace('Recruiting:', '').trim();
                            const statusClass = status === 'accepting' ? 'recruiting-yes' : status === 'not_accepting' ? 'recruiting-no' : 'recruiting-unknown';
                            return `<div class="homepage-line"><span class="homepage-label">Recruiting</span><span class="homepage-badge ${statusClass}">${escapeHtml(status)}</span></div>`;
                        } else if (line.startsWith('Summary:')) {
                            return `<div class="homepage-line"><span class="homepage-label">Summary</span><span class="homepage-text">${escapeHtml(line.replace('Summary:', '').trim())}</span></div>`;
                        } else {
                            return `<div class="homepage-line"><span class="homepage-text">${escapeHtml(line)}</span></div>`;
                        }
                    }).join('')}
                </div>
            ` : prof.homepage_fetch_status === 'pending' ? '<p style="color: var(--text-muted); font-size: 13px;">Homepage analysis pending...</p>' : prof.homepage_fetch_status === 'failed' ? '<p style="color: var(--text-muted); font-size: 13px;">Homepage analysis failed</p>' : '<p style="color: var(--text-muted); font-size: 13px;">No homepage content available</p>'}
        </div>

        <div class="section">
            <div class="section-title">Contact</div>
            <div class="info-grid">
                <div class="info-item">
                    <div class="info-label">Homepage</div>
                    <div class="info-value">${prof.homepage ? `<a href="${escapeHtml(prof.homepage)}" target="_blank" class="paper-link">${escapeHtml(prof.homepage)}</a>` : 'Not provided'}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Email</div>
                    <div class="info-value">${prof.email ? `<a href="mailto:${escapeHtml(prof.email)}" class="paper-link">${escapeHtml(prof.email)}</a>` : 'Not provided'}</div>
                </div>
            </div>
        </div>

        <div class="section">
            <div class="section-title">Papers (${(prof.papers || []).length})</div>
            <div id="papers-list">
            ${prof.papers && prof.papers.length > 0
                ? prof.papers.map(paper => `
                    <div class="paper-item" data-paper-id="${paper.id}">
                        <div class="paper-header">
                            <div class="paper-title">${paper.url ? `<a href="${escapeHtml(paper.url)}" target="_blank" class="paper-title-link">${escapeHtml(paper.title)}</a>` : escapeHtml(paper.title)}</div>
                            <button class="paper-delete-btn" onclick="deletePaper(${prof.id}, ${paper.id}, this)" title="Delete paper">
                                &#x2715;
                            </button>
                        </div>
                        <div class="paper-meta">
                            <span>📅 ${paper.year || 'N/A'}</span>
                            ${paper.venue ? `<span>📍 ${escapeHtml(paper.venue)}</span>` : ''}
                            ${paper.citation_count ? `<span>🔗 ${paper.citation_count} citations</span>` : ''}
                        </div>
                        <div class="paper-abstract">${escapeHtml(paper.abstract || 'No abstract')}</div>
                        <div class="paper-links">
                            ${paper.url ? `<a href="${escapeHtml(paper.url)}" target="_blank" class="paper-link">arXiv</a>` : ''}
                            ${paper.local_pdf_path ? `<a href="/papers/${encodeURIComponent(escapeHtml(paper.local_pdf_path))}" target="_blank" class="paper-link">PDF</a>` : ''}
                        </div>
                    </div>
                `).join('')
                : '<p style="color: var(--text-muted); font-size: 13px;">No papers yet</p>'
            }
            </div>
            <div class="add-paper-row">
                <input type="text" id="add-paper-input-${prof.id}" class="add-paper-input" placeholder="Paste arXiv URL..." />
                <button class="btn-add-paper" onclick="addPaper(${prof.id})">Add</button>
            </div>
        </div>
    `;

    document.getElementById('modal-overlay').classList.add('active');
}

// ========== Rescore ==========
async function rescoreProfessor(profId) {
    const btn = document.getElementById('rescore-btn-' + profId);
    if (!btn) return;

    btn.disabled = true;
    btn.querySelector('.btn-text').textContent = 'Rescoring...';

    try {
        const resp = await fetch(`/api/professor/${profId}/rescore`, { method: 'POST' });
        const data = await resp.json();

        if (resp.ok && data.success) {
            showToast('Rescored successfully! DM=' + data.direction_match + ' AD=' + data.admission_difficulty, 'success');
            // Update scores in modal
            const dmEl = document.getElementById('metric-dm-' + profId);
            const adEl = document.getElementById('metric-ad-' + profId);
            if (dmEl) dmEl.textContent = (data.direction_match || '-') + '/5';
            if (adEl) adEl.textContent = (data.admission_difficulty || '-') + '/5';
            // Also update the professor card
            const prof = professors.find(p => p.id === profId);
            if (prof) {
                prof.direction_match_score = data.direction_match;
                prof.admission_difficulty_score = data.admission_difficulty;
            }
            renderProfessors();
        } else {
            showToast(data.error || 'Rescoring failed', 'error');
        }
    } catch (e) {
        showToast('Rescoring failed: ' + e.message, 'error');
    } finally {
        btn.disabled = false;
        btn.querySelector('.btn-text').textContent = '\u21bb Rescore';
    }
}

// ========== Add Paper ==========
async function addPaper(profId) {
    const input = document.getElementById('add-paper-input-' + profId);
    if (!input) return;

    const url = input.value.trim();
    if (!url) {
        showToast('Please enter an arXiv URL', 'error');
        return;
    }

    try {
        const resp = await fetch(`/api/professor/${profId}/paper`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url }),
        });
        const data = await resp.json();

        if (resp.ok && data.success) {
            showToast('Paper added: ' + data.paper.title, 'success');
            input.value = '';
            // Refresh modal
            await refreshProfessorModal(profId);
        } else {
            showToast(data.error || (data.detail ? data.detail : 'Failed to add paper'), 'error');
        }
    } catch (e) {
        showToast('Failed to add paper: ' + e.message, 'error');
    }
}

// ========== Delete Paper ==========
async function deletePaper(profId, paperId, btnEl) {
    if (!confirm('Delete this paper?')) return;

    try {
        const resp = await fetch(`/api/professor/${profId}/paper/${paperId}`, {
            method: 'DELETE',
        });
        const data = await resp.json();

        if (resp.ok && data.success) {
            showToast('Paper deleted', 'success');
            // Remove from DOM
            const item = btnEl.closest('.paper-item');
            if (item) item.remove();
            // Also update the professor card count
            const prof = professors.find(p => p.id === profId);
            if (prof && prof.papers) {
                prof.papers = prof.papers.filter(p => p.id !== paperId);
            }
        } else {
            showToast(data.error || 'Failed to delete paper', 'error');
        }
    } catch (e) {
        showToast('Failed to delete paper: ' + e.message, 'error');
    }
}

// ========== Refresh Modal ==========
async function refreshProfessorModal(profId) {
    try {
        const resp = await fetch(`/api/professor/${profId}`);
        if (!resp.ok) return;
        const freshProf = await resp.json();
        // Update in-memory list
        const idx = professors.findIndex(p => p.id === profId);
        if (idx >= 0) {
            professors[idx] = freshProf;
        }
        // Re-render modal
        openProfessorModal(freshProf);
    } catch (e) {
        console.error('Failed to refresh modal:', e);
    }
}

// Close modal
function closeModal() {
    document.getElementById('modal-overlay').classList.remove('active');
    selectedProfessor = null;
    document.querySelectorAll('.professor-card').forEach(card => card.classList.remove('active'));
}

// Event listeners
document.getElementById('modal-overlay').addEventListener('click', (e) => {
    if (e.target === document.getElementById('modal-overlay')) closeModal();
});

document.getElementById('modal-close').addEventListener('click', closeModal);

document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeModal();
});

// Send message
async function sendMessage() {
    const input = document.getElementById('user-input');
    const message = input.value.trim();

    if (!message) return;
    if (!selectedProfessor) {
        showToast('Please select a professor from the list first.', 'error');
        return;
    }
    if (chatLoading) return;

    const container = document.getElementById('chat-messages');
    const userIndex = container.children.length;
    addChatMessage(message, 'user', null, false, userIndex);
    input.value = '';
    chatLoading = true;

    // Show "Analyzing..." loading indicator
    const loadingId = 'loading-' + Date.now();
    addChatMessage('', 'assistant', loadingId, true);

    try {
        const response = await fetch(`/api/chat/${selectedProfessor.id}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: message })
        });
        const data = await response.json();

        // Remove loading indicator
        const loadingMsg = document.getElementById(loadingId);
        if (loadingMsg) loadingMsg.remove();

        const assistantIndex = container.children.length;
        if (data.success && data.response) {
            addChatMessage(data.response, 'assistant', null, false, assistantIndex);
        } else {
            addChatMessage('Sorry, I encountered an error. Please try again.', 'assistant', null, false, assistantIndex);
        }
    } catch (error) {
        // Remove loading indicator
        const loadingMsg = document.getElementById(loadingId);
        if (loadingMsg) loadingMsg.remove();

        const assistantIndex = container.children.length;
        addChatMessage('Sorry, I encountered an error. Please try again.', 'assistant', null, false, assistantIndex);
        console.error('Chat API error:', error);
    } finally {
        chatLoading = false;
    }
}

function addChatMessage(content, type, msgId, isLoading, visibleIndex) {
    const container = document.getElementById('chat-messages');
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${type}`;
    if (msgId) msgDiv.id = msgId;

    // Avatar
    const avatarDiv = document.createElement('div');
    avatarDiv.className = 'chat-avatar';
    if (type === 'assistant') {
        avatarDiv.innerHTML = `<img src="static/windsurf.svg" alt="AI" class="avatar-img">`;
    } else {
        const displayName = userNickname || 'Me';
        avatarDiv.textContent = displayName.slice(0, 2);
        avatarDiv.classList.add('user-avatar');
    }

    // Content wrapper
    const wrapperDiv = document.createElement('div');
    wrapperDiv.className = 'message-wrapper';

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';

    if (isLoading) {
        contentDiv.innerHTML = `<span class="analyzing-text">Analyzing</span><span class="analyzing-dots"></span>`;
    } else if (type === 'assistant') {
        contentDiv.innerHTML = simpleMarkdownToHtml(content);
    } else {
        contentDiv.textContent = content;
    }

    wrapperDiv.appendChild(contentDiv);

    // Delete button (not for loading messages)
    if (!isLoading && visibleIndex !== undefined) {
        const deleteBtn = document.createElement('button');
        deleteBtn.className = 'message-delete-btn';
        deleteBtn.innerHTML = '🗑';
        deleteBtn.title = 'Delete message';
        deleteBtn.onclick = async () => {
            if (!confirm('Delete this message?')) return;
            await deleteChatMessage(visibleIndex);
        };
        wrapperDiv.appendChild(deleteBtn);
    }

    msgDiv.appendChild(avatarDiv);
    msgDiv.appendChild(wrapperDiv);
    container.appendChild(msgDiv);
    container.scrollTop = container.scrollHeight;
}

async function deleteChatMessage(visibleIndex) {
    if (!selectedProfessor) return;
    try {
        const response = await fetch(`/api/chat/${selectedProfessor.id}/message`, {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ index: visibleIndex })
        });
        if (!response.ok) {
            const text = await response.text();
            alert(`Delete failed (${response.status}): ${text}`);
            return;
        }
        const data = await response.json();
        if (data.success) {
            await loadChatMessages(selectedProfessor.id);
        } else {
            alert(data.error || 'Failed to delete message');
        }
    } catch (error) {
        console.error('Delete message error:', error);
        alert('Delete failed: ' + error.message);
    }
}

// Utility functions
function escapeHtml(text) {
    if (!text && text !== 0) return '';
    const div = document.createElement('div');
    div.textContent = String(text);
    return div.innerHTML;
}

// Update professor priority
async function updatePriority(event) {
    const select = event.target;
    const profId = parseInt(select.dataset.id);
    const priority = parseInt(select.value);

    try {
        const response = await fetch(`/api/professor/${profId}/priority`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ priority })
        });

        const data = await response.json();

        if (data.success) {
            console.log(`Priority updated for professor ${profId}: ${priority}`);
            // Reload professors to reflect the change
            loadProfessors();
        } else {
            throw new Error(data.error || 'Update failed');
        }
    } catch (error) {
        console.error('Failed to update priority:', error);
        // Revert selection on error
        showToast('Failed to update priority. Please try again.', 'error');
    }
}

// Event bindings
document.getElementById('user-input').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendMessage();
});

document.getElementById('send-btn').addEventListener('click', sendMessage);

// ============ Hunt Page: Tags ============

// Region display name mapping (flag emoji + clean name)
const REGION_NAMES = {
    'world': 'World',
    'asia': 'Asia',
    'northamerica': 'North America',
    'europe': 'Europe',
    'australasia': 'Australasia',
    'southamerica': 'South America',
    'africa': 'Africa',
    'us': 'United States',
    'cn': 'China',
    'jp': 'Japan',
    'in': 'India',
    'kr': 'South Korea',
    'sg': 'Singapore',
    'hk': 'Hong Kong',
    'tw': 'Taiwan',
    'mo': 'Macao',
    'my': 'Malaysia',
    'id': 'Indonesia',
    'ph': 'Philippines',
    'th': 'Thailand',
    'vn': 'Vietnam',
    'lk': 'Sri Lanka',
    'bd': 'Bangladesh',
    'ca': 'Canada',
    'gb': 'United Kingdom',
    'de': 'Germany',
    'fr': 'France',
    'it': 'Italy',
    'es': 'Spain',
    'nl': 'Netherlands',
    'ch': 'Switzerland',
    'se': 'Sweden',
    'at': 'Austria',
    'be': 'Belgium',
    'dk': 'Denmark',
    'fi': 'Finland',
    'gr': 'Greece',
    'ie': 'Ireland',
    'pl': 'Poland',
    'pt': 'Portugal',
    'cz': 'Czech Republic',
    'hu': 'Hungary',
    'ro': 'Romania',
    'sk': 'Slovakia',
    'bg': 'Bulgaria',
    'lu': 'Luxembourg',
    'mt': 'Malta',
    'cy': 'Cyprus',
    'ee': 'Estonia',
    'lv': 'Latvia',
    'lt': 'Lithuania',
    'ua': 'Ukraine',
    'by': 'Belarus',
    'rs': 'Serbia',
    'hr': 'Croatia',
    'si': 'Slovenia',
    'no': 'Norway',
    'au': ' Australia',
    'nz': ' New Zealand',
    'br': ' Brazil',
    'ar': ' Argentina',
    'cl': ' Chile',
    'co': ' Colombia',
    'za': ' South Africa',
    'eg': ' Egypt',
    'ma': ' Morocco',
    'ae': ' UAE',
    'sa': ' Saudi Arabia',
    'il': ' Israel',
    'ir': ' Iran',
    'jo': ' Jordan',
    'qa': ' Qatar',
    'lb': ' Lebanon',
    'pk': ' Pakistan',
    'ru': 'Russia',
    'tr': 'Turkey'
};

// Research Area display names
const AREA_NAMES = {
    'ai': 'AI',
    'ml': 'ML',
    'nlp': 'NLP',
    'vision': 'Vision',
    'ir': 'Information Retrieval',
    'systems': 'Systems',
    'arch': 'Architecture',
    'net': 'Networking',
    'os': 'Operating Systems',
    'da': 'Data Engineering',
    'es': 'Embedded Systems',
    'hpca': 'High Performance Computing',
    'mob': 'Mobile Computing',
    'metrics': 'Metrics',
    'pl': 'Programming Languages',
    'se': 'Software Engineering',
    'sec': 'Security',
    'crypto': 'Cryptography',
    'theory': 'Theory',
    'db': 'Databases',
    'hci': 'HCI',
    'interdisciplinary': 'Interdisciplinary',
    'bio': 'Bioinformatics',
    'graphics': 'Graphics',
    'ed': 'Educational Tech',
    'econ': 'Economics',
    'robotics': 'Robotics',
    'visualization': 'Visualization'
};

// Selection state (loaded from server config, not localStorage)
let selectedRegion = '';
let selectedAreas = new Set();

function renderAreaTags() {
    const tagsContainer = document.getElementById('area-tags');
    if (!tagsContainer) return;
    tagsContainer.innerHTML = '';
    selectedAreas.forEach(value => {
        const tag = document.createElement('span');
        tag.className = 'area-tag';
        tag.dataset.area = value;
        const name = AREA_NAMES[value] || value;
        tag.innerHTML = `<span>${name}</span><button class="remove-tag" data-value="${value}" title="Remove">×</button>`;
        tagsContainer.appendChild(tag);
    });

    tagsContainer.querySelectorAll('.remove-tag').forEach(btn => {
        btn.addEventListener('click', (e) => {
            selectedAreas.delete(e.target.dataset.value);
            saveSelectedAreas();
            renderAreaTags();
        });
    });
}

// Save selections to server config
async function saveSelectedRegion() {
    try {
        await fetch('/api/hunt-config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ regions: selectedRegion ? [selectedRegion] : [] })
        });
    } catch (e) {
        console.error('Failed to save region:', e);
    }
}

async function saveSelectedAreas() {
    try {
        await fetch('/api/hunt-config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ areas: Array.from(selectedAreas) })
        });
    } catch (e) {
        console.error('Failed to save areas:', e);
    }
}

// Load hunt config from server and restore UI
async function loadHuntConfig() {
    try {
        const response = await fetch('/api/hunt-config');
        if (!response.ok) return;
        const config = await response.json();

        // Restore areas
        if (config.areas && Array.isArray(config.areas)) {
            selectedAreas = new Set(config.areas);
        }
        // Restore region (single selection from first item)
        if (config.regions && Array.isArray(config.regions) && config.regions.length > 0) {
            selectedRegion = config.regions[0];
        }
        // Restore year selects
        if (config.start_year) {
            const el = document.getElementById('hunt-start-year');
            if (el) el.value = config.start_year;
        }
        if (config.end_year) {
            const el = document.getElementById('hunt-end-year');
            if (el) el.value = config.end_year;
        }
        if (config.max_universities) {
            const el = document.getElementById('hunt-max-universities');
            if (el) el.value = config.max_universities;
        }
        if (config.max_professors) {
            const el = document.getElementById('hunt-max-professors');
            if (el) el.value = config.max_professors;
        }
        if (config.max_papers) {
            const el = document.getElementById('hunt-max-papers');
            if (el) el.value = config.max_papers;
        }

        // Restore region select value
        const regionSelect = document.getElementById('hunt-region');
        if (regionSelect && selectedRegion) {
            regionSelect.value = selectedRegion;
        }

        // Render area tags
        renderAreaTags();
    } catch (error) {
        console.error('Failed to load hunt config:', error);
    }
}

// Initialize region select (single selection, no tags)
(function initRegionSelect() {
    const regionSelect = document.getElementById('hunt-region');
    if (!regionSelect) return;

    regionSelect.addEventListener('change', (e) => {
        if (e.target.value) {
            selectedRegion = e.target.value;
            saveSelectedRegion();
        }
    });
})();

// Initialize area tags
(function initAreaTags() {
    const areaSelect = document.getElementById('hunt-area');
    if (!areaSelect) return;

    areaSelect.addEventListener('change', (e) => {
        if (e.target.value && !selectedAreas.has(e.target.value)) {
            selectedAreas.add(e.target.value);
            saveSelectedAreas();
            renderAreaTags();
        }
        e.target.value = '';
    });
})();

// ============ End Hunt Page Tags ============

// ============ Hunt Progress & Background Crawl ============

let huntPollingInterval = null;

// Start Hunt button handler
document.getElementById('start-hunt-btn').addEventListener('click', async () => {
    // Collect selected areas
    const areas = Array.from(selectedAreas);
    if (areas.length === 0) {
        showToast('Please select at least one research area.', 'error');
        return;
    }

    // Collect selected region
    const regions = selectedRegion ? [selectedRegion] : [];
    if (regions.length === 0) {
        showToast('Please select at least one region.', 'error');
        return;
    }

    // Collect other parameters
    const startYear = parseInt(document.getElementById('hunt-start-year').value);
    const endYear = parseInt(document.getElementById('hunt-end-year').value);
    const maxUniversities = parseInt(document.getElementById('hunt-max-universities').value);
    const maxProfessors = parseInt(document.getElementById('hunt-max-professors').value);
    const maxPapers = parseInt(document.getElementById('hunt-max-papers').value);

    // Validate
    if (startYear >= endYear) {
        showToast('End year must be greater than start year.', 'error');
        return;
    }

    // Save full config to server first
    try {
        const configResp = await fetch('/api/hunt-config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                areas, regions, start_year: startYear, end_year: endYear,
                max_universities: maxUniversities, max_professors: maxProfessors, max_papers: maxPapers
            })
        });
        if (!configResp.ok) {
            throw new Error('Failed to save hunt configuration');
        }
    } catch (e) {
        showToast('Error saving config: ' + e.message, 'error');
        return;
    }

    // Show progress panel
    document.getElementById('hunt-progress').style.display = 'block';

    // Reset progress UI
    resetProgressUI();

    // Disable button during hunt
    const btn = document.getElementById('start-hunt-btn');
    btn.disabled = true;
    btn.querySelector('.button-text').textContent = 'Hunting in progress...';

    // Show stop button
    document.getElementById('stop-hunt-btn').style.display = 'inline-block';

    // Clear any existing polling
    if (huntPollingInterval) {
        clearInterval(huntPollingInterval);
    }

    // Start polling for status (fast 300ms for responsive stop detection)
    huntPollingInterval = setInterval(updateHuntProgress, 300);

    // Send start request (no params needed; worker reads from file)
    try {
        const response = await fetch('/api/start-hunt', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({})
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to start hunt');
        }

        // Save current page and reload to stay on Hunt tab with fresh state
        localStorage.setItem(ACTIVE_PAGE_KEY, 'hunt');
        location.reload();
    } catch (error) {
        showToast('Error: ' + error.message, 'error');
        resetHuntButton();
        document.getElementById('hunt-progress').style.display = 'none';
        if (huntPollingInterval) {
            clearInterval(huntPollingInterval);
            huntPollingInterval = null;
        }
    }
});

// Update progress UI from server
async function updateHuntProgress() {
    try {
        const response = await fetch('/api/hunt-status');
        if (!response.ok) return;

        const status = await response.json();

        // Update professors progress
        let profPercent = 0;
        let profText = '0%';
        if (status.professors_total === -1) {
            // Indeterminate: fetching from CSRankings
            profText = 'Fetching...';
        } else if (status.professors_total > 0) {
            profPercent = Math.round((status.professors_completed / status.professors_total) * 100);
            profText = profPercent + '%';
        }
        document.getElementById('professors-bar').style.width = profPercent + '%';
        document.getElementById('professors-percent').textContent = profText;

        // Update papers progress
        const papersPercent = status.papers_total > 0
            ? Math.round((status.papers_completed / status.papers_total) * 100)
            : 0;
        document.getElementById('papers-bar').style.width = papersPercent + '%';
        document.getElementById('papers-percent').textContent = papersPercent + '%';

        // Show/hide phase sections
        document.getElementById('phase-crawl').style.display = status.running && status.phase === 'crawl' ? 'block' : 'none';
        document.getElementById('phase-papers').style.display = status.running && status.phase === 'papers' ? 'block' : 'none';

        // Update logs — show only the latest line
        const logsContainer = document.getElementById('progress-logs');
        if (status.logs && status.logs.length > 0) {
            const latestLog = status.logs[status.logs.length - 1];
            const displayText = '> ' + latestLog;
            const currentText = logsContainer.textContent;
            if (currentText !== displayText) {
                logsContainer.innerHTML = '';
                const line = document.createElement('div');
                line.className = 'log-line';
                line.textContent = displayText;
                logsContainer.appendChild(line);
            }
        }

        // Check if hunt completed or stopped
        if (!status.running && status.phase === null) {
            clearInterval(huntPollingInterval);
            huntPollingInterval = null;
            resetHuntButton();
            // Check logs to determine if it was stopped or completed
            const lastLog = status.logs[status.logs.length - 1] || '';
            if (lastLog.includes('stopped by user') || lastLog.includes('Stop requested')) {
                showToast('Hunting stopped.', 'info');
            } else {
                showToast('Hunting completed!', 'success');
            }
            // Refresh professor list without full page reload
            await loadProfessors();
        }

        // Check for error
        if (status.error) {
            clearInterval(huntPollingInterval);
            huntPollingInterval = null;
            resetHuntButton();
            showToast('Error: ' + status.error, 'error');
        }

    } catch (error) {
        console.error('Failed to update progress:', error);
    }
}

function resetProgressUI() {
    // Reset both progress bars
    document.getElementById('professors-bar').style.width = '0%';
    document.getElementById('professors-percent').textContent = '0%';
    document.getElementById('papers-bar').style.width = '0%';
    document.getElementById('papers-percent').textContent = '0%';

    // Hide papers phase initially
    document.getElementById('phase-papers').style.display = 'none';
    document.getElementById('phase-crawl').style.display = 'block';

    // Clear logs
    const logsContainer = document.getElementById('progress-logs');
    logsContainer.innerHTML = '';
}

function resetHuntButton() {
    const startBtn = document.getElementById('start-hunt-btn');
    startBtn.disabled = false;
    startBtn.querySelector('.button-text').textContent = 'Start Hunting';
    // Hide stop button
    const stopBtn = document.getElementById('stop-hunt-btn');
    stopBtn.style.display = 'none';
}

// Restore hunt progress on page load (for page refresh scenarios)
async function restoreHuntProgress() {
    try {
        const response = await fetch('/api/hunt-status');
        if (!response.ok) return;

        const status = await response.json();

        // If a hunt is still running, restore UI
        if (status.running && status.phase) {
            console.log('Restoring hunt progress:', status);

            // Show progress panel
            document.getElementById('hunt-progress').style.display = 'block';

            // Reset UI to current state (will be updated by first poll)
            resetProgressUI();

            // Disable start button and show stop button
            document.getElementById('start-hunt-btn').disabled = true;
            document.getElementById('start-hunt-btn').querySelector('.button-text').textContent = 'Hunting in progress...';
            document.getElementById('stop-hunt-btn').style.display = 'inline-block';

            // Start polling immediately (fast 300ms)
            huntPollingInterval = setInterval(updateHuntProgress, 300);

            console.log('Hunt is still running. Progress restored.');
        }
    } catch (error) {
        console.error('Failed to restore hunt progress:', error);
    }
}

// ============ End Hunt Progress ============

// ============ Profile Page ============

// In-memory paper list: [{url, title, arxiv_id, pdf_url}]
let profilePapers = [];

async function loadProfile() {
    try {
        const response = await fetch('/api/profile');
        if (!response.ok) return;
        const profile = await response.json();

        // CV
        if (profile.cv) {
            showFileInfo('cv', profile.cv.filename);
        } else {
            hideFileInfo('cv');
        }

        // PS
        if (profile.ps) {
            showFileInfo('ps', profile.ps.filename);
        } else {
            hideFileInfo('ps');
        }

        // Paper links — support both old format (string array) and new format (object array)
        profilePapers = [];
        if (profile.paper_links && Array.isArray(profile.paper_links)) {
            for (const item of profile.paper_links) {
                if (typeof item === 'string') {
                    // Old format: just a URL string
                    profilePapers.push({ url: item, title: item, arxiv_id: '', pdf_url: '' });
                } else if (item && typeof item === 'object') {
                    // New format: {url, title, arxiv_id, pdf_url}
                    profilePapers.push({
                        url: item.url || '',
                        title: item.title || item.url || '',
                        arxiv_id: item.arxiv_id || '',
                        pdf_url: item.pdf_url || ''
                    });
                }
            }
        }
        renderPaperTags();

        // Preferences
        const prefEl = document.getElementById('profile-preferences');
        if (prefEl && profile.preferences) {
            prefEl.value = profile.preferences;
        }
    } catch (error) {
        console.error('Failed to load profile:', error);
    }
}

function showFileInfo(type, filename) {
    const uploadBox = document.getElementById(`${type}-upload-box`);
    const fileInfo = document.getElementById(`${type}-file-info`);
    const filenameEl = document.getElementById(`${type}-filename`);
    if (uploadBox) uploadBox.style.display = 'none';
    if (fileInfo) fileInfo.style.display = 'flex';
    if (filenameEl) filenameEl.textContent = filename;
}

function hideFileInfo(type) {
    const uploadBox = document.getElementById(`${type}-upload-box`);
    const fileInfo = document.getElementById(`${type}-file-info`);
    if (uploadBox) uploadBox.style.display = 'block';
    if (fileInfo) fileInfo.style.display = 'none';
}

function renderPaperTags() {
    const container = document.getElementById('paper-tags');
    if (!container) return;

    if (profilePapers.length === 0) {
        container.innerHTML = '';
        return;
    }

    container.innerHTML = profilePapers.map((paper, index) => `
        <div class="paper-tag" data-index="${index}">
            <span class="paper-tag-pdf">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                    <polyline points="14 2 14 8 20 8"/>
                    <line x1="16" y1="13" x2="8" y2="13"/>
                    <line x1="16" y1="17" x2="8" y2="17"/>
                    <polyline points="10 9 9 9 8 9"/>
                </svg>
            </span>
            <span class="paper-tag-title" title="${escapeHtml(paper.title)}">${escapeHtml(paper.title)}</span>
            <button class="paper-tag-delete" data-index="${index}" title="Remove">×</button>
        </div>
    `).join('');

    // Attach delete handlers
    container.querySelectorAll('.paper-tag-delete').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const idx = parseInt(e.target.dataset.index);
            profilePapers.splice(idx, 1);
            renderPaperTags();
        });
    });
}

function initProfilePage() {
    // CV upload
    const cvInput = document.getElementById('cv-input');
    const cvBox = document.getElementById('cv-upload-box');
    if (cvInput) {
        cvInput.addEventListener('change', (e) => handleFileUpload(e.target.files[0], 'cv'));
    }
    setupDragDrop(cvBox, 'cv');

    // PS upload
    const psInput = document.getElementById('ps-input');
    const psBox = document.getElementById('ps-upload-box');
    if (psInput) {
        psInput.addEventListener('change', (e) => handleFileUpload(e.target.files[0], 'ps'));
    }
    setupDragDrop(psBox, 'ps');

    // Delete buttons
    document.getElementById('cv-delete')?.addEventListener('click', () => deleteFile('cv'));
    document.getElementById('ps-delete')?.addEventListener('click', () => deleteFile('ps'));

    // Paper input — Enter to add
    const paperInput = document.getElementById('paper-input');
    if (paperInput) {
        paperInput.addEventListener('keydown', async (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                const url = paperInput.value.trim();
                if (!url) return;
                // Check duplicate
                if (profilePapers.some(p => p.url === url)) {
                    showToast('This paper is already added', 'info');
                    paperInput.value = '';
                    return;
                }
                await addPaper(url);
                paperInput.value = '';
            }
        });
    }

    // Save button
    document.getElementById('save-profile-btn')?.addEventListener('click', saveProfile);
}

async function addPaper(url) {
    showToast('Fetching paper info from arXiv...', 'info', 2000);
    try {
        const response = await fetch('/api/arxiv/resolve', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url })
        });
        const data = await response.json();
        if (data.success) {
            profilePapers.push({
                url: data.url,
                title: data.title,
                arxiv_id: data.arxiv_id,
                pdf_url: data.pdf_url
            });
            renderPaperTags();
            showToast('Paper added', 'success');
        } else {
            showToast(data.error || 'Failed to resolve paper', 'error');
        }
    } catch (error) {
        showToast('Error: ' + error.message, 'error');
    }
}

function setupDragDrop(box, type) {
    if (!box) return;
    box.addEventListener('dragover', (e) => {
        e.preventDefault();
        box.classList.add('dragover');
    });
    box.addEventListener('dragleave', () => {
        box.classList.remove('dragover');
    });
    box.addEventListener('drop', (e) => {
        e.preventDefault();
        box.classList.remove('dragover');
        const file = e.dataTransfer.files[0];
        if (file) handleFileUpload(file, type);
    });
}

async function handleFileUpload(file, type) {
    if (!file) return;
    if (file.type !== 'application/pdf' && !file.name.endsWith('.pdf')) {
        showToast('Only PDF files are allowed', 'error');
        return;
    }

    const formData = new FormData();
    formData.append('file', file);
    formData.append('type', type);

    try {
        const response = await fetch('/api/profile/upload', {
            method: 'POST',
            body: formData
        });
        const data = await response.json();
        if (data.success) {
            showFileInfo(type, data.filename);
            showToast(`${type.toUpperCase()} uploaded successfully`, 'success');
        } else {
            showToast(data.error || 'Upload failed', 'error');
        }
    } catch (error) {
        showToast('Upload error: ' + error.message, 'error');
    }
}

async function deleteFile(type) {
    if (!confirm(`Remove ${type.toUpperCase()} file?`)) return;

    try {
        const response = await fetch(`/api/profile/upload?type=${type}`, {
            method: 'DELETE'
        });
        const data = await response.json();
        if (data.success) {
            hideFileInfo(type);
            showToast(`${type.toUpperCase()} removed`, 'info');
        } else {
            showToast(data.error || 'Delete failed', 'error');
        }
    } catch (error) {
        showToast('Delete error: ' + error.message, 'error');
    }
}

async function saveProfile() {
    const preferences = document.getElementById('profile-preferences')?.value || '';

    // paper_links now contains objects with url + title
    const paper_links = profilePapers.map(p => ({
        url: p.url,
        title: p.title,
        arxiv_id: p.arxiv_id,
        pdf_url: p.pdf_url
    }));

    try {
        const response = await fetch('/api/profile', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ paper_links, preferences })
        });
        const data = await response.json();
        if (data.success) {
            showToast('Profile saved successfully', 'success');
        } else {
            showToast('Save failed', 'error');
        }
    } catch (error) {
        showToast('Save error: ' + error.message, 'error');
    }
}

// Initialize profile page
initProfilePage();
loadProfile();

// ============ End Profile Page ============

// ============ Settings Modal ============

function openSettingsModal() {
    document.getElementById('settings-modal-overlay').classList.add('active');
    loadSettings();
}

function closeSettingsModal() {
    document.getElementById('settings-modal-overlay').classList.remove('active');
}

let userNickname = '';

async function loadSettings() {
    try {
        const response = await fetch('/api/hound-config');
        if (!response.ok) return;
        const config = await response.json();

        document.getElementById('setting-nickname').value = config.nickname || '';
        document.getElementById('setting-api-key').value = config.api_key || '';
        document.getElementById('setting-provider').value = config.provider || 'yunwu';
        document.getElementById('setting-model').value = config.model || 'deepseek-v3.2';
        document.getElementById('setting-url').value = config.url || 'https://yunwu.ai/v1';
        document.getElementById('setting-temperature').value = config.temperature ?? 0.6;
        document.getElementById('setting-max-tokens').value = config.max_tokens ?? 800;
        document.getElementById('setting-scoring-iterations').value = config.scoring_iterations ?? 3;
        userNickname = config.nickname || '';
    } catch (error) {
        console.error('Failed to load settings:', error);
    }
}

async function saveSettings() {
    const config = {
        nickname: document.getElementById('setting-nickname').value.trim(),
        api_key: document.getElementById('setting-api-key').value.trim(),
        provider: document.getElementById('setting-provider').value.trim(),
        model: document.getElementById('setting-model').value.trim(),
        url: document.getElementById('setting-url').value.trim(),
        temperature: parseFloat(document.getElementById('setting-temperature').value),
        max_tokens: parseInt(document.getElementById('setting-max-tokens').value),
        scoring_iterations: parseInt(document.getElementById('setting-scoring-iterations').value),
    };
    userNickname = config.nickname;

    if (!config.api_key) {
        showToast('API Key is required', 'error');
        return;
    }

    try {
        const response = await fetch('/api/hound-config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });
        const data = await response.json();
        if (data.success) {
            showToast('Settings saved successfully', 'success');
            closeSettingsModal();
        } else {
            showToast(data.error || 'Save failed', 'error');
        }
    } catch (error) {
        showToast('Save error: ' + error.message, 'error');
    }
}

// Settings event bindings
document.getElementById('settings-link')?.addEventListener('click', (e) => {
    e.preventDefault();
    openSettingsModal();
});

document.getElementById('settings-modal-close')?.addEventListener('click', closeSettingsModal);

document.getElementById('settings-modal-overlay')?.addEventListener('click', (e) => {
    if (e.target === document.getElementById('settings-modal-overlay')) closeSettingsModal();
});

document.getElementById('save-settings-btn')?.addEventListener('click', saveSettings);

document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && document.getElementById('settings-modal-overlay')?.classList.contains('active')) {
        closeSettingsModal();
    }
});

// ============ End Settings Modal ============

// Restore last active page after all definitions are loaded
restoreActivePage();
