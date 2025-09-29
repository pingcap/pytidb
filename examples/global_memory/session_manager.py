import json
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
import logging
from models import ChatSession, SessionSummary, Message
from llm_service import LLMService
from db_models import TiDBConnection, ChatSessionDB, SessionSummaryDB

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SessionManager:
    def __init__(self, llm_service: LLMService = None):
        self.llm_service = llm_service or LLMService()
        self.db_conn = TiDBConnection()

        logger.info("SessionManager initialized with TiDB connection")

    def create_session(self, memory_enabled: bool = True) -> ChatSession:
        """Create a new chat session"""
        session_id = str(uuid.uuid4())[:8]  # Short UUID for readability
        previous_summaries = []

        # Load previous summaries if memory is enabled
        if memory_enabled:
            previous_summaries = self._load_all_summaries()

        session = ChatSession(
            session_id=session_id,
            messages=[],
            start_time=datetime.now(),
            is_active=True,
            memory_enabled=memory_enabled,
            previous_summaries=previous_summaries,
        )

        logger.info(
            f"Created new session {session_id} with memory_enabled={memory_enabled}"
        )
        return session

    def save_session(self, session: ChatSession) -> None:
        """Save session to TiDB"""
        try:
            # Convert session data to JSON strings
            messages_json = json.dumps([msg.to_dict() for msg in session.messages])
            previous_summaries_json = json.dumps(
                [summary.to_dict() for summary in session.previous_summaries]
            )

            session_data = ChatSessionDB(
                session_id=session.session_id,
                start_time=session.start_time,
                is_active=session.is_active,
                memory_enabled=session.memory_enabled,
                messages=messages_json,
                previous_summaries=previous_summaries_json,
            )

            # Use upsert (insert or update)
            self.db_conn.sessions_table.save(session_data)

            logger.info(f"Session {session.session_id} saved successfully")

        except Exception as e:
            logger.error(f"Error saving session {session.session_id}: {str(e)}")
            raise

    def load_session(self, session_id: str) -> Optional[ChatSession]:
        """Load a session from TiDB"""
        try:
            results = self.db_conn.sessions_table.query(
                filters={"session_id": session_id}
            ).to_pydantic()

            if results:
                session_data = results[0]

                # Parse JSON strings back to objects
                messages_data = json.loads(session_data.messages)
                previous_summaries_data = json.loads(session_data.previous_summaries)

                # Convert to original format
                messages = [Message.from_dict(msg) for msg in messages_data]
                previous_summaries = [
                    SessionSummary.from_dict(summary)
                    for summary in previous_summaries_data
                ]

                session = ChatSession(
                    session_id=session_data.session_id,
                    messages=messages,
                    start_time=session_data.start_time,
                    is_active=session_data.is_active,
                    memory_enabled=session_data.memory_enabled,
                    previous_summaries=previous_summaries,
                )

                logger.info(f"Session {session_id} loaded successfully")
                return session
            else:
                logger.warning(f"Session {session_id} not found")
                return None

        except Exception as e:
            logger.error(f"Error loading session {session_id}: {str(e)}")
            return None

    def close_session(self, session: ChatSession) -> Optional[SessionSummary]:
        """Close a session and generate summary"""
        try:
            # Mark session as inactive
            session.is_active = False

            # Generate summary
            summary_text = self.llm_service.generate_session_summary_sync(session)

            # Create summary object
            session_summary = SessionSummary(
                session_id=session.session_id,
                summary=summary_text,
                message_count=len(session.messages),
                start_time=session.start_time,
                end_time=datetime.now(),
            )

            # Save summary to storage (always, regardless of memory setting)
            self._save_summary(session_summary)

            # Save updated session
            self.save_session(session)

            logger.info(f"Session {session.session_id} closed and summarized")
            return session_summary

        except Exception as e:
            logger.error(f"Error closing session {session.session_id}: {str(e)}")
            return None

    def get_session_history(self) -> List[str]:
        """Get list of all session IDs"""
        try:
            results = self.db_conn.sessions_table.query().to_pydantic()
            return [session.session_id for session in results]
        except Exception:
            return []

    def get_active_sessions(self) -> List[ChatSession]:
        """Get all currently active sessions"""
        try:
            results = self.db_conn.sessions_table.query(
                filters={"is_active": True}
            ).to_pydantic()
            active_sessions = []

            for session_data in results:
                # Parse JSON strings back to objects
                messages_data = json.loads(session_data.messages)
                previous_summaries_data = json.loads(session_data.previous_summaries)

                messages = [Message.from_dict(msg) for msg in messages_data]
                previous_summaries = [
                    SessionSummary.from_dict(summary)
                    for summary in previous_summaries_data
                ]

                session = ChatSession(
                    session_id=session_data.session_id,
                    messages=messages,
                    start_time=session_data.start_time,
                    is_active=session_data.is_active,
                    memory_enabled=session_data.memory_enabled,
                    previous_summaries=previous_summaries,
                )

                active_sessions.append(session)

            return active_sessions

        except Exception as e:
            logger.error(f"Error getting active sessions: {str(e)}")
            return []

    def delete_session(self, session_id: str) -> bool:
        """Delete a session from TiDB"""
        try:
            rows_deleted = self.db_conn.sessions_table.delete(
                filters={"session_id": session_id}
            )

            if rows_deleted > 0:
                logger.info(f"Session {session_id} deleted")
                return True
            else:
                logger.warning(f"Session {session_id} not found for deletion")
                return False

        except Exception as e:
            logger.error(f"Error deleting session {session_id}: {str(e)}")
            return False

    def get_session_summaries(self) -> List[SessionSummary]:
        """Get all session summaries"""
        return self._load_all_summaries()

    def _save_summary(self, summary: SessionSummary) -> None:
        """Save a session summary to TiDB"""
        try:
            summary_data = SessionSummaryDB(
                session_id=summary.session_id,
                summary=summary.summary,
                message_count=summary.message_count,
                start_time=summary.start_time,
                end_time=summary.end_time,
            )

            # Use upsert (insert or update)
            self.db_conn.summaries_table.save(summary_data)

            logger.info(f"Summary for session {summary.session_id} saved")

        except Exception as e:
            logger.error(f"Error saving summary: {str(e)}")
            raise

    def _load_all_summaries(self) -> List[SessionSummary]:
        """Load all session summaries from TiDB"""
        try:
            results = self.db_conn.summaries_table.query().to_pydantic()
            summaries = []

            for summary_data in results:
                summary = SessionSummary(
                    session_id=summary_data.session_id,
                    summary=summary_data.summary,
                    message_count=summary_data.message_count,
                    start_time=summary_data.start_time,
                    end_time=summary_data.end_time,
                )
                summaries.append(summary)

            # Sort by end_time (most recent first)
            summaries.sort(key=lambda x: x.end_time, reverse=True)
            return summaries

        except Exception as e:
            logger.error(f"Error loading all summaries: {str(e)}")
            return []

    def cleanup_old_sessions(self, keep_count: int = 50) -> None:
        """Clean up old sessions, keeping only the most recent ones"""
        try:
            # Get all sessions ordered by start_time
            all_sessions = self.db_conn.sessions_table.query().to_pydantic()

            if len(all_sessions) <= keep_count:
                return

            # Sort sessions by start_time (most recent first)
            all_sessions.sort(key=lambda x: x.start_time, reverse=True)

            # Get sessions to delete (everything after keep_count)
            sessions_to_delete = all_sessions[keep_count:]

            # Delete old sessions and their summaries
            for session in sessions_to_delete:
                self.db_conn.sessions_table.delete(
                    filters={"session_id": session.session_id}
                )
                self.db_conn.summaries_table.delete(
                    filters={"session_id": session.session_id}
                )

            logger.info(f"Cleaned up {len(sessions_to_delete)} old sessions")

        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")

    def get_storage_stats(self) -> Dict[str, Any]:
        """Get statistics about stored sessions"""
        try:
            # Get session count
            total_sessions = self.db_conn.sessions_table.rows()

            # Get active sessions count
            active_sessions = len(
                self.db_conn.sessions_table.query(
                    filters={"is_active": True}
                ).to_pydantic()
            )

            # Get summaries count
            total_summaries = self.db_conn.summaries_table.rows()

            # Count total messages (requires loading all sessions)
            all_sessions = self.db_conn.sessions_table.query().to_pydantic()
            total_messages = 0
            for session in all_sessions:
                messages_data = json.loads(session.messages)
                total_messages += len(messages_data)

            return {
                "total_sessions": total_sessions,
                "active_sessions": active_sessions,
                "total_summaries": total_summaries,
                "total_messages": total_messages,
                "storage_type": "TiDB Cloud",
            }

        except Exception as e:
            logger.error(f"Error getting storage stats: {str(e)}")
            return {}
