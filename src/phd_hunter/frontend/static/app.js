// PhD Hunter Frontend - Light theme, English UI

let professors = [];
let selectedProfessor = null;

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

// Restore last active page after all definitions are loaded
restoreActivePage();
