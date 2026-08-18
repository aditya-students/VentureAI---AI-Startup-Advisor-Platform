"""
Automated unit & integration tests for Mentor-Founder Chat System.
"""

import unittest
from fastapi import HTTPException

from app.chat.service import _sanitize_message_content
from app.chat.storage import ALLOWED_EXTENSIONS, MAX_FILE_SIZE_BYTES
from app.chat.models import ConversationStatus, MessageType


class ChatSystemTests(unittest.TestCase):

    def test_sanitize_message_content_valid(self):
        text = "Hello Mentor! Can you check my pricing model?\nThanks!"
        cleaned = _sanitize_message_content(text)
        self.assertEqual(cleaned, "Hello Mentor! Can you check my pricing model?\nThanks!")

    def test_sanitize_message_content_html_escaping(self):
        malicious = "<script>alert('xss')</script> Hello <b>World</b>"
        cleaned = _sanitize_message_content(malicious)
        self.assertNotIn("<script>", cleaned)
        self.assertIn("&lt;script&gt;", cleaned)

    def test_sanitize_message_content_empty_raises(self):
        with self.assertRaises(HTTPException) as ctx:
            _sanitize_message_content("   \n\t  ")
        self.assertEqual(ctx.exception.status_code, 422)

    def test_sanitize_message_content_over_length_raises(self):
        huge_text = "a" * 4001
        with self.assertRaises(HTTPException) as ctx:
            _sanitize_message_content(huge_text)
        self.assertEqual(ctx.exception.status_code, 422)

    def test_file_attachment_validation_constants(self):
        self.assertIn(".pdf", ALLOWED_EXTENSIONS)
        self.assertIn(".docx", ALLOWED_EXTENSIONS)
        self.assertIn(".png", ALLOWED_EXTENSIONS)
        self.assertEqual(MAX_FILE_SIZE_BYTES, 10 * 1024 * 1024)

    def test_conversation_status_enum(self):
        self.assertEqual(ConversationStatus.ACTIVE.value, "active")
        self.assertEqual(ConversationStatus.READ_ONLY.value, "read_only")
        self.assertEqual(ConversationStatus.ARCHIVED.value, "archived")

    def test_message_type_enum(self):
        self.assertEqual(MessageType.TEXT.value, "text")
        self.assertEqual(MessageType.FILE.value, "file")
        self.assertEqual(MessageType.SYSTEM.value, "system")


if __name__ == "__main__":
    unittest.main()
