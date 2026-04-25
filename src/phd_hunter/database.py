"""Database models and operations."""

import json
import sqlite3
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path

from .models import Professor, University, ProfessorStatus
from .utils.logger import get_logger

logger = get_logger(__name__)


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

        # Migrate papers table if it exists with old schema (must happen before CREATE)
        self._migrate_papers_table_if_needed()

        # Papers table - stores individual paper records linked to professors
        # NOTE: s2_paper_id is NOT globally unique; a paper can belong to multiple professors.
        #       The uniqueness constraint is on (professor_id, s2_paper_id) to prevent duplicates per professor.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS papers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                professor_id INTEGER NOT NULL,
                s2_paper_id TEXT NOT NULL,
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
                FOREIGN KEY (professor_id) REFERENCES professors(id) ON DELETE CASCADE,
                UNIQUE(professor_id, s2_paper_id)
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

        # Profile table - single-row singleton (id=1) storing user profile data
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS profiles (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                cv_path TEXT,
                cv_filename TEXT,
                cv_uploaded_at TEXT,
                ps_path TEXT,
                ps_filename TEXT,
                ps_uploaded_at TEXT,
                paper_links TEXT,
                preferences TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Apply migrations for existing databases
        self._migrate_tables()

        self.conn.commit()

    def _migrate_tables(self) -> None:
        """Apply migrations to existing tables."""
        cursor = self.conn.cursor()
        cursor.execute("PRAGMA table_info(professors)")
        columns = [row["name"] for row in cursor.fetchall()]

        # Migration: priority column
        if "priority" not in columns:
            cursor.execute("ALTER TABLE professors ADD COLUMN priority INTEGER DEFAULT -1")
            self.conn.commit()
            print("[Migration] Added 'priority' column to professors table")

        # Migration: hound scoring fields
        hound_fields = {
            "direction_match_score": "INTEGER",
            "admission_difficulty_score": "INTEGER",
            "homepage_url": "TEXT",
            "messages": "TEXT",  # JSON array of API messages
            "analyzed_at": "TEXT",
            "homepage_summary": "TEXT",
            "homepage_fetched_at": "TEXT",
            "homepage_fetch_status": "TEXT DEFAULT 'pending'",
            "homepage_fetch_error": "TEXT",
        }
        for field, sql_type in hound_fields.items():
            if field not in columns:
                cursor.execute(f"ALTER TABLE professors ADD COLUMN {field} {sql_type}")
                self.conn.commit()
                print(f"[Migration] Added '{field}' column to professors table")

    def _migrate_papers_table_if_needed(self) -> None:
        """Check if papers table needs migration from old schema (UNIQUE on s2_paper_id)
        to new schema (UNIQUE(professor_id, s2_paper_id)). If migration needed, rebuild table."""
        cursor = self.conn.cursor()

        # Check if papers table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='papers'")
        if not cursor.fetchone():
            return  # Table doesn't exist yet; will be created fresh with new schema

        # Detect old schema: look for a UNIQUE index on s2_paper_id only (single-column unique)
        # Use PRAGMA index_list to get all indexes and their uniqueness
        cursor.execute("PRAGMA index_list('papers')")
        indexes = cursor.fetchall()  # each row: seq, name, unique, origin, partial
        has_s2_unique = False
        for idx in indexes:
            idx_name = idx['name']
            is_unique = bool(idx['unique'])
            if not is_unique:
                continue
            # Get columns for this unique index
            cursor.execute(f"PRAGMA index_info('{idx_name}')")
            cols = [row['name'] for row in cursor.fetchall()]
            # Old schema: single-column unique index on s2_paper_id
            if len(cols) == 1 and cols[0] == 's2_paper_id':
                has_s2_unique = True
                break
            # Also catch case where it's a unique index that includes s2_paper_id but not professor_id?
            # But the new schema's unique constraint on (professor_id, s2_paper_id) will have 2 columns.
            # So any unique index that does NOT contain professor_id and contains s2_paper_id could be old.
            # However, we only expect single-column s2_paper_id unique in old.
        if has_s2_unique:
            print("[Migration] Detected old unique index on s2_paper_id. Migrating papers table to composite unique...")
            self._rebuild_papers_table()

    def _rebuild_papers_table(self) -> None:
        """Rebuild papers table with composite unique constraint, preserving existing data."""
        cursor = self.conn.cursor()
        try:
            # 1. Rename old table
            cursor.execute("ALTER TABLE papers RENAME TO papers_old")

            # 2. Create new papers table with correct schema
            cursor.execute("""
                CREATE TABLE papers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    professor_id INTEGER NOT NULL,
                    s2_paper_id TEXT NOT NULL,
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
                    FOREIGN KEY (professor_id) REFERENCES professors(id) ON DELETE CASCADE,
                    UNIQUE(professor_id, s2_paper_id)
                )
            """)

            # 3. Copy data from old table (skip rows with NULL s2_paper_id to satisfy NOT NULL)
            cursor.execute("""
                INSERT INTO papers
                (id, professor_id, s2_paper_id, title, abstract, year, venue, doi, url, citation_count, openaccess_pdf, local_pdf_path, publication_type, created_at)
                SELECT id, professor_id, s2_paper_id, title, abstract, year, venue, doi, url, citation_count, openaccess_pdf, local_pdf_path, publication_type, created_at
                FROM papers_old
                WHERE s2_paper_id IS NOT NULL
            """)
            copied = cursor.rowcount

            # 4. Drop old table
            cursor.execute("DROP TABLE papers_old")

            self.conn.commit()
            print(f"[Migration] Papers table rebuilt successfully. Copied {copied} rows.")
        except Exception as e:
            # If anything fails, try to recover
            print(f"[Migration] Error during papers table migration: {e}")
            # Attempt to restore: if papers_old exists and papers exists, drop new and rename back
            try:
                cursor.execute("DROP TABLE papers")
            except:
                pass
            try:
                cursor.execute("ALTER TABLE papers_old RENAME TO papers")
                self.conn.commit()
                print("[Migration] Rolled back to old table.")
            except Exception as e2:
                print(f"[Migration] Rollback failed: {e2}")
            raise

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

    # --- Profile operations ---

    def get_profile(self) -> Optional[Dict[str, Any]]:
        """Get user profile (singleton, id=1).

        Returns:
            Profile dict or None if not set up yet.
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM profiles WHERE id = 1")
        row = cursor.fetchone()
        if not row:
            return None
        prof = dict(row)
        # Parse JSON fields
        if isinstance(prof.get("paper_links"), str):
            try:
                prof["paper_links"] = json.loads(prof["paper_links"])
            except Exception:
                prof["paper_links"] = []
        return prof

    def update_profile(self, paper_links: Optional[List[str]] = None,
                       preferences: Optional[str] = None) -> None:
        """Update profile text fields (paper_links + preferences).

        Creates the singleton row if it doesn't exist.
        """
        cursor = self.conn.cursor()
        import json
        paper_links_json = json.dumps(paper_links) if paper_links is not None else None

        cursor.execute("SELECT id FROM profiles WHERE id = 1")
        exists = cursor.fetchone()
        if exists:
            # Build dynamic UPDATE
            fields = []
            values = []
            if paper_links_json is not None:
                fields.append("paper_links = ?")
                values.append(paper_links_json)
            if preferences is not None:
                fields.append("preferences = ?")
                values.append(preferences)
            if fields:
                fields.append("updated_at = CURRENT_TIMESTAMP")
                query = f"UPDATE profiles SET {', '.join(fields)} WHERE id = 1"
                cursor.execute(query, values)
                self.conn.commit()
        else:
            cursor.execute("""
                INSERT INTO profiles (id, paper_links, preferences)
                VALUES (1, ?, ?)
            """, (paper_links_json, preferences))
            self.conn.commit()

    def update_profile_file(self, file_type: str, file_path: str,
                            filename: str) -> None:
        """Update CV or PS file info in profile.

        Args:
            file_type: 'cv' or 'ps'
            file_path: Absolute or relative path to stored file
            filename: Original uploaded filename
        """
        cursor = self.conn.cursor()
        from datetime import datetime
        uploaded_at = datetime.now().isoformat()

        cursor.execute("SELECT id FROM profiles WHERE id = 1")
        exists = cursor.fetchone()

        if file_type == "cv":
            cols = "cv_path = ?, cv_filename = ?, cv_uploaded_at = ?"
            vals = (file_path, filename, uploaded_at)
        elif file_type == "ps":
            cols = "ps_path = ?, ps_filename = ?, ps_uploaded_at = ?"
            vals = (file_path, filename, uploaded_at)
        else:
            raise ValueError(f"Invalid file_type: {file_type}")

        if exists:
            cursor.execute(f"UPDATE profiles SET {cols}, updated_at = CURRENT_TIMESTAMP WHERE id = 1", vals)
        else:
            if file_type == "cv":
                cursor.execute("""
                    INSERT INTO profiles (id, cv_path, cv_filename, cv_uploaded_at)
                    VALUES (1, ?, ?, ?)
                """, vals)
            else:
                cursor.execute("""
                    INSERT INTO profiles (id, ps_path, ps_filename, ps_uploaded_at)
                    VALUES (1, ?, ?, ?)
                """, vals)
        self.conn.commit()

    def delete_profile_file(self, file_type: str) -> None:
        """Remove CV or PS file info from profile.

        Args:
            file_type: 'cv' or 'ps'
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM profiles WHERE id = 1")
        exists = cursor.fetchone()
        if not exists:
            return

        if file_type == "cv":
            cols = "cv_path = NULL, cv_filename = NULL, cv_uploaded_at = NULL"
        elif file_type == "ps":
            cols = "ps_path = NULL, ps_filename = NULL, ps_uploaded_at = NULL"
        else:
            raise ValueError(f"Invalid file_type: {file_type}")

        cursor.execute(f"UPDATE profiles SET {cols}, updated_at = CURRENT_TIMESTAMP WHERE id = 1")
        self.conn.commit()

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
            # Paper exists (by (professor_id, s2_paper_id) unique constraint), update
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
            # Fetch the ID of the existing/updated row
            cursor.execute("SELECT id FROM papers WHERE s2_paper_id = ? AND professor_id = ?",
                          (prepare(s2_id), prepare(professor_id)))
            row = cursor.fetchone()
            if row is None:
                # This should not happen: the row should exist after UPDATE on unique constraint
                # Log error and raise to avoid crash
                logger.error(f"Failed to locate paper after UPDATE: professor_id={professor_id}, s2_paper_id={s2_id}")
                raise ValueError(f"Paper not found after upsert: professor={professor_id}, paper={s2_id}")
            paper_id = row["id"]

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

    # --- Hound Scorer operations ---

    def update_professor_scores(
        self,
        professor_id: int,
        direction_match: int,
        admission_difficulty: int,
        reasoning: str = "",
    ) -> None:
        """Update hound scoring results for a professor.

        Args:
            professor_id: Professor database ID
            direction_match: Direction match score (1-5)
            admission_difficulty: Admission difficulty score (1-5)
            reasoning: Optional reasoning text from LLM
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE professors
            SET direction_match_score = ?,
                admission_difficulty_score = ?,
                analyzed_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (direction_match, admission_difficulty, professor_id))
        self.conn.commit()

    def update_professor_homepage(
        self,
        professor_id: int,
        summary: str,
        email: Optional[str] = None,
        status: str = "success",
        error_msg: str = "",
    ) -> None:
        """Update homepage summary and related fields for a professor.

        Args:
            professor_id: Professor database ID
            summary: LLM-generated homepage summary
            email: Extracted email (if found, updates only if not empty)
            status: fetch status - 'success', 'failed', or 'dead'
            error_msg: Error message if failed
        """
        cursor = self.conn.cursor()
        updates = [
            "homepage_summary = ?",
            "homepage_fetched_at = CURRENT_TIMESTAMP",
            "homepage_fetch_status = ?",
        ]
        params = [summary, status]

        if email and email.strip():
            updates.append("email = ?")
            params.append(email.strip())

        if error_msg:
            updates.append("homepage_fetch_error = ?")
            params.append(error_msg)

        params.append(professor_id)

        cursor.execute(
            f"UPDATE professors SET {', '.join(updates)} WHERE id = ?",
            tuple(params),
        )
        self.conn.commit()

    def get_professor_hound_data(self, professor_id: int) -> Optional[Dict[str, Any]]:
        """Get professor data needed for hound scoring (with papers).

        Returns:
            Professor dict with 'papers' key containing paper records,
            or None if not found.
        """
        prof = self.get_professor_with_papers(professor_id)
        if not prof:
            return None

        # Parse research_interests
        if isinstance(prof.get("research_interests"), str):
            try:
                prof["research_interests"] = json.loads(prof["research_interests"])
            except Exception:
                prof["research_interests"] = []

        # Parse messages
        if isinstance(prof.get("messages"), str):
            try:
                prof["messages"] = json.loads(prof["messages"])
            except Exception:
                prof["messages"] = []

        return prof

    def update_professor_messages(
        self,
        professor_id: int,
        messages: List[Dict[str, str]],
    ) -> None:
        """Update conversation messages for a professor.

        Args:
            professor_id: Professor database ID
            messages: List of API message dicts [{role, content}, ...]
        """
        cursor = self.conn.cursor()
        messages_json = json.dumps(messages, ensure_ascii=False)
        cursor.execute(
            "UPDATE professors SET messages = ? WHERE id = ?",
            (messages_json, professor_id),
        )
        self.conn.commit()

    def list_professors_for_scoring(
        self,
        limit: Optional[int] = None,
        unscored_only: bool = False,
    ) -> List[Dict[str, Any]]:
        """List professors that need scoring.

        Args:
            limit: Max number of professors
            unscored_only: If True, only return professors without scores

        Returns:
            List of professor records (minimal fields)
        """
        cursor = self.conn.cursor()
        query = """
            SELECT p.id, p.name, p.university_name, p.university_rank,
                   p.research_interests, p.total_papers, p.recent_papers
            FROM professors p
            WHERE (SELECT COUNT(*) FROM papers WHERE professor_id = p.id) >= 3
        """
        if unscored_only:
            query += " AND p.direction_match_score IS NULL"
        query += " ORDER BY p.university_rank ASC, (SELECT COUNT(*) FROM papers WHERE professor_id = p.id) DESC"
        if limit:
            query += " LIMIT ?"
            cursor.execute(query, (limit,))
        else:
            cursor.execute(query)
        return [dict(row) for row in cursor.fetchall()]

    # --- End Hound operations ---

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

        cursor.execute("SELECT AVG(direction_match_score) as avg_direction FROM professors WHERE direction_match_score IS NOT NULL")
        avg_direction = cursor.fetchone()["avg_direction"] or 0

        cursor.execute("SELECT AVG(admission_difficulty_score) as avg_difficulty FROM professors WHERE admission_difficulty_score IS NOT NULL")
        avg_difficulty = cursor.fetchone()["avg_difficulty"] or 0

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
            "avg_direction_match": round(avg_direction, 1),
            "avg_admission_difficulty": round(avg_difficulty, 1),
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
