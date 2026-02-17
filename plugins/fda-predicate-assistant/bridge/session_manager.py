"""
Session Manager - Conversation Context Persistence for FDA Bridge

Manages user sessions with:
1. In-memory LRU cache (max 1000 sessions)
2. Disk persistence (~/.claude/sessions/{session_id}.json)
3. Automatic cleanup (configurable expiry, default 24 hours)
4. Thread-safe operations

Author: FDA Tools Development Team
Date: 2026-02-16
Version: 1.0.0
"""

import os
import json
import uuid
import threading
from collections import OrderedDict
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta


@dataclass
class Session:
    """
    Represents a user session with conversation context.

    Attributes:
        session_id: Unique session identifier (UUID4)
        user_id: User identifier
        created_at: ISO 8601 creation timestamp
        last_accessed: ISO 8601 last access timestamp
        context: Conversation context (history, file paths, etc.)
        metadata: User preferences, configuration overrides, etc.
    """
    session_id: str
    user_id: str
    created_at: str
    last_accessed: str
    context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize session to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Session':
        """Deserialize session from dictionary."""
        return cls(
            session_id=data['session_id'],
            user_id=data['user_id'],
            created_at=data['created_at'],
            last_accessed=data['last_accessed'],
            context=data.get('context', {}),
            metadata=data.get('metadata', {})
        )

    def touch(self) -> None:
        """Update last_accessed timestamp."""
        self.last_accessed = datetime.now(timezone.utc).isoformat() + 'Z'

    def is_expired(self, max_age_hours: int = 24) -> bool:
        """Check if session has expired."""
        last_access = datetime.fromisoformat(
            self.last_accessed.rstrip('Z')
        ).replace(tzinfo=timezone.utc)
        age = datetime.now(timezone.utc) - last_access
        return age > timedelta(hours=max_age_hours)


class LRUSessionCache:
    """
    Thread-safe LRU cache for sessions with bounded capacity.

    Evicts least-recently-used sessions when capacity is reached.
    """

    def __init__(self, max_size: int = 1000):
        self._cache: OrderedDict[str, Session] = OrderedDict()
        self._max_size = max_size
        self._lock = threading.Lock()

    def get(self, session_id: str) -> Optional[Session]:
        """Get session, moving it to most-recent position."""
        with self._lock:
            if session_id in self._cache:
                self._cache.move_to_end(session_id)
                return self._cache[session_id]
        return None

    def put(self, session: Session) -> Optional[Session]:
        """
        Put session in cache, evicting LRU if at capacity.

        Returns:
            Evicted session if capacity was reached, None otherwise
        """
        evicted = None
        with self._lock:
            if session.session_id in self._cache:
                self._cache.move_to_end(session.session_id)
                self._cache[session.session_id] = session
            else:
                if len(self._cache) >= self._max_size:
                    # Evict least recently used
                    _, evicted = self._cache.popitem(last=False)
                self._cache[session.session_id] = session
        return evicted

    def remove(self, session_id: str) -> Optional[Session]:
        """Remove session from cache."""
        with self._lock:
            return self._cache.pop(session_id, None)

    def keys(self) -> List[str]:
        """Get all session IDs."""
        with self._lock:
            return list(self._cache.keys())

    def size(self) -> int:
        """Get current cache size."""
        with self._lock:
            return len(self._cache)

    def clear(self) -> None:
        """Clear all sessions."""
        with self._lock:
            self._cache.clear()


class SessionManager:
    """
    Manages conversation sessions with in-memory cache and disk persistence.

    Features:
    - In-memory LRU cache (max 1000 sessions)
    - JSON disk persistence in ~/.claude/sessions/
    - Automatic eviction persistence (evicted sessions saved to disk)
    - Configurable expiry (default 24 hours)
    - Thread-safe operations
    """

    def __init__(
        self,
        sessions_dir: Optional[str] = None,
        max_cache_size: int = 1000,
        max_age_hours: int = 24
    ):
        """
        Initialize session manager.

        Args:
            sessions_dir: Directory for session persistence
                         (default: ~/.claude/sessions/)
            max_cache_size: Maximum sessions in memory (default: 1000)
            max_age_hours: Session expiry in hours (default: 24)
        """
        if sessions_dir is None:
            sessions_dir = os.path.expanduser("~/.claude/sessions")

        self.sessions_dir = Path(sessions_dir)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.max_age_hours = max_age_hours

        self._cache = LRUSessionCache(max_size=max_cache_size)
        self._lock = threading.Lock()

    def create_session(self, user_id: str, session_id: Optional[str] = None) -> Session:
        """
        Create a new session for a user.

        Args:
            user_id: User identifier
            session_id: Optional predetermined session ID (generates UUID4 if None)

        Returns:
            Newly created Session object
        """
        now = datetime.now(timezone.utc).isoformat() + 'Z'

        session = Session(
            session_id=session_id or str(uuid.uuid4()),
            user_id=user_id,
            created_at=now,
            last_accessed=now,
            context={
                'conversation_history': [],
                'file_paths': [],
                'last_command': None,
                'command_count': 0
            },
            metadata={
                'created_by': 'bridge_server',
                'version': '1.0.0'
            }
        )

        # Store in cache (persist evicted sessions)
        evicted = self._cache.put(session)
        if evicted:
            self._persist_session(evicted)

        # Also persist new session to disk
        self._persist_session(session)

        return session

    def get_session(self, session_id: str) -> Optional[Session]:
        """
        Retrieve a session by ID.

        Checks in-memory cache first, falls back to disk.

        Args:
            session_id: Session identifier

        Returns:
            Session object or None if not found/expired
        """
        # Check cache first
        session = self._cache.get(session_id)

        if session is None:
            # Try disk
            session = self._restore_from_disk(session_id)
            if session is not None:
                # Re-cache restored session
                evicted = self._cache.put(session)
                if evicted:
                    self._persist_session(evicted)

        if session is None:
            return None

        # Check expiry
        if session.is_expired(self.max_age_hours):
            self._cache.remove(session_id)
            self._delete_from_disk(session_id)
            return None

        # Update access time
        session.touch()
        return session

    def get_or_create_session(
        self,
        user_id: str,
        session_id: Optional[str] = None
    ) -> Session:
        """
        Get existing session or create new one.

        Args:
            user_id: User identifier
            session_id: Optional session ID to look up

        Returns:
            Existing or newly created Session
        """
        if session_id:
            session = self.get_session(session_id)
            if session is not None:
                return session

        return self.create_session(user_id, session_id)

    def update_context(
        self,
        session_id: str,
        context: Dict[str, Any],
        merge: bool = True
    ) -> bool:
        """
        Update session context.

        Args:
            session_id: Session identifier
            context: New context data
            merge: If True, merge with existing context; if False, replace

        Returns:
            True if session found and updated, False otherwise
        """
        session = self.get_session(session_id)
        if session is None:
            return False

        if merge:
            session.context.update(context)
        else:
            session.context = context

        session.touch()
        self._persist_session(session)
        return True

    def add_to_conversation(
        self,
        session_id: str,
        role: str,
        content: str,
        command: Optional[str] = None
    ) -> bool:
        """
        Add an entry to the session's conversation history.

        Args:
            session_id: Session identifier
            role: Message role (user, assistant, system)
            content: Message content
            command: Optional command that generated this entry

        Returns:
            True if successful, False if session not found
        """
        session = self.get_session(session_id)
        if session is None:
            return False

        entry = {
            'role': role,
            'content': content,
            'timestamp': datetime.now(timezone.utc).isoformat() + 'Z'
        }
        if command:
            entry['command'] = command

        history = session.context.get('conversation_history', [])
        # Keep last 50 entries to prevent unbounded growth
        if len(history) >= 50:
            history = history[-49:]
        history.append(entry)
        session.context['conversation_history'] = history

        if command:
            session.context['last_command'] = command
            session.context['command_count'] = session.context.get('command_count', 0) + 1

        session.touch()
        self._persist_session(session)
        return True

    def add_file_path(self, session_id: str, file_path: str) -> bool:
        """
        Track a file path accessed during the session.

        Args:
            session_id: Session identifier
            file_path: File path to track

        Returns:
            True if successful, False if session not found
        """
        session = self.get_session(session_id)
        if session is None:
            return False

        file_paths = session.context.get('file_paths', [])
        if file_path not in file_paths:
            file_paths.append(file_path)
            # Keep last 200 paths
            if len(file_paths) > 200:
                file_paths = file_paths[-200:]
            session.context['file_paths'] = file_paths

        session.touch()
        self._persist_session(session)
        return True

    def cleanup_expired(self, max_age_hours: Optional[int] = None) -> int:
        """
        Remove expired sessions from cache and disk.

        Args:
            max_age_hours: Override default max age (optional)

        Returns:
            Number of sessions cleaned up
        """
        age = max_age_hours or self.max_age_hours
        cleaned = 0

        # Clean cache
        for session_id in self._cache.keys():
            session = self._cache.get(session_id)
            if session and session.is_expired(age):
                self._cache.remove(session_id)
                self._delete_from_disk(session_id)
                cleaned += 1

        # Clean disk (sessions not in cache)
        if self.sessions_dir.exists():
            for session_file in self.sessions_dir.glob("*.json"):
                try:
                    with open(session_file, 'r') as f:
                        data = json.load(f)
                    session = Session.from_dict(data)
                    if session.is_expired(age):
                        session_file.unlink()
                        cleaned += 1
                except (json.JSONDecodeError, KeyError, OSError):
                    # Corrupt session file -- remove it
                    try:
                        session_file.unlink()
                        cleaned += 1
                    except OSError:
                        pass

        return cleaned

    def list_sessions(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List active sessions, optionally filtered by user.

        Args:
            user_id: Optional user filter

        Returns:
            List of session summaries
        """
        sessions = []

        # Combine cache and disk sessions
        seen_ids = set()

        for session_id in self._cache.keys():
            session = self._cache.get(session_id)
            if session and not session.is_expired(self.max_age_hours):
                if user_id is None or session.user_id == user_id:
                    sessions.append({
                        'session_id': session.session_id,
                        'user_id': session.user_id,
                        'created_at': session.created_at,
                        'last_accessed': session.last_accessed,
                        'command_count': session.context.get('command_count', 0),
                        'source': 'cache'
                    })
                    seen_ids.add(session.session_id)

        # Check disk for sessions not in cache
        if self.sessions_dir.exists():
            for session_file in self.sessions_dir.glob("*.json"):
                sid = session_file.stem
                if sid in seen_ids:
                    continue
                try:
                    with open(session_file, 'r') as f:
                        data = json.load(f)
                    session = Session.from_dict(data)
                    if not session.is_expired(self.max_age_hours):
                        if user_id is None or session.user_id == user_id:
                            sessions.append({
                                'session_id': session.session_id,
                                'user_id': session.user_id,
                                'created_at': session.created_at,
                                'last_accessed': session.last_accessed,
                                'command_count': session.context.get('command_count', 0),
                                'source': 'disk'
                            })
                except (json.JSONDecodeError, KeyError, OSError):
                    pass

        return sessions

    def persist_to_disk(self, session_id: str) -> bool:
        """
        Force-persist a session to disk.

        Args:
            session_id: Session identifier

        Returns:
            True if persisted, False if session not found
        """
        session = self._cache.get(session_id)
        if session is None:
            return False
        self._persist_session(session)
        return True

    def restore_from_disk(self, session_id: str) -> Optional[Session]:
        """
        Restore a session from disk into cache.

        Args:
            session_id: Session identifier

        Returns:
            Restored Session or None if not found
        """
        session = self._restore_from_disk(session_id)
        if session is not None:
            evicted = self._cache.put(session)
            if evicted:
                self._persist_session(evicted)
        return session

    def _persist_session(self, session: Session) -> None:
        """Write session to disk."""
        session_file = self.sessions_dir / f"{session.session_id}.json"
        try:
            with open(session_file, 'w') as f:
                json.dump(session.to_dict(), f, indent=2, default=str)
        except OSError:
            pass

    def _restore_from_disk(self, session_id: str) -> Optional[Session]:
        """Read session from disk."""
        session_file = self.sessions_dir / f"{session_id}.json"
        if not session_file.exists():
            return None
        try:
            with open(session_file, 'r') as f:
                data = json.load(f)
            return Session.from_dict(data)
        except (json.JSONDecodeError, KeyError, OSError):
            return None

    def _delete_from_disk(self, session_id: str) -> None:
        """Remove session file from disk."""
        session_file = self.sessions_dir / f"{session_id}.json"
        try:
            if session_file.exists():
                session_file.unlink()
        except OSError:
            pass

    @property
    def cache_size(self) -> int:
        """Get current number of cached sessions."""
        return self._cache.size()


# Global singleton
_session_manager_instance: Optional[SessionManager] = None


def get_session_manager(
    sessions_dir: Optional[str] = None,
    max_cache_size: int = 1000,
    max_age_hours: int = 24
) -> SessionManager:
    """
    Get global SessionManager instance (singleton pattern).

    Args:
        sessions_dir: Optional sessions directory override
        max_cache_size: Maximum in-memory sessions
        max_age_hours: Session expiry in hours

    Returns:
        SessionManager instance
    """
    global _session_manager_instance
    if _session_manager_instance is None:
        _session_manager_instance = SessionManager(
            sessions_dir=sessions_dir,
            max_cache_size=max_cache_size,
            max_age_hours=max_age_hours
        )
    return _session_manager_instance
