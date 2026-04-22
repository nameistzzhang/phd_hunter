"""Database models and operations."""

import sqlite3
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path

from .models import Professor, University, ProfessorStatus


class Database:
    """SQLite database handler for PhD Hunter."""

    def __init__(self, db_path: str = "phd_hunter.db"):
        """Initialize database connection and create tables if needed.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.conn: Optional[sqlite3.Connection] = None
        self._connect()
        self._create_tables()

    def _connect(self):
        """Establish database connection."""
        self.conn = sqlite3.connect(str(self.db_path))
        # Enable foreign keys
        self.conn.execute("PRAGMA foreign_keys = ON")
        # Return rows as dictionaries
        self.conn.row_factory = sqlite3.Row

    def _create_tables(self):
        """Create database tables if they don't exist."""
        cursor = self.conn.cursor()

        # Professors table - university info denormalized as columns
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS professors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                -- University info (denormalized)
                university_name TEXT NOT NULL,
                university_rank INTEGER,
                university_score REAL,
                university_paper_count INTEGER,
                university_url TEXT,
                -- Professor details
                department TEXT,
                homepage TEXT,
                scholar_url TEXT,
                email TEXT,
                research_interests TEXT,  -- JSON array
                status TEXT DEFAULT 'unknown',
                priority INTEGER DEFAULT -1,  -- -1: not considered, 0-3: priority tiers
                total_papers INTEGER DEFAULT 0,
                recent_papers INTEGER DEFAULT 0,
                papers_per_year REAL DEFAULT 0.0,
                match_score REAL DEFAULT 0.0,
                research_alignment REAL DEFAULT 0.0,
                activity_score REAL DEFAULT 0.0,
                last_updated TIMESTAMP,
                source_urls TEXT,  -- JSON array
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(name, university_name)
            )
        """)

        # Papers table - stores individual paper records linked to professors
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS papers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                professor_id INTEGER NOT NULL,
                s2_paper_id TEXT UNIQUE,  -- Semantic Scholar paper ID
                title TEXT NOT NULL,
                abstract TEXT,
                year INTEGER,
                venue TEXT,
                doi TEXT,
                url TEXT,
                citation_count INTEGER DEFAULT 0,
                openaccess_pdf TEXT,
                local_pdf_path TEXT,
                publication_type TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (professor_id) REFERENCES professors(id) ON DELETE CASCADE
            )
        """)

        # Indexes for faster queries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_professors_university ON professors(university_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_professors_status ON professors(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_professors_match_score ON professors(match_score DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_professors_rank ON professors(university_rank)")

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_papers_professor ON papers(professor_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_papers_year ON papers(year DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_papers_s2_id ON papers(s2_paper_id)")

        # Apply migrations for existing databases
        self._migrate_tables()

        self.conn.commit()

    def _migrate_tables(self) -> None:
        """Apply migrations to existing tables."""
        cursor = self.conn.cursor()
        # Check if priority column exists in professors table
        cursor.execute("PRAGMA table_info(professors)")
        columns = [row["name"] for row in cursor.fetchall()]
        if "priority" not in columns:
            cursor.execute("ALTER TABLE professors ADD COLUMN priority INTEGER DEFAULT -1")
            self.conn.commit()
            print("[Migration] Added 'priority' column to professors table")

    def update_professor_priority(self, professor_id: int, priority: int) -> bool:
        """Update priority for a professor.

        Args:
            professor_id: Professor database ID
            priority: Priority value (-1, 0, 1, 2, 3)

        Returns:
            True if updated, False if professor not found
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE professors SET priority = ? WHERE id = ?",
            (priority, professor_id)
        )
        self.conn.commit()
        return cursor.rowcount > 0

    def get_professor_priority(self, professor_id: int) -> Optional[int]:
        """Get current priority of a professor."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT priority FROM professors WHERE id = ?", (professor_id,))
        row = cursor.fetchone()
        return row["priority"] if row else None

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()

    # --- Professor operations ---

    def upsert_professor(self, prof: Professor, university: University) -> int:
        """Insert or update a professor with denormalized university info.

        Args:
            prof: Professor object
            university: University object (info will be denormalized)

        Returns:
            Professor database ID
        """
        cursor = self.conn.cursor()

        import json
        research_interests_json = json.dumps(prof.research_interests) if prof.research_interests else "[]"
        source_urls_json = json.dumps(prof.source_urls) if prof.source_urls else "[]"

        try:
            cursor.execute("""
                INSERT INTO professors
                (name, university_name, university_rank, university_score,
                 university_paper_count, university_url, department, homepage,
                 scholar_url, email, research_interests, status, priority,
                 total_papers, recent_papers, papers_per_year, match_score,
                 research_alignment, activity_score, last_updated, source_urls)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                prof.name,
                university.name,
                university.rank,
                university.score,
                university.paper_count,
                university.cs_rankings_url,
                prof.department,
                prof.homepage,
                prof.scholar_url,
                prof.email,
                research_interests_json,
                prof.status.value if hasattr(prof.status, 'value') else str(prof.status),
                prof.priority,
                prof.total_papers,
                prof.recent_papers,
                prof.papers_per_year,
                prof.match_score,
                prof.research_alignment,
                prof.activity_score,
                prof.last_updated.isoformat() if prof.last_updated else None,
                source_urls_json,
            ))
            prof_id = cursor.lastrowid
        except sqlite3.IntegrityError:
            # Professor exists, update
            cursor.execute("""
                UPDATE professors
                SET university_rank = ?, university_score = ?, university_paper_count = ?,
                    university_url = ?, department = ?, homepage = ?, scholar_url = ?,
                    email = ?, research_interests = ?, status = ?, priority = ?,
                    total_papers = ?, recent_papers = ?, papers_per_year = ?,
                    match_score = ?, research_alignment = ?, activity_score = ?,
                    last_updated = ?, source_urls = ?
                WHERE university_name = ? AND name = ?
            """, (
                university.rank,
                university.score,
                university.paper_count,
                university.cs_rankings_url,
                prof.department,
                prof.homepage,
                prof.scholar_url,
                prof.email,
                research_interests_json,
                prof.status.value if hasattr(prof.status, 'value') else str(prof.status),
                prof.priority,
                prof.total_papers,
                prof.recent_papers,
                prof.papers_per_year,
                prof.match_score,
                prof.research_alignment,
                prof.activity_score,
                prof.last_updated.isoformat() if prof.last_updated else None,
                source_urls_json,
                university.name,
                prof.name,
            ))
            cursor.execute("SELECT id FROM professors WHERE university_name = ? AND name = ?",
                          (university.name, prof.name))
            prof_id = cursor.fetchone()["id"]

        self.conn.commit()
        return prof_id

    # --- Paper operations ---

    def upsert_paper(
        self,
        professor_id: int,
        paper_data: Dict[str, Any]
    ) -> int:
        """Insert or update a paper record.

        Args:
            professor_id: Foreign key to professor
            paper_data: Paper metadata dict with keys:
                - s2_paper_id: Semantic Scholar paper ID
                - title: Paper title
                - abstract: Paper abstract
                - year: Publication year
                - venue: Venue name
                - doi: DOI
                - url: Semantic Scholar URL
                - citation_count: Number of citations
                - openaccess_pdf: Open access PDF URL
                - local_pdf_path: Local downloaded PDF path
                - publication_type: Type of publication

        Returns:
            Paper database ID
        """
        cursor = self.conn.cursor()

        # Prepare values with proper types for SQLite
        def prepare(val):
            if val is None:
                return None
            if isinstance(val, (dict, list)):
                import json
                return json.dumps(val, ensure_ascii=False)
            return val

        try:
            cursor.execute("""
                INSERT INTO papers
                (professor_id, s2_paper_id, title, abstract, year, venue, doi,
                 url, citation_count, openaccess_pdf, local_pdf_path, publication_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                prepare(professor_id),
                prepare(paper_data.get('s2_paper_id') or paper_data.get('paper_id')),
                prepare(paper_data.get('title')),
                prepare(paper_data.get('abstract')),
                prepare(paper_data.get('year')),
                prepare(paper_data.get('venue')),
                prepare(paper_data.get('doi')),
                prepare(paper_data.get('url')),
                prepare(paper_data.get('citation_count', 0)),
                prepare(paper_data.get('openaccess_pdf')),
                prepare(paper_data.get('local_pdf_path')),
                prepare(paper_data.get('publication_type')),
            ))
            paper_id = cursor.lastrowid
        except sqlite3.IntegrityError:
            # Paper exists (by s2_paper_id), update
            s2_id = paper_data.get('s2_paper_id') or paper_data.get('paper_id')
            cursor.execute("""
                UPDATE papers
                SET title = ?, abstract = ?, year = ?, venue = ?, doi = ?,
                    url = ?, citation_count = ?, openaccess_pdf = ?,
                    local_pdf_path = ?, publication_type = ?
                WHERE s2_paper_id = ? AND professor_id = ?
            """, (
                prepare(paper_data.get('title')),
                prepare(paper_data.get('abstract')),
                prepare(paper_data.get('year')),
                prepare(paper_data.get('venue')),
                prepare(paper_data.get('doi')),
                prepare(paper_data.get('url')),
                prepare(paper_data.get('citation_count', 0)),
                prepare(paper_data.get('openaccess_pdf')),
                prepare(paper_data.get('local_pdf_path')),
                prepare(paper_data.get('publication_type')),
                prepare(s2_id),
                prepare(professor_id),
            ))
            cursor.execute("SELECT id FROM papers WHERE s2_paper_id = ? AND professor_id = ?",
                          (prepare(s2_id), prepare(professor_id)))
            paper_id = cursor.fetchone()["id"]

        self.conn.commit()
        return paper_id

    def get_papers_by_professor(
        self,
        professor_id: int,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get all papers for a professor."""
        cursor = self.conn.cursor()
        query = """
            SELECT * FROM papers
            WHERE professor_id = ?
            ORDER BY year DESC, created_at DESC
        """
        params = [professor_id]
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def get_professor_with_papers(
        self,
        professor_id: int
    ) -> Optional[Dict[str, Any]]:
        """Get professor with their papers."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM professors WHERE id = ?", (professor_id,))
        prof = cursor.fetchone()
        if not prof:
            return None

        prof_dict = dict(prof)
        papers = self.get_papers_by_professor(professor_id)
        prof_dict['papers'] = papers
        return prof_dict

    def update_professor_paper_stats(
        self,
        professor_id: int,
        total_papers: int,
        recent_papers: int
    ) -> None:
        """Update professor's paper statistics."""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE professors
            SET total_papers = ?, recent_papers = ?
            WHERE id = ?
        """, (total_papers, recent_papers, professor_id))
        self.conn.commit()

    def get_professor(self, prof_id: int) -> Optional[Dict[str, Any]]:
        """Get professor by ID."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM professors WHERE id = ?", (prof_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_professors_by_university(self, university_name: str) -> List[Dict[str, Any]]:
        """Get all professors for a given university name."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM professors
            WHERE university_name = ?
            ORDER BY match_score DESC
        """, (university_name,))
        return [dict(row) for row in cursor.fetchall()]

    def list_professors(self,
                       status: Optional[str] = None,
                       min_match_score: float = 0.0,
                       limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """List professors with optional filters.

        Args:
            status: Filter by status (accepting, not_accepting, unknown, conditional)
            min_match_score: Minimum match score
            limit: Maximum number of results

        Returns:
            List of professor records
        """
        cursor = self.conn.cursor()

        query = """
            SELECT * FROM professors
            WHERE match_score >= ?
        """
        params = [min_match_score]

        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY match_score DESC, university_rank ASC"

        if limit:
            query += " LIMIT ?"
            params.append(limit)

        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def get_professor_by_name(
        self,
        name: str,
        university_name: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get professor by name (optionally filtered by university)."""
        cursor = self.conn.cursor()
        if university_name:
            cursor.execute("""
                SELECT * FROM professors
                WHERE name = ? AND university_name = ?
            """, (name, university_name))
        else:
            cursor.execute("SELECT * FROM professors WHERE name = ?", (name,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def search_professors(self, keyword: str) -> List[Dict[str, Any]]:
        """Search professors by name, research interests, or department."""
        cursor = self.conn.cursor()
        pattern = f"%{keyword}%"
        cursor.execute("""
            SELECT * FROM professors
            WHERE name LIKE ?
               OR department LIKE ?
               OR research_interests LIKE ?
               OR university_name LIKE ?
            ORDER BY match_score DESC, university_rank ASC
        """, (pattern, pattern, pattern, pattern))
        return [dict(row) for row in cursor.fetchall()]

    def delete_professor(self, prof_id: int) -> bool:
        """Delete professor by ID."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM professors WHERE id = ?", (prof_id,))
        deleted = cursor.rowcount > 0
        self.conn.commit()
        return deleted

    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        cursor = self.conn.cursor()

        cursor.execute("SELECT COUNT(*) as count FROM professors")
        prof_count = cursor.fetchone()["count"]

        cursor.execute("SELECT COUNT(DISTINCT university_name) as count FROM professors")
        uni_count = cursor.fetchone()["count"]

        cursor.execute("SELECT COUNT(*) as count FROM papers")
        paper_count = cursor.fetchone()["count"]

        cursor.execute("""
            SELECT status, COUNT(*) as count
            FROM professors
            GROUP BY status
        """)
        status_counts = {row["status"]: row["count"] for row in cursor.fetchall()}

        cursor.execute("SELECT AVG(total_papers) as avg_papers FROM professors")
        avg_papers = cursor.fetchone()["avg_papers"] or 0

        cursor.execute("SELECT AVG(match_score) as avg_score FROM professors")
        avg_score = cursor.fetchone()["avg_score"] or 0

        # Count papers with local PDFs
        cursor.execute("SELECT COUNT(*) as count FROM papers WHERE local_pdf_path IS NOT NULL")
        pdf_count = cursor.fetchone()["count"]

        return {
            "universities": uni_count,
            "professors": prof_count,
            "papers": paper_count,
            "papers_with_pdf": pdf_count,
            "by_status": status_counts,
            "avg_papers": round(avg_papers, 1),
            "avg_match_score": round(avg_score, 1),
        }

    def export_to_json(self, output_path: str):
        """Export all data to JSON file.

        Args:
            output_path: Path to output JSON file
        """
        import json

        professors = self.list_professors()

        # Parse JSON fields and attach papers
        for prof in professors:
            if isinstance(prof.get("research_interests"), str):
                prof["research_interests"] = json.loads(prof["research_interests"])
            if isinstance(prof.get("source_urls"), str):
                prof["source_urls"] = json.loads(prof["source_urls"])

            # Get papers for this professor
            prof_id = prof['id']
            papers = self.get_papers_by_professor(prof_id)
            for paper in papers:
                if isinstance(paper.get("openaccess_pdf"), str):
                    paper["has_pdf"] = bool(paper["openaccess_pdf"])
            prof["papers"] = papers

        data = {
            "professors": professors,
            "count": len(professors),
            "exported_at": datetime.now().isoformat()
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
