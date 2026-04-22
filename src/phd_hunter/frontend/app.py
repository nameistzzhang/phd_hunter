#!/usr/bin/env python3
"""Simple API server to serve professor data as JSON for frontend."""

import json
import sqlite3
from pathlib import Path
from flask import Flask, jsonify, render_template, request
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from phd_hunter.database import Database

app = Flask(__name__,
            template_folder=str(Path(__file__).parent),
            static_folder=str(Path(__file__).parent / 'static'))

DB_PATH = str(Path(__file__).parent.parent.parent.parent / "phd_hunter.db")


def get_db():
    """Get database connection."""
    db = Database(db_path=DB_PATH)
    return db.conn


@app.route('/')
def index():
    """Serve the main HTML page."""
    return render_template('index.html')


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


if __name__ == '__main__':
    print("Starting PhD Hunter Frontend Server...")
    print(f"Database: {DB_PATH}")
    print("Open browser to: http://localhost:5000")
    app.run(debug=True, port=5000)
