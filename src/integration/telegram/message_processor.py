"""
Telegram Message Processor for Native IQ
Converts Telegram messages to Observer Agent input format
"""

from datetime import datetime
from typing import Dict, Any, Optional
from telegram import Update
import logging


logger = logging.getLogger(__name__)


class TelegramMessageProcessor:
    """Processes Telegram messages for Observer Agent consumption"""
    
    def __init__(self):
        self.processed_count = 0
    
    def process_telegram_message(self, update: Update) -> Optional[Dict[str, Any]]:
        """
        Convert Telegram update to Observer Agent input format
        
        Args:
            update: Telegram update object
            
        Returns:
            Dict with input_data and context for Observer Agent
        """
        try:
            if not update.message or not update.message.text:
                return None
            
            message = update.message
            user = update.effective_user
            chat = update.effective_chat

            # extract message content
            content = message.text
            
            # build context information
            context = {
                "message_type": "telegram",
                "platform": "telegram",
                "sender": self._get_sender_info(user),
                "chat_info": self._get_chat_info(chat),
                "timestamp": message.date.isoformat() if message.date else datetime.now().isoformat(),
                "message_id": message.message_id,
                "reply_to": self._get_reply_info(message),
                "forwarded": hasattr(message, 'forward_origin') and message.forward_origin is not None,
                "edited": message.edit_date is not None,
                "priority": self._determine_priority(content, user, chat),
                "frequency": "unknown",  # could be enhanced with user history
                "language": user.language_code if user else "unknown"
            }
            
            # create input data for observer agent
            input_data = {
                "message": content,
                "metadata": {
                    "source": "telegram",
                    "processed_at": datetime.now().isoformat(),
                    "content_length": len(content),
                    "has_mentions": "@" in content,
                    "has_hashtags": "#" in content,
                    "has_urls": "http" in content.lower() or "www." in content.lower(),
                    "word_count": len(content.split()),
                    "character_count": len(content)
                }
            }
            
            self.processed_count += 1
            
            logger.info(f"Processed Telegram message {self.processed_count} from {user.first_name}")
            
            return {
                "input_data": input_data,
                "context": context
            }
            
        except Exception as e:
            logger.error(f"Error processing Telegram message: {e}")
            return None

    def _get_sender_info(self, user) -> Dict[str, Any]:
        """Extract sender information"""
        
        return {
            "user_id": user.id,
            "first_name": user.first_name or "Unknown",
            "last_name": user.last_name or "",
            "username": user.username or "",
            "is_bot": user.is_bot,
            "language_code": user.language_code or "unknown"
        }
    
    def _get_chat_info(self, chat) -> Dict[str, Any]:
        """Extract chat information"""
        
        return {
            "chat_id": chat.id,
            "chat_type": chat.type,
            "title": chat.title or "",
            "username": chat.username or "",
            "description": chat.description if hasattr(chat, "description") else ""
        }
    
    def _get_reply_info(self, message) -> Optional[Dict[str, Any]]:
        """Extract reply information if message is a reply"""
        
        if message.reply_to_message:
            return {
                "reply_to_message_id": message.reply_to_message.message_id,
                "reply_to_user": message.reply_to_message.from_user.first_name if message.reply_to_message.from_user else "Unknown",
                "reply_to_text": message.reply_to_message.text[:100] if message.reply_to_message.text else ""
            }
        return None
    
    def _determine_priority(self, content: str, user, chat) -> str:
        """Determine message priority based on content and context"""
        
        content_lower = content.lower()
        
        # high priority indicators
        high_priority_words = ["urgent", "asap", "emergency", "critical", "important", "deadline"]
        if any(word in content_lower for word in high_priority_words):
            return "high"
        
        # medium priority indicators
        medium_priority_words = ["meeting", "call", "schedule", "project", "deadline", "review"]
        if any(word in content_lower for word in medium_priority_words):
            return "medium"
        
        # questions typically have medium priority
        if "?" in content:
            return "medium"
        
        # direct messages might have higher priority than group messages
        if chat.type == "private":
            return "medium"
        
        return "low"
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get message processing statistics"""
        return {
            "messages_processed": self.processed_count,
            "processor_status": "active"
        }