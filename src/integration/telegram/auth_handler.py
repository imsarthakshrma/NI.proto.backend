"""
Telegram Authorization Handler for DELA AI
Manages user permissions and group access control
"""

import os
from typing import Set
from telegram import Update
import logging

logger = logging.getLogger(__name__)

class TelegramAuthHandler:
    """
    Handles authorization for Telegram bot interactions
    """
    def __init__(self):
        self.authorized_groups = self._load_authorized_groups()
        self.authorized_users = self._load_authorized_users()
        self.admin_users = self._load_admin_users()

        logger.info(f"Auth handler initialized with {len(self.authorized_groups)} groups, {len(self.authorized_users)} users")

    def _load_authorized_groups(self) -> Set[int]:

        group_env = os.getenv("TELEGRAM_ALLOWED_GROUPS", "")

        if not group_env:
            logger.warning("No TELEGRAM_ALLOWED_GROUPS specified - bot will work in all groups")
            return set()

        try:
            group_ids = [int(group_id.strip()) for group_id in group_env.split(",") if group_id.strip()]
            return set(group_ids)
        except ValueError as e:
            logger.error(f"Error parsing TELEGRAM_ALLOWED_GROUPS: {e}")
            return set()

    def _load_authorized_users(self) -> Set[int]:
        

        user_env = os.getenv("TELEGRAM_ALLOWED_USERS", "")

        if not user_env:
            return set()

        try:
            user_ids = [int(user_id.strip()) for user_id in user_env.split(",") if user_id.strip()]
            return set(user_ids)
        except ValueError as e:
            logger.error(f"Error parsing TELEGRAM_ALLOWED_USERS: {e}")
            return set()
    
    def _load_admin_users(self) -> Set[int]:

        admins_env = os.getenv("TELEGRAM_ADMIN_USERS", "")
        
        if not admins_env:
            return set()
        
        try:
            admin_ids = [int(admin_id.strip()) for admin_id in admins_env.split(",") if admin_id.strip()]
            return set(admin_ids)
        except ValueError as e:
            logger.error(f"Error parsing TELEGRAM_ADMIN_USERS: {e}")
            return set()

    def is_authorized(self, update: Update) -> bool:

        try:
            user = update.effective_user
            chat = update.effective_chat
            
            if not user or not chat:
                return False
            
            # admin users are always authorized
            if user.id in self.admin_users:
                logger.info(f"Admin user {user.first_name} ({user.id}) authorized")
                return True
            
            # check if user is in authorized users list
            if self.authorized_users and user.id in self.authorized_users:
                logger.info(f"Authorized user {user.first_name} ({user.id}) granted access")
                return True
            
            # explicit development mode check
            dev_mode = os.getenv("TELEGRAM_DEV_MODE", "false").lower() == "true"

            # check if chat is in authorized groups
            if self.authorized_groups:
                if chat.id in self.authorized_groups:
                    logger.info(f"Message from authorized group {chat.title} ({chat.id})")
                    return True
                else:
                    logger.warning(f"Unauthorized group access attempt: {chat.title} ({chat.id})")
                    return False
            
            # if no specific authorization configured, allow all (development mode)
            if dev_mode and not self.authorized_groups and not self.authorized_users:
                logger.info(f"Development mode - allowing access from {user.first_name}")
                return True
            
            elif not self.authorized_groups and not self.authorized_users:
                logger.warning("No authorization configured and dev mode disabled - denying access")
                return False
            
            logger.warning(f"Unauthorized access attempt from {user.first_name} ({user.id}) in {chat.title}")
            return False
        
        except Exception as e:
            logger.error(f"Error checking authorization : {e}")
            return False

    def is_admin(self, user_id: int) -> bool:
        return user_id in self.admin_users
    
    def add_authorized_group(self, group_id: int) -> bool:

        try:
            self.authorized_groups.add(group_id)
            logger.info(f"Added group {group_id} to authorized list")
            return True
        except Exception as e:
            logger.error(f"Error adding authorized group: {e}")
            return False
    
    def remove_authorized_group(self, group_id: int) -> bool:

        try:
            self.authorized_groups.discard(group_id)
            logger.info(f"Removed group {group_id} from authorized list")
            return True
        except Exception as e:
            logger.error(f"Error removing authorized group: {e}")
            return False
    
    def get_auth_status(self) -> dict:

        return {
            "authorized_groups": len(self.authorized_groups),
            "authorized_users": len(self.authorized_users),
            "admin_users": len(self.admin_users),
            "development_mode": not self.authorized_groups and not self.authorized_users
        }