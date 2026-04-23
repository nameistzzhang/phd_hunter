#!/usr/bin/env python3
"""Simple API server to serve professor data as JSON for frontend."""

import json
import sqlite3
import threading
import time
import sys
import traceback
from pathlib import Path
from flask import Flask, jsonify, render_template, request
from queue import Queue, Empty

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from phd_hunter.crawlers import CSRankingsCrawler, ArxivCrawler
from phd_hunter.database import Database
from phd_hunter.utils.logger import get_logger, setup_logger
from phd_hunter.models import Professor, University

app = Flask(__name__,
            template_folder=str(Path(__file__).parent),
            static_folder=str(Path(__file__).parent / 'static'))

DB_PATH = str(Path(__file__).parent.parent.parent.parent / "phd_hunter.db")
HUNT_CONFIG_PATH = str(Path(__file__).parent / "hunt_config.json")

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
    data = request.get_json()
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
    data = request.get_json()
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

        # ========== Phase 2: Fetch Papers ==========
        log_message("")
        log_message("=" * 70)
        log_message("Phase 2: 从 arXiv 获取教授论文")
        log_message("=" * 70)

        arxiv_crawler = ArxivCrawler(delay=10.0)

        try:
            # Get professors from database
            professors_from_db = db.list_professors(limit=max_professors * 10)

            if not professors_from_db:
                log_message("[WARN] 数据库中没有教授记录")
                with hunt_lock:
                    hunt_state['running'] = False
                return

            log_message(f"找到 {len(professors_from_db)} 位教授，开始获取论文...")

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

                # Fetch papers from arXiv
                papers = arxiv_crawler.fetch(
                    prof,
                    max_papers=max_papers,
                    download=False,
                    pdf_dir=None,
                )

                if papers:
                    # Filter out already-existing papers and invalid arxiv_id
                    new_papers = [p for p in papers if p.arxiv_id and p.arxiv_id not in existing_s2_ids]
                    skipped_papers = len(papers) - len(new_papers)

                    if skipped_papers > 0:
                        log_message(f"[SKIP] 跳过 {skipped_papers} 篇已存在的论文")
                        total_skipped += skipped_papers

                    if new_papers:
                        log_message(f"[OK] 找到 {len(new_papers)} 篇新论文")

                        # Save NEW papers to database only
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
                            total_papers += 1  # Increment for each successfully saved paper
                    else:
                        log_message(f"    [INFO] 所有论文都已存在，无需更新")
                else:
                    log_message(f"    [WARN] 未找到论文")

                # Update progress: number of professors processed so far
                with hunt_lock:
                    hunt_state['papers_completed'] = i

                # Small delay to avoid overwhelming
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
                arxiv_crawler.close()
                return

            log_message("")
            log_message("=" * 70)
            log_message(f"[OK] 完成！新增 {total_papers} 篇论文，跳过 {total_skipped} 篇已存在的论文")
            log_message("=" * 70)

        finally:
            arxiv_crawler.close()

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


if __name__ == '__main__':
    print("Starting PhD Hunter Frontend Server...")
    print(f"Database: {DB_PATH}")
    print("Open browser to: http://localhost:8080")
    app.run(debug=True, port=8081, use_reloader=False)  # Disable reloader to share global state
