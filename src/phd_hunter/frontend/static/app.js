// PhD Hunter Frontend - Light theme, English UI

let professors = [];
let selectedProfessor = null;

document.addEventListener('DOMContentLoaded', async () => {
    await loadStats();
    await loadProfessors();
    initFilters();
});

// Load statistics
async function loadStats() {
    try {
        const response = await fetch('/api/stats');
        const stats = await response.json();

        document.getElementById('stats').innerHTML = `
            <div class="stat"><span class="stat-value">${stats.universities}</span> Univ</div>
            <div class="stat"><span class="stat-value">${stats.professors}</span> Profs</div>
            <div class="stat"><span class="stat-value">${stats.papers}</span> Papers</div>
            <div class="stat"><span class="stat-value">${stats.avg_match_score}</span> Avg Score</div>
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
        <div class="professor-card" data-id="${prof.id}" onclick="openProfessor(${prof.id})">
            <div class="priority-strip priority-strip-${prof.priority === -1 ? 'neg1' : prof.priority}"></div>
            <div class="card-top">
                <div class="card-name-wrapper">
                    <div class="card-name">${escapeHtml(prof.name)}</div>
                    <select class="priority-select" data-id="${prof.id}" data-priority="${prof.priority}" onclick="event.stopPropagation()">
                        <option value="-1" ${prof.priority === -1 ? 'selected' : ''}>Not Considered</option>
                        <option value="0" ${prof.priority === 0 ? 'selected' : ''}>Reach</option>
                        <option value="1" ${prof.priority === 1 ? 'selected' : ''}>Good Match</option>
                        <option value="2" ${prof.priority === 2 ? 'selected' : ''}>Safe</option>
                        <option value="3" ${prof.priority === 3 ? 'selected' : ''}>Backup</option>
                    </select>
                </div>
                <div class="card-score">${prof.match_score?.toFixed(1) || 0}<small>pts</small></div>
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
                    <div class="info-label">Department</div>
                    <div class="info-value">${prof.department || 'Not provided'}</div>
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
            <div class="section-title">Metrics</div>
            <div class="metrics-grid">
                <div class="metric-box">
                    <div class="metric-label">Match Score</div>
                    <div class="metric-value">${prof.match_score?.toFixed(1) || 0}</div>
                </div>
                <div class="metric-box">
                    <div class="metric-label">Research Alignment</div>
                    <div class="metric-value">${prof.research_alignment?.toFixed(1) || 0}</div>
                </div>
                <div class="metric-box">
                    <div class="metric-label">Activity</div>
                    <div class="metric-value">${prof.activity_score?.toFixed(1) || 0}</div>
                </div>
                <div class="metric-box">
                    <div class="metric-label">Papers / Year</div>
                    <div class="metric-value">${(prof.papers_per_year || 0).toFixed(1)}</div>
                </div>
            </div>
        </div>

        <div class="section">
            <div class="section-title">Contact</div>
            <div class="info-grid">
                <div class="info-item">
                    <div class="info-label">Homepage</div>
                    <div class="info-value">${prof.homepage ? `<a href="${escapeHtml(prof.homepage)}" target="_blank" class="paper-link">Visit</a>` : 'Not provided'}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Email</div>
                    <div class="info-value">${prof.email || 'Not provided'}</div>
                </div>
            </div>
        </div>

        <div class="section">
            <div class="section-title">Papers (${(prof.papers || []).length})</div>
            ${prof.papers && prof.papers.length > 0
                ? prof.papers.map(paper => `
                    <div class="paper-item">
                        <div class="paper-title">${escapeHtml(paper.title)}</div>
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
    `;

    document.getElementById('modal-overlay').classList.add('active');
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
function sendMessage() {
    const input = document.getElementById('user-input');
    const message = input.value.trim();

    if (!message) return;

    addChatMessage(message, 'user');
    input.value = '';

    // Auto-reply
    setTimeout(() => {
        if (selectedProfessor) {
            addChatMessage(`Analyzing <strong>${selectedProfessor.name}</strong>...<br><br>This professor at <strong>${selectedProfessor.university_name}</strong> works on ${(selectedProfessor.research_interests || []).slice(0, 3).join(', ')}. Completed ${selectedProfessor.total_papers || 0} papers.`, 'assistant');
        } else {
            addChatMessage('Please select a professor from the list first.', 'assistant');
        }
    }, 300);
}

function addChatMessage(content, type) {
    const container = document.getElementById('chat-messages');
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${type}`;
    msgDiv.innerHTML = `<div class="message-content">${content}</div>`;
    container.appendChild(msgDiv);
    container.scrollTop = container.scrollHeight;
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
        alert('Failed to update priority. Please try again.');
    }
}

// Event bindings
document.getElementById('user-input').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendMessage();
});

document.getElementById('send-btn').addEventListener('click', sendMessage);
