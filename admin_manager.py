"""Admin management system - stores admins in bot state (memory only)."""
from typing import Optional, Set

from config import SYSADMIN_USER_ID


class AdminManager:
    """Manages admin users. Only sysadmin is persistent, other admins are stored in memory by username."""
    
    def __init__(self):
        self._admins: Set[str] = set()  # Store usernames (lowercase, without @)
    
    def is_sysadmin(self, user_id: int) -> bool:
        """Check if user is the system admin."""
        return user_id == SYSADMIN_USER_ID
    
    def is_admin(self, username: Optional[str]) -> bool:
        """
        Check if user is admin (sysadmin or sub-admin).
        Args:
            username: Username of the user (can be None)
        """
        if username is None:
            return False
        # Normalize username: lowercase, remove @ if present
        normalized_username = username.lower().lstrip('@')
        return normalized_username in self._admins
    
    def add_admin(self, username: str) -> bool:
        """
        Add a sub-admin by username. Only sysadmin can do this.
        Args:
            username: Username to add (with or without @)
        Returns:
            True if added, False if already exists or invalid
        """
        if not username:
            return False
        # Normalize username: lowercase, remove @ if present
        normalized_username = username.lower().lstrip('@')
        if normalized_username in self._admins:
            return False  # Already exists
        self._admins.add(normalized_username)
        return True
    
    def remove_admin(self, username: str) -> bool:
        """
        Remove a sub-admin by username. Only sysadmin can do this.
        Args:
            username: Username to remove (with or without @)
        Returns:
            True if removed, False if not found
        """
        if not username:
            return False
        # Normalize username: lowercase, remove @ if present
        normalized_username = username.lower().lstrip('@')
        if normalized_username in self._admins:
            self._admins.remove(normalized_username)
            return True
        return False
    
    def list_admins(self) -> Set[str]:
        """Get list of all admin usernames (excluding sysadmin)."""
        return self._admins.copy()


# Global admin manager instance
admin_manager = AdminManager()

