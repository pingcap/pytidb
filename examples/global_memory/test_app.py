#!/usr/bin/env python3
"""
Simple test script to verify the core functionality of the TiDB Memory Chatbot
"""

import tempfile
import shutil
from datetime import datetime
from models import ChatSession, Message, SessionSummary
from session_manager import SessionManager
from llm_service import LLMService


def test_models():
    """Test data models"""
    print("Testing models...")

    # Test Message
    msg = Message("user", "Hello", datetime.now())
    msg_dict = msg.to_dict()
    msg_restored = Message.from_dict(msg_dict)
    assert msg.role == msg_restored.role
    assert msg.content == msg_restored.content
    print("✅ Message model works")

    # Test SessionSummary
    summary = SessionSummary(
        "test-123", "Test summary", 5, datetime.now(), datetime.now()
    )
    summary_dict = summary.to_dict()
    summary_restored = SessionSummary.from_dict(summary_dict)
    assert summary.session_id == summary_restored.session_id
    print("✅ SessionSummary model works")

    # Test ChatSession
    session = ChatSession("test-session", [], datetime.now(), True, True, [])
    session.add_message("user", "Test message")
    session_dict = session.to_dict()
    session_restored = ChatSession.from_dict(session_dict)
    assert len(session_restored.messages) == 1
    assert session_restored.messages[0].content == "Test message"
    print("✅ ChatSession model works")

    print("✅ All models working correctly!\n")


def test_session_manager():
    """Test session manager"""
    print("Testing session manager...")

    # Create temporary directory for testing
    temp_dir = tempfile.mkdtemp()

    try:
        # Create session manager with temporary storage
        session_manager = SessionManager(storage_path=temp_dir)

        # Test creating session
        session = session_manager.create_session(memory_enabled=True)
        assert session is not None
        assert session.memory_enabled
        print("✅ Session creation works")

        # Test adding messages and saving
        session.add_message("user", "Hello")
        session.add_message("assistant", "Hi there!")
        session_manager.save_session(session)
        print("✅ Session saving works")

        # Test loading session
        loaded_session = session_manager.load_session(session.session_id)
        assert loaded_session is not None
        assert len(loaded_session.messages) == 2
        print("✅ Session loading works")

        # Test session history
        history = session_manager.get_session_history()
        assert session.session_id in history
        print("✅ Session history works")

        print("✅ SessionManager working correctly!\n")

    finally:
        # Clean up temporary directory
        shutil.rmtree(temp_dir)


def test_llm_service():
    """Test LLM service (basic initialization only)"""
    print("Testing LLM service...")

    # Test initialization
    llm_service = LLMService()
    assert llm_service.model is not None
    print("✅ LLM service initialization works")

    # Test conversation formatting (without actual API calls)
    from models import ChatSession

    session = ChatSession("test", [], datetime.now(), True, False, [])
    session.add_message("user", "Hello")
    session.add_message("assistant", "Hi!")

    formatted = llm_service._format_conversation_for_summary(session.messages)
    assert "User: Hello" in formatted
    assert "Assistant: Hi!" in formatted
    print("✅ Conversation formatting works")

    print("✅ LLMService basic functionality working!\n")


def main():
    """Run all tests"""
    print("🧪 Running TiDB Memory Chatbot Tests\n")

    try:
        test_models()
        test_session_manager()
        test_llm_service()

        print("🎉 All tests passed! The application should work correctly.")
        print("\nNext steps:")
        print("1. Copy .env.example to .env")
        print("2. Configure your API keys in .env")
        print("3. Run: python main.py")

    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
