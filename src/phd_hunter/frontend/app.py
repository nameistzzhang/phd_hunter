#!/usr/bin/env python3
"""Simple API server to serve professor data as JSON for frontend."""

import asyncio
import json
import os
import sqlite3
import threading
import time
import sys
import traceback
import uuid
from pathlib import Path
from flask import Flask, jsonify, render_template, request
from queue import Queue, Empty

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from phd_hunter.crawlers import CSRankingsCrawler, ArxivCrawler
from phd_hunter.database import Database
from phd_hunter.utils.logger import get_logger, setup_logger
from phd_hunter.models import Professor, University
from phd_hunter.hound.scorer_daemon import get_daemon, start_daemon, stop_daemon
from phd_hunter.analyzer import analyze_professor_first_time, chat_with_professor

import arxiv as arxiv_lib
import re

app = Flask(__name__,
            template_folder=str(Path(__file__).parent),
            static_folder=str(Path(__file__).parent / 'static'))

# --- arXiv URL helper ---
_ARXIV_ID_RE = re.compile(r"(\d{4}\.\d{4,5})")  # e.g. 2403.18814


def extract_arxiv_id(raw: str) -> str:
    """Extract arXiv ID from a URL or raw ID string.

    Supports:
      - Full URL: https://arxiv.org/abs/2403.18814
      - PDF URL:  https://arxiv.org/pdf/2403.18814.pdf
      - Plain ID: 2403.18814
      - arxiv:2403.18814
      - With extra whitespace

    Returns the bare arXiv ID or raises ValueError.
    """
    if not raw or not isinstance(raw, str):
        raise ValueError("Empty or non-string input")

    text = raw.strip()

    # Plain ID (no slashes)
    if "/" not in text and "." in text:
        m = _ARXIV_ID_RE.match(text)
        if m:
            return m.group(1)

    # Try URL parsing
    try:
        from urllib.parse import urlparse
        parsed = urlparse(text)
        path = parsed.path.strip("/")
        if path.startswith("abs/"):
            candidate = path.split("/", 1)[1]
        elif path.startswith("pdf/"):
            candidate = path.split("/", 1)[1].replace(".pdf", "")
        else:
            candidate = path.split("/")[-1].replace(".pdf", "")
        if candidate:
            m = _ARXIV_ID_RE.match(candidate)
            if m:
                return m.group(1)
    except Exception:
        pass

    # Last resort: search the whole string for an arXiv-like ID
    m = _ARXIV_ID_RE.search(text)
    if m:
        return m.group(1)

    raise ValueError(f"Could not extract arXiv ID from: {text}")


DB_PATH = str(Path(__file__).parent.parent.parent.parent / "phd_hunter_new.db")
HUNT_CONFIG_PATH = str(Path(__file__).parent / "hunt_config.json")
HOUND_CONFIG_PATH = str(Path(__file__).parent / "hound_config.json")
UPLOADS_DIR = Path(__file__).parent.parent.parent.parent / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)

# Default hunt configuration
DEFAULT_HUNT_CONFIG = {
    "areas": ["nlp"],
    "regions": ["asia"],
    "start_year": 2024,
    "end_year": 2026,
    "max_universities": 10,
    "max_professors": 5,
    "max_papers": 10,
    "stop_requested": False,
}

# Global hunt state
hunt_state = {
    'running': False,
    'phase': None,  # 'crawl' or 'papers'
    'professors_total': 0,
    'professors_completed': 0,
    'papers_total': 0,
    'papers_completed': 0,
    'logs': [],
    'error': None,
    'start_time': None,
}
hunt_lock = threading.RLock()
hunt_stop_event = threading.Event()
log_queue = Queue()

# Global reference to the currently running crawler (for force-stop)
_current_crawler = None
_current_crawler_lock = threading.Lock()

# Global logger for hunt operations
_hunt_logger = get_logger(__name__)


def _load_hunt_config():
    """Load hunt config from file, creating defaults if missing."""
    try:
        if Path(HUNT_CONFIG_PATH).exists():
            with open(HUNT_CONFIG_PATH, 'r', encoding='utf-8') as f:
                return {**DEFAULT_HUNT_CONFIG, **json.load(f)}
    except Exception as e:
        _hunt_logger.warning(f"Failed to load hunt config: {e}, using defaults")
    return DEFAULT_HUNT_CONFIG.copy()


def _save_hunt_config(config):
    """Save hunt config to file."""
    try:
        with open(HUNT_CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except Exception as e:
        _hunt_logger.error(f"Failed to save hunt config: {e}")


def log_message(msg: str) -> None:
    """Thread-safe logging to both logger and hunt_state logs."""
    _hunt_logger.info(msg)
    with hunt_lock:
        hunt_state['logs'].append(msg)
        if len(hunt_state['logs']) > 500:
            hunt_state['logs'] = hunt_state['logs'][-400:]


def get_db():
    """Get database connection."""
    db = Database(db_path=DB_PATH)
    return db.conn


@app.route('/')
def index():
    """Serve the main HTML page."""
    return render_template('index.html')


@app.route('/api/hunt-config')
def get_hunt_config():
    """Get current hunt configuration."""
    config = _load_hunt_config()
    # Don't expose stop_requested to frontend
    config.pop('stop_requested', None)
    return jsonify(config)


@app.route('/api/hunt-config', methods=['POST'])
def update_hunt_config():
    """Update hunt configuration."""
    data = request.get_json(silent=True) or {}
    config = _load_hunt_config()

    # Update allowed fields
    for key in ['areas', 'regions', 'start_year', 'end_year', 'max_universities', 'max_professors', 'max_papers']:
        if key in data:
            config[key] = data[key]

    _save_hunt_config(config)
    return jsonify({'success': True})


@app.route('/api/professors')
def get_professors():
    """Return all professors with their papers."""
    conn = get_db()
    cursor = conn.cursor()

    # Get all professors
    cursor.execute("SELECT * FROM professors ORDER BY match_score DESC")
    professors = [dict(row) for row in cursor.fetchall()]

    # Parse JSON fields and attach papers for each professor
    for prof in professors:
        # Parse research_interests JSON
        if isinstance(prof.get('research_interests'), str):
            try:
                prof['research_interests'] = json.loads(prof['research_interests'])
            except:
                prof['research_interests'] = []

        # Parse source_urls JSON
        if isinstance(prof.get('source_urls'), str):
            try:
                prof['source_urls'] = json.loads(prof['source_urls'])
            except:
                prof['source_urls'] = []

        # Get papers for this professor
        cursor.execute("""
            SELECT * FROM papers
            WHERE professor_id = ?
            ORDER BY year DESC, created_at DESC
        """, (prof['id'],))
        papers = [dict(row) for row in cursor.fetchall()]
        prof['papers'] = papers

    return jsonify({
        'professors': professors,
        'count': len(professors)
    })


@app.route('/api/stats')
def get_stats():
    """Return database statistics."""
    db = Database(db_path=DB_PATH)
    stats = db.get_stats()
    return jsonify(stats)


@app.route('/api/professor/<int:prof_id>')
def get_professor(prof_id):
    """Get single professor by ID."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM professors WHERE id = ?", (prof_id,))
    row = cursor.fetchone()
    if not row:
        return jsonify({'error': 'Professor not found'}), 404

    prof = dict(row)

    # Parse JSON fields
    if isinstance(prof.get('research_interests'), str):
        try:
            prof['research_interests'] = json.loads(prof['research_interests'])
        except:
            prof['research_interests'] = []

    # Get papers
    cursor.execute("""
        SELECT * FROM papers
        WHERE professor_id = ?
        ORDER BY year DESC
    """, (prof_id,))
    prof['papers'] = [dict(row) for row in cursor.fetchall()]

    return jsonify(prof)


@app.route('/api/professor/<int:prof_id>/priority', methods=['POST'])
def update_priority(prof_id):
    """Update professor priority."""
    data = request.get_json(silent=True) or {}
    priority = data.get('priority')

    if priority is None:
        return jsonify({'error': 'Priority is required'}), 400

    # Validate priority value
    if priority not in [-1, 0, 1, 2, 3]:
        return jsonify({'error': 'Invalid priority. Must be -1, 0, 1, 2, or 3'}), 400

    db = Database(db_path=DB_PATH)
    success = db.update_professor_priority(prof_id, priority)

    if success:
        return jsonify({'success': True, 'priority': priority})
    else:
        return jsonify({'error': 'Professor not found'}), 404


# ========== Professor Paper Management API ==========

@app.route('/api/professor/<int:prof_id>/rescore', methods=['POST'])
def rescore_professor(prof_id):
    """Re-score a professor using the LLM scorer.

    This clears existing scores and re-runs the scorer daemon logic.
    """
    db = Database(db_path=DB_PATH)
    prof = db.get_professor_hound_data(prof_id)
    if not prof:
        db.close()
        return jsonify({'error': 'Professor not found'}), 404

    try:
        # Clear existing scores
        db.update_professor_scores(
            professor_id=prof_id,
            direction_match=None,
            admission_difficulty=None,
            reasoning="",
        )
        db.close()

        # Re-run scorer
        from phd_hunter.hound.scorer import score_professor
        result = _run_async(score_professor(
            professor_id=prof_id,
            db_path=DB_PATH,
        ))

        if result:
            return jsonify({
                'success': True,
                'direction_match': result['direction_match'],
                'admission_difficulty': result['admission_difficulty'],
            })
        else:
            return jsonify({'error': 'Scoring failed. Please check profile and hound config.'}), 500
    except Exception as e:
        return jsonify({'error': f'Rescoring failed: {str(e)}'}), 500


@app.route('/api/professor/<int:prof_id>/paper', methods=['POST'])
def add_paper_to_professor(prof_id):
    """Add an arXiv paper to a professor by URL.

    Validates that the professor is in the author list before adding.
    """
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify({'error': 'Invalid request body'}), 400
    url = data.get('url', '')
    if isinstance(url, str):
        url = url.strip()

    if not url:
        return jsonify({'error': 'URL is required'}), 400

    try:
        arxiv_id = extract_arxiv_id(url)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

    db = Database(db_path=DB_PATH)
    prof = db.get_professor_hound_data(prof_id)
    if not prof:
        db.close()
        return jsonify({'error': 'Professor not found'}), 404

    try:
        search = arxiv_lib.Search(id_list=[arxiv_id])
        results = list(search.results())
        if not results:
            db.close()
            return jsonify({'error': 'Paper not found on arXiv'}), 404

        paper = results[0]
        authors = [a.name for a in paper.authors]

        # Validate professor is an author
        from phd_hunter.crawlers.arxiv_crawler import _is_author_match
        if not _is_author_match(prof['name'], authors):
            db.close()
            return jsonify({
                'error': 'Author verification failed',
                'detail': f"'{prof['name']}' was not found in the author list: {', '.join(authors[:5])}",
            }), 400

        paper_data = {
            's2_paper_id': arxiv_id,
            'title': paper.title,
            'abstract': paper.summary,
            'year': paper.published.year,
            'venue': None,
            'url': f'https://arxiv.org/abs/{arxiv_id}',
            'openaccess_pdf': paper.pdf_url,
            'citation_count': 0,
        }
        db.upsert_paper(prof_id, paper_data)

        # Refresh professor data to include the new paper
        updated_prof = db.get_professor_with_papers(prof_id)
        db.close()

        return jsonify({
            'success': True,
            'paper': {
                'id': updated_prof['papers'][0]['id'],
                'title': paper.title,
                'arxiv_id': arxiv_id,
            },
        })
    except Exception as e:
        db.close()
        return jsonify({'error': f'Failed to add paper: {str(e)}'}), 500


@app.route('/api/professor/<int:prof_id>/paper/<int:paper_id>', methods=['DELETE'])
def delete_paper(prof_id, paper_id):
    """Delete a paper from a professor."""
    db = Database(db_path=DB_PATH)
    success = db.delete_paper(paper_id)
    db.close()

    if success:
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'Paper not found'}), 404


# ========== Profile API ==========

@app.route('/api/profile', methods=['GET'])
def get_profile():
    """Get user profile."""
    db = Database(db_path=DB_PATH)
    profile = db.get_profile()
    if profile is None:
        return jsonify({
            'cv': None,
            'ps': None,
            'paper_links': [],
            'preferences': ''
        })

    return jsonify({
        'cv': {
            'filename': profile.get('cv_filename'),
            'uploaded_at': profile.get('cv_uploaded_at')
        } if profile.get('cv_filename') else None,
        'ps': {
            'filename': profile.get('ps_filename'),
            'uploaded_at': profile.get('ps_uploaded_at')
        } if profile.get('ps_filename') else None,
        'paper_links': profile.get('paper_links') or [],
        'preferences': profile.get('preferences') or ''
    })


@app.route('/api/profile', methods=['POST'])
def update_profile():
    """Update profile text fields."""
    data = request.get_json(silent=True) or {}
    db = Database(db_path=DB_PATH)

    paper_links = data.get('paper_links')
    preferences = data.get('preferences')

    db.update_profile(
        paper_links=paper_links,
        preferences=preferences
    )
    return jsonify({'success': True})


@app.route('/api/profile/upload', methods=['POST'])
def upload_profile_file():
    """Upload CV or PS PDF file."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    file_type = request.form.get('type')

    if not file or file.filename == '':
        return jsonify({'error': 'Empty file'}), 400

    if file_type not in ('cv', 'ps'):
        return jsonify({'error': 'Invalid type. Must be cv or ps'}), 400

    # Validate file extension
    ext = Path(file.filename).suffix.lower()
    if ext != '.pdf':
        return jsonify({'error': 'Only PDF files are allowed'}), 400

    # Save file with UUID
    stored_name = f"{uuid.uuid4().hex}{ext}"
    file_path = UPLOADS_DIR / stored_name
    file.save(str(file_path))

    # Update database
    db = Database(db_path=DB_PATH)
    db.update_profile_file(file_type, str(file_path), file.filename)

    return jsonify({
        'success': True,
        'filename': file.filename,
        'type': file_type
    })


@app.route('/api/profile/upload', methods=['DELETE'])
def delete_profile_file():
    """Delete CV or PS file."""
    file_type = request.args.get('type')
    if file_type not in ('cv', 'ps'):
        return jsonify({'error': 'Invalid type. Must be cv or ps'}), 400

    db = Database(db_path=DB_PATH)
    profile = db.get_profile()

    # Delete physical file
    if profile:
        path_key = f"{file_type}_path"
        file_path = profile.get(path_key)
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass  # Ignore delete errors

    db.delete_profile_file(file_type)
    return jsonify({'success': True})


# ========== arXiv Resolver API ==========

@app.route('/api/arxiv/resolve', methods=['POST'])
def resolve_arxiv():
    """Resolve an arXiv URL to paper metadata (title, PDF URL)."""
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify({'error': 'Invalid request body'}), 400
    url = data.get('url', '')
    if isinstance(url, str):
        url = url.strip()

    if not url:
        return jsonify({'error': 'URL is required'}), 400

    try:
        arxiv_id = extract_arxiv_id(url)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

    try:
        search = arxiv_lib.Search(id_list=[arxiv_id])
        results = list(search.results())
        if not results:
            return jsonify({'error': 'Paper not found on arXiv'}), 404

        paper = results[0]
        return jsonify({
            'success': True,
            'arxiv_id': arxiv_id,
            'title': paper.title,
            'url': f'https://arxiv.org/abs/{arxiv_id}',
            'pdf_url': paper.pdf_url,
            'authors': [a.name for a in paper.authors],
            'year': paper.published.year,
        })
    except Exception as e:
        return jsonify({'error': f'Failed to fetch from arXiv: {str(e)}'}), 500


# ========== End Profile API ==========


# ========== Hound Scorer Daemon API ==========

@app.route('/api/hound/status', methods=['GET'])
def hound_status():
    """Get scorer daemon status."""
    daemon = get_daemon(db_path=DB_PATH)
    return jsonify(daemon.get_status())


@app.route('/api/hound/start', methods=['POST'])
def hound_start():
    """Manually start the scorer daemon."""
    daemon = get_daemon(db_path=DB_PATH)
    daemon.start()
    return jsonify({'success': True, 'status': daemon.get_status()})


@app.route('/api/hound/stop', methods=['POST'])
def hound_stop():
    """Manually stop the scorer daemon."""
    daemon = get_daemon(db_path=DB_PATH)
    daemon.stop()
    return jsonify({'success': True, 'status': daemon.get_status()})


# ========== End Hound API ==========


# ========== Chat API ==========

def _run_async(coro):
    """Safely run an async coroutine in Flask's threaded environment.

    asyncio.run() can fail when Werkzeug reuses threads with stale event loops.
    We always create a fresh loop and clean it up afterward.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()
        asyncio.set_event_loop(None)


@app.route('/api/chat/<int:prof_id>', methods=['GET'])
def get_chat_messages(prof_id):
    """Get existing chat messages for a professor."""
    db = Database(db_path=DB_PATH)
    prof = db.get_professor_hound_data(prof_id)
    db.close()

    if not prof:
        return jsonify({'error': 'Professor not found'}), 404

    messages = prof.get('messages', [])
    if not messages or not isinstance(messages, list):
        messages = []

    # Hide system prompt and hidden/initial analysis prompts
    # (initial user prompt contains '=== APPLICANT PROFILE ===')
    visible_messages = []
    for m in messages:
        if m.get('role') == 'system':
            continue
        if m.get('hidden'):
            continue
        if m.get('role') == 'user' and '=== APPLICANT PROFILE ===' in m.get('content', ''):
            continue
        visible_messages.append(m)

    return jsonify({
        'messages': visible_messages,
        'professor_name': prof.get('name', ''),
        'university_name': prof.get('university_name', ''),
    })


@app.route('/api/chat/<int:prof_id>', methods=['POST'])
def post_chat_message(prof_id):
    """Handle chat actions for a professor.

    If request body has 'message' field: send user message and get assistant reply.
    If request body is empty or has no 'message': trigger first-time analysis.
    """
    data = request.get_json(silent=True) or {}
    user_message = data.get('message', '').strip()

    db = Database(db_path=DB_PATH)
    prof = db.get_professor_hound_data(prof_id)
    if not prof:
        db.close()
        return jsonify({'error': 'Professor not found'}), 404
    db.close()

    if user_message:
        # --- Continue existing chat ---
        try:
            response = _run_async(chat_with_professor(
                professor_id=prof_id,
                user_message=user_message,
                db_path=DB_PATH,
            ))
            if response is None:
                return jsonify({'error': 'Chat failed. Make sure first-time analysis has been run.'}), 500
            return jsonify({
                'success': True,
                'response': response,
                'message': user_message,
            })
        except Exception as e:
            return jsonify({'error': f'Chat failed: {str(e)}'}), 500
    else:
        # --- First-time analysis ---
        try:
            response = _run_async(analyze_professor_first_time(
                professor_id=prof_id,
                db_path=DB_PATH,
            ))
            if response is None:
                return jsonify({'error': 'Analysis failed. Please check profile and try again.'}), 500
            return jsonify({
                'success': True,
                'response': response,
            })
        except Exception as e:
            return jsonify({'error': f'Analysis failed: {str(e)}'}), 500


@app.route('/api/chat/<int:prof_id>/message', methods=['DELETE'])
def delete_chat_message(prof_id):
    """Delete a single visible message by its visible index."""
    data = request.get_json(silent=True) or {}
    visible_index = data.get('index')

    if visible_index is None:
        return jsonify({'error': 'Missing index'}), 400

    db = Database(db_path=DB_PATH)
    prof = db.get_professor_hound_data(prof_id)
    if not prof:
        db.close()
        return jsonify({'error': 'Professor not found'}), 404

    messages = prof.get('messages', [])
    if not messages or not isinstance(messages, list):
        db.close()
        return jsonify({'error': 'No messages'}), 400

    # Filter visible messages (same logic as GET)
    visible_messages = []
    for m in messages:
        if m.get('role') == 'system':
            continue
        if m.get('hidden'):
            continue
        if m.get('role') == 'user' and '=== APPLICANT PROFILE ===' in m.get('content', ''):
            continue
        visible_messages.append(m)

    if visible_index < 0 or visible_index >= len(visible_messages):
        db.close()
        return jsonify({'error': 'Invalid index'}), 400

    target = visible_messages[visible_index]

    # Remove from original messages by matching role + content
    for i, m in enumerate(messages):
        if m.get('role') == target.get('role') and m.get('content') == target.get('content'):
            messages.pop(i)
            break

    db.update_professor_messages(prof_id, messages)
    db.close()

    return jsonify({'success': True})


# ========== End Chat API ==========


# ========== Hound Config API ==========

# Default hound config values
DEFAULT_HOUND_CONFIG = {
    "api_key": "",
    "model": "deepseek-v3.2",
    "provider": "yunwu",
    "url": "https://yunwu.ai/v1",
    "temperature": 0.6,
    "max_tokens": 800,
    "scoring_iterations": 3,
    "nickname": "",
}


def _load_hound_config():
    """Load hound config from JSON file, creating defaults if missing."""
    try:
        if Path(HOUND_CONFIG_PATH).exists():
            with open(HOUND_CONFIG_PATH, 'r', encoding='utf-8') as f:
                return {**DEFAULT_HOUND_CONFIG, **json.load(f)}
    except Exception as e:
        _hunt_logger.warning(f"Failed to load hound config: {e}, using defaults")
    return DEFAULT_HOUND_CONFIG.copy()


def _save_hound_config(config):
    """Save hound config to JSON file."""
    try:
        with open(HOUND_CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except Exception as e:
        _hunt_logger.error(f"Failed to save hound config: {e}")


@app.route('/api/hound-config', methods=['GET'])
def get_hound_config_api():
    """Get current hound configuration (LLM settings)."""
    config = _load_hound_config()
    # Mask API key for safety
    display_config = config.copy()
    if display_config.get('api_key'):
        key = display_config['api_key']
        display_config['api_key'] = key[:4] + '*' * (len(key) - 8) + key[-4:]
    return jsonify(display_config)


@app.route('/api/hound-config', methods=['POST'])
def update_hound_config_api():
    """Update hound configuration (LLM settings)."""
    data = request.get_json(silent=True) or {}
    config = _load_hound_config()

    # Update allowed fields
    if 'api_key' in data:
        config['api_key'] = data['api_key']
    if 'model' in data:
        config['model'] = data['model']
    if 'provider' in data:
        config['provider'] = data['provider']
    if 'url' in data:
        config['url'] = data['url']
    if 'temperature' in data:
        config['temperature'] = float(data['temperature'])
    if 'max_tokens' in data:
        config['max_tokens'] = int(data['max_tokens'])
    if 'scoring_iterations' in data:
        config['scoring_iterations'] = int(data['scoring_iterations'])
    if 'nickname' in data:
        config['nickname'] = data['nickname']

    _save_hound_config(config)
    return jsonify({'success': True})


# ========== End Hound Config API ==========


@app.route('/api/stop-hunt', methods=['POST'])
def stop_hunt():
    """Stop the currently running hunt."""
    global hunt_stop_event

    with hunt_lock:
        if not hunt_state['running']:
            return jsonify({'success': False, 'message': 'No hunt is currently running'}), 400

        # Set stop flag in config
        config = _load_hunt_config()
        config['stop_requested'] = True
        _save_hunt_config(config)

        # Signal the worker to stop
        hunt_stop_event.set()
        log_message("[INFO] Stop requested by user...")

        # IMMEDIATELY reset running state so Start can work again right away
        hunt_state['running'] = False
        hunt_state['phase'] = None

    return jsonify({'success': True, 'message': 'Hunt stopped'})


@app.route('/api/start-hunt', methods=['POST'])
def start_hunt():
    """Start background crawling job."""
    global hunt_state

    with hunt_lock:
        if hunt_state['running']:
            return jsonify({'error': 'Hunt already running'}), 400

        # Load config from file (already saved by frontend POST /api/hunt-config)
        config = _load_hunt_config()

        # Reset stop flag
        config['stop_requested'] = False
        _save_hunt_config(config)

        # Validate
        if not config.get('areas'):
            return jsonify({'error': 'At least one research area is required'}), 400
        if not config.get('regions'):
            return jsonify({'error': 'At least one region is required'}), 400

        # Reset state
        hunt_state = {
            'running': True,
            'phase': 'crawl',
            'professors_total': 0,
            'professors_completed': 0,
            'papers_total': 0,
            'papers_completed': 0,
            'logs': [],
            'error': None,
            'start_time': time.time(),
        }

        # Clear log queue
        while not log_queue.empty():
            try:
                log_queue.get_nowait()
            except Empty:
                break

        # Start background thread (no args — worker reads config from file)
        t = threading.Thread(
            target=run_hunt_worker,
            daemon=True
        )
        t.start()

        return jsonify({'success': True, 'message': 'Hunt started'})


@app.route('/api/hunt-status')
def get_hunt_status():
    """Get current hunt progress."""
    with hunt_lock:
        return jsonify({
            'running': hunt_state['running'],
            'phase': hunt_state['phase'],
            'professors_total': hunt_state['professors_total'],
            'professors_completed': hunt_state['professors_completed'],
            'papers_total': hunt_state['papers_total'],
            'papers_completed': hunt_state['papers_completed'],
            'logs': hunt_state['logs'][-50:],  # Last 50 log lines
            'error': hunt_state['error'],
        })


def run_hunt_worker():
    """Background worker that runs the crawling pipeline.

    Reads all configuration from hunt_config.json (no arguments).
    """
    global hunt_state

    # Setup logging
    import logging
    import time
    logger = get_logger(__name__)

    # Read configuration from file
    config = _load_hunt_config()
    areas = config.get('areas', [])
    regions = config.get('regions', [])
    start_year = config.get('start_year', 2024)
    end_year = config.get('end_year', 2026)
    max_universities = config.get('max_universities', 10)
    max_papers = config.get('max_papers', 10)
    max_professors = config.get('max_professors', 5)

    try:
        # Clear any previous stop request
        hunt_stop_event.clear()

        # ========== Phase 1: Crawl Professors ==========
        log_message("=" * 70)
        log_message("Phase 1: 从 CSRankings 爬取教授信息")
        log_message("=" * 70)
        log_message(f"Areas: {', '.join(areas)}")
        log_message(f"Regions: {', '.join(regions)}")
        log_message(f"Max professors per university: {max_professors}")
        log_message("")

        db = Database(db_path=DB_PATH)

        # Build area filter
        area_filter = areas[0] if len(areas) == 1 else None

        from phd_hunter.crawlers.csrankings import CrawlerInterrupted

        def crawl_progress(current, total, phase):
            """Progress callback from CSRankingsCrawler."""
            with hunt_lock:
                hunt_state['professors_total'] = total
                hunt_state['professors_completed'] = current

        # Remember existing professor IDs BEFORE crawl so we can identify new ones
        existing_profs_before = db.list_professors(limit=10000)
        existing_ids_before = {p['id'] for p in existing_profs_before}
        log_message(f"[INFO] Existing professors in DB before crawl: {len(existing_ids_before)}")

        crawler = CSRankingsCrawler(
            headless=True,
            timeout=10,
            verbose=False,
            db_path=DB_PATH,
            stop_event=hunt_stop_event,
            progress_callback=crawl_progress,
        )

        with _current_crawler_lock:
            global _current_crawler
            _current_crawler = crawler

        try:
            # Initial indeterminate state — crawler callback will update it
            with hunt_lock:
                hunt_state['professors_total'] = -1
                hunt_state['professors_completed'] = 0

            result = crawler.fetch(
                areas=[area_filter] if area_filter else None,
                region=regions[0] if len(regions) == 1 else None,
                include_professors=True,
                max_universities=max_universities,
                max_professors=max_professors,
            )

            universities, professors = result

            # ========== DE-DUPLICATION: Skip existing professors ==========
            log_message("Checking for existing professors...")
            existing_profs = db.list_professors(limit=10000)  # Get all professors
            existing_names = {(p['name'], p['university_name']) for p in existing_profs}

            new_professors = []
            skipped_count = 0
            for prof in professors:
                key = (prof.name, prof.university)
                if key in existing_names:
                    skipped_count += 1
                    logger.debug(f"  [SKIP] {prof.name} ({prof.university}) - already in database")
                else:
                    new_professors.append(prof)

            log_message(f"[INFO] Found {len(professors)} total professors from CSRankings")
            log_message(f"[INFO] Skipping {skipped_count} existing professors")
            log_message(f"[INFO] New professors to save: {len(new_professors)}")

            with hunt_lock:
                hunt_state['professors_total'] = len(new_professors)
                hunt_state['professors_completed'] = 0

            # Save NEW professors to database only
            log_message(f"Saving {len(new_professors)} new professors to database...")
            uni_by_name = {uni.name: uni for uni in universities}
            saved_count = 0
            for i, prof in enumerate(new_professors, 1):
                # Check for stop request
                if hunt_stop_event.is_set():
                    log_message("[INFO] Stop requested during professor saving. Exiting...")
                    with hunt_lock:
                        hunt_state['running'] = False
                        hunt_state['phase'] = None
                    return

                uni = uni_by_name.get(prof.university)
                if not uni:
                    uni = University(
                        name=prof.university,
                        rank=0,
                        score=0.0,
                        paper_count=0,
                        cs_rankings_url="",
                    )
                db.upsert_professor(prof, uni)
                saved_count += 1

                # Update progress incrementally
                with hunt_lock:
                    hunt_state['professors_completed'] = i

                # Small delay to avoid overwhelming database
                time.sleep(0.05)

            log_message(f"[OK] Saved {saved_count} new professors to database")

        finally:
            crawler.close()
            with _current_crawler_lock:
                _current_crawler = None

        # Identify NEWLY ADDED professor IDs for Phase 2
        all_profs_after = db.list_professors(limit=10000)
        new_professor_ids = [p['id'] for p in all_profs_after if p['id'] not in existing_ids_before]
        log_message(f"[INFO] New professor IDs for paper fetch: {len(new_professor_ids)}")

        # ========== Phase 2: Fetch Papers via OpenAlex ==========
        log_message("")
        log_message("=" * 70)
        log_message("Phase 2: 从 OpenAlex 获取教授论文")
        log_message("=" * 70)

        from phd_hunter.crawlers import OpenAlexCrawler
        openalex_crawler = OpenAlexCrawler(delay=1.0)

        try:
            # Only fetch papers for NEWLY ADDED professors in this hunt
            if not new_professor_ids:
                log_message("[INFO] No new professors to fetch papers for.")
                with hunt_lock:
                    hunt_state['running'] = False
                    hunt_state['phase'] = None
                return

            professors_from_db = []
            for pid in new_professor_ids:
                prof = db.get_professor_hound_data(pid)
                if prof:
                    professors_from_db.append(prof)

            log_message(f"找到 {len(professors_from_db)} 位新教授，开始获取论文...")

            if not professors_from_db:
                log_message("[WARN] 数据库中没有教授记录")
                with hunt_lock:
                    hunt_state['running'] = False
                return

            # Pre-fetch existing papers for ALL professors (batch)
            log_message("Checking for existing papers...")
            existing_papers_by_prof = {}
            for prof_dict in professors_from_db:
                pid = prof_dict['id']
                existing = db.get_papers_by_professor(pid)
                existing_papers_by_prof[pid] = {p['s2_paper_id'] for p in existing if p['s2_paper_id']}

            total_existing = sum(len(v) for v in existing_papers_by_prof.values())
            log_message(f"[INFO] Found {total_existing} existing papers in database")

            with hunt_lock:
                hunt_state['phase'] = 'papers'
                hunt_state['papers_total'] = len(professors_from_db)
                hunt_state['papers_completed'] = 0

            total_papers = 0
            total_skipped = 0

            for i, prof_dict in enumerate(professors_from_db, 1):
                # Check for stop request
                if hunt_stop_event.is_set():
                    log_message("[INFO] Stop requested during paper fetching. Exiting...")
                    with hunt_lock:
                        hunt_state['running'] = False
                        hunt_state['phase'] = None
                    break

                prof_name = prof_dict['name']
                prof_id = prof_dict['id']
                existing_s2_ids = existing_papers_by_prof.get(prof_id, set())

                log_message(f"[{i}/{len(professors_from_db)}] {prof_name}")

                # Reconstruct Professor object
                from phd_hunter.models import Professor
                prof = Professor(
                    id=prof_id,
                    name=prof_name,
                    university=prof_dict['university_name'],
                )

                # --- Fetch papers via OpenAlex ---
                log_message(f"  [OpenAlex] Searching {prof_name} @ {prof.university}...")
                try:
                    papers = openalex_crawler.fetch(prof, max_papers=max_papers)
                except Exception as e:
                    log_message(f"  [OpenAlex] Error: {e}")
                    papers = []

                if papers:
                    # Filter out already-existing papers
                    new_papers = [p for p in papers if p.arxiv_id and p.arxiv_id not in existing_s2_ids]
                    skipped_papers = len(papers) - len(new_papers)

                    if skipped_papers > 0:
                        log_message(f"[SKIP] 跳过 {skipped_papers} 篇已存在的论文")
                        total_skipped += skipped_papers

                    if new_papers:
                        log_message(f"[OK] 找到 {len(new_papers)} 篇新论文")

                        # Save NEW papers to database
                        for paper in new_papers:
                            paper_data = {
                                's2_paper_id': paper.arxiv_id,
                                'title': paper.title,
                                'abstract': paper.abstract,
                                'year': paper.year,
                                'venue': paper.venue,
                                'url': paper.url,
                                'openaccess_pdf': paper.pdf_url,
                                'local_pdf_path': paper.pdf_path,
                            }
                            db.upsert_paper(prof_id, paper_data)
                            total_papers += 1

                        # --- Enrich abstracts from arXiv ---
                        arxiv_ids = [p.arxiv_id for p in new_papers if p.arxiv_id]
                        if arxiv_ids:
                            log_message(f"  [arXiv] Enriching {len(arxiv_ids)} abstracts...")
                            try:
                                arxiv_crawler = ArxivCrawler(delay=3.0)
                                arxiv_results = arxiv_crawler.fetch_by_ids(arxiv_ids)
                                updated_count = 0
                                for paper in new_papers:
                                    if paper.arxiv_id and paper.arxiv_id in arxiv_results:
                                        arxiv_paper = arxiv_results[paper.arxiv_id]
                                        # Update if arXiv abstract is better (longer or OpenAlex was empty)
                                        if (arxiv_paper.abstract and
                                            len(arxiv_paper.abstract) > len(paper.abstract or '')):
                                            db.update_paper_by_arxiv_id(
                                                prof_id, paper.arxiv_id,
                                                {
                                                    'abstract': arxiv_paper.abstract,
                                                    'openaccess_pdf': arxiv_paper.pdf_url,
                                                }
                                            )
                                            updated_count += 1
                                log_message(f"  [arXiv] Updated {updated_count} abstracts")
                                arxiv_crawler.close()
                            except Exception as e:
                                log_message(f"  [arXiv] Enrichment error: {e}")
                    else:
                        log_message(f"    [INFO] 所有论文都已存在，无需更新")
                else:
                    log_message(f"    [WARN] 未找到论文")

                # Update progress
                with hunt_lock:
                    hunt_state['papers_completed'] = i

                # Small delay between professors
                time.sleep(0.5)

            # Check if stopped
            if hunt_stop_event.is_set():
                log_message("")
                log_message("=" * 70)
                log_message(f"[INFO] Hunt stopped by user. Progress: {total_papers} new papers, {total_skipped} skipped")
                log_message("=" * 70)
                with hunt_lock:
                    hunt_state['running'] = False
                    hunt_state['phase'] = None
                openalex_crawler.close()
                return

            log_message("")
            log_message("=" * 70)
            log_message(f"[OK] 完成！新增 {total_papers} 篇论文，跳过 {total_skipped} 篇已存在的论文")
            log_message("=" * 70)

        finally:
            openalex_crawler.close()

        with hunt_lock:
            hunt_state['running'] = False
            hunt_state['phase'] = None

        log_message("\n[OK] 所有任务完成！")

    except CrawlerInterrupted:
        log_message("[INFO] Crawler stopped by user request.")
        with hunt_lock:
            hunt_state['running'] = False
            hunt_state['phase'] = None

    except Exception as e:
        with hunt_lock:
            hunt_state['running'] = False
            # If stop was requested, this is expected (driver was force-closed)
            # Don't record it as an error
            if hunt_stop_event.is_set():
                hunt_state['phase'] = None
                hunt_state['error'] = None
                log_message("[INFO] Crawler force-stopped by user.")
            else:
                hunt_state['error'] = str(e)
                log_message(f"\n[ERROR] {traceback.format_exc()}")


# Auto-start scorer daemon when app module is loaded (with delay to avoid reloader dup)
def _delayed_start_daemon():
    try:
        start_daemon(db_path=DB_PATH)
    except Exception as e:
        _hunt_logger.warning(f"Failed to auto-start scorer daemon: {e}")

# Only auto-start if not inside Werkzeug reloader child process
if os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
    threading.Timer(2.0, _delayed_start_daemon).start()


if __name__ == '__main__':
    print("Starting PhD Hunter Frontend Server...")
    print(f"Database: {DB_PATH}")
    print("Open browser to: http://localhost:8080")

    # Start scorer daemon in background
    start_daemon(db_path=DB_PATH)

    app.run(debug=True, port=8082, use_reloader=False)  # Disable reloader to share global state
