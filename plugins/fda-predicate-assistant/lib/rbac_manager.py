"""
RBAC Manager - Role-Based Access Control for FDA Tools Enterprise

Enforces role-based permissions on FDA command execution with:
1. Four roles: admin, ra_professional, reviewer, readonly
2. Granular permission model (user, project, command, system)
3. Command-to-permission mapping
4. Audit logging of all permission checks
5. Integration with SecurityGateway data classification

Compliance: 21 CFR Part 11.10(d) - Limiting system access to
authorized individuals.

Author: FDA Tools Development Team
Date: 2026-02-16
Version: 1.0.0
"""

import os
import json
import logging
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timezone

# Local imports
try:
    from user_manager import User
except ImportError:
    from lib.user_manager import User

logger = logging.getLogger("fda-rbac")


class Role(str, Enum):
    """User roles in the FDA Tools enterprise system."""
    ADMIN = "admin"
    RA_PROFESSIONAL = "ra_professional"
    REVIEWER = "reviewer"
    READONLY = "readonly"


class Permission(str, Enum):
    """Granular permissions for FDA Tools operations."""
    # User management
    USER_CREATE = "user:create"
    USER_READ = "user:read"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"

    # Project management
    PROJECT_CREATE = "project:create"
    PROJECT_READ = "project:read"
    PROJECT_UPDATE = "project:update"
    PROJECT_DELETE = "project:delete"

    # Command execution levels
    COMMAND_PUBLIC = "command:public"
    COMMAND_RESTRICTED = "command:restricted"
    COMMAND_CONFIDENTIAL = "command:confidential"

    # System operations
    SYSTEM_ADMIN = "system:admin"
    SYSTEM_MONITOR = "system:monitor"


# Role -> Permission mapping
# Each role includes all permissions listed
ROLE_PERMISSIONS: Dict[str, List[Permission]] = {
    Role.ADMIN: [
        Permission.USER_CREATE,
        Permission.USER_READ,
        Permission.USER_UPDATE,
        Permission.USER_DELETE,
        Permission.PROJECT_CREATE,
        Permission.PROJECT_READ,
        Permission.PROJECT_UPDATE,
        Permission.PROJECT_DELETE,
        Permission.COMMAND_PUBLIC,
        Permission.COMMAND_RESTRICTED,
        Permission.COMMAND_CONFIDENTIAL,
        Permission.SYSTEM_ADMIN,
        Permission.SYSTEM_MONITOR,
    ],
    Role.RA_PROFESSIONAL: [
        Permission.USER_READ,
        Permission.PROJECT_CREATE,
        Permission.PROJECT_READ,
        Permission.PROJECT_UPDATE,
        Permission.PROJECT_DELETE,
        Permission.COMMAND_PUBLIC,
        Permission.COMMAND_RESTRICTED,
        Permission.COMMAND_CONFIDENTIAL,
        Permission.SYSTEM_MONITOR,
    ],
    Role.REVIEWER: [
        Permission.PROJECT_READ,
        Permission.COMMAND_PUBLIC,
        Permission.COMMAND_RESTRICTED,
    ],
    Role.READONLY: [
        Permission.COMMAND_PUBLIC,
    ],
}


# Command -> required Permission mapping
COMMAND_PERMISSIONS: Dict[str, Permission] = {
    # Public commands (all roles)
    'validate': Permission.COMMAND_PUBLIC,
    'status': Permission.COMMAND_PUBLIC,
    'cache': Permission.COMMAND_PUBLIC,
    'help': Permission.COMMAND_PUBLIC,

    # Restricted commands (reviewer+)
    'research': Permission.COMMAND_RESTRICTED,
    'analyze': Permission.COMMAND_RESTRICTED,
    'safety': Permission.COMMAND_RESTRICTED,
    'warnings': Permission.COMMAND_RESTRICTED,
    'batchfetch': Permission.COMMAND_RESTRICTED,
    'compare-se': Permission.COMMAND_RESTRICTED,
    'pre-check': Permission.COMMAND_RESTRICTED,
    'review-simulator': Permission.COMMAND_RESTRICTED,
    'consistency': Permission.COMMAND_RESTRICTED,

    # Confidential commands (ra_professional+)
    'draft': Permission.COMMAND_CONFIDENTIAL,
    'assemble': Permission.COMMAND_CONFIDENTIAL,
    'export': Permission.COMMAND_CONFIDENTIAL,
    'submission-writer': Permission.COMMAND_CONFIDENTIAL,

    # Admin commands (admin only)
    'configure': Permission.SYSTEM_ADMIN,
    'user-manage': Permission.SYSTEM_ADMIN,
    'audit-review': Permission.SYSTEM_ADMIN,
}


class RBACManager:
    """
    Role-Based Access Control manager for FDA Tools.

    Enforces permission checks for command execution and
    resource access. All permission decisions are audited.

    Usage:
        rbac = RBACManager()
        allowed, reason = rbac.check_command_permission(
            user, "draft", DataClassification.CONFIDENTIAL
        )
    """

    def __init__(self, audit_log_path: Optional[str] = None):
        """
        Initialize RBAC manager.

        Args:
            audit_log_path: Path for RBAC audit log
                           (default: ~/.claude/fda-tools.rbac-audit.jsonl)
        """
        if audit_log_path is None:
            audit_log_path = os.path.expanduser(
                "~/.claude/fda-tools.rbac-audit.jsonl"
            )

        self.audit_log_path = Path(audit_log_path)
        self.audit_log_path.parent.mkdir(parents=True, exist_ok=True)

        # Permission cache for performance
        self._permission_cache: Dict[str, List[Permission]] = {}

    def check_permission(self, user: User, permission: Permission) -> bool:
        """
        Check if a user has a specific permission.

        Args:
            user: User object to check
            permission: Permission to verify

        Returns:
            True if user has the permission, False otherwise
        """
        if not user.is_active:
            return False

        user_permissions = self.get_user_permissions(user)
        allowed = permission in user_permissions

        # Audit the check
        self._audit_permission_check(
            user_id=user.user_id,
            permission=permission,
            allowed=allowed,
            reason="inactive_user" if not user.is_active else None
        )

        return allowed

    def check_command_permission(
        self,
        user: User,
        command: str,
        classification: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if a user has permission to execute a specific command.

        This combines command-level permission checks with data
        classification requirements.

        Args:
            user: User object to check
            command: FDA command name
            classification: Optional data classification (PUBLIC, RESTRICTED, CONFIDENTIAL)

        Returns:
            Tuple of (allowed, reason_if_denied)
        """
        if not user.is_active:
            reason = "User account '{}' is deactivated".format(user.user_id)
            self._audit_permission_check(
                user_id=user.user_id,
                permission=Permission.COMMAND_PUBLIC,
                allowed=False,
                reason=reason,
                command=command
            )
            return False, reason

        # Get required permission for command
        required_permission = COMMAND_PERMISSIONS.get(command)

        if required_permission is None:
            # Unknown command -- default to RESTRICTED
            required_permission = Permission.COMMAND_RESTRICTED
            logger.warning(
                "Unknown command '%s' -- defaulting to RESTRICTED permission",
                command
            )

        # Check user has required permission
        user_permissions = self.get_user_permissions(user)

        if required_permission not in user_permissions:
            reason = (
                "Role '{}' does not have '{}' permission "
                "required for command '{}'".format(
                    user.role,
                    required_permission.value,
                    command
                )
            )
            self._audit_permission_check(
                user_id=user.user_id,
                permission=required_permission,
                allowed=False,
                reason=reason,
                command=command
            )
            return False, reason

        # Additional classification check
        if classification:
            classification_ok, class_reason = self._check_classification_access(
                user, classification
            )
            if not classification_ok:
                self._audit_permission_check(
                    user_id=user.user_id,
                    permission=required_permission,
                    allowed=False,
                    reason=class_reason,
                    command=command
                )
                return False, class_reason

        # Permission granted
        self._audit_permission_check(
            user_id=user.user_id,
            permission=required_permission,
            allowed=True,
            command=command
        )

        return True, None

    def get_user_permissions(self, user: User) -> List[Permission]:
        """
        Get all permissions for a user based on their role.

        Args:
            user: User object

        Returns:
            List of Permission values
        """
        # Check cache first
        cache_key = "{}:{}".format(user.user_id, user.role)
        if cache_key in self._permission_cache:
            return self._permission_cache[cache_key]

        # Look up role permissions
        role_str = user.role
        permissions = ROLE_PERMISSIONS.get(role_str, [])

        # Cache for performance
        self._permission_cache[cache_key] = permissions

        return permissions

    def get_role_permissions(self, role: str) -> List[Permission]:
        """
        Get all permissions for a specific role.

        Args:
            role: Role name

        Returns:
            List of Permission values
        """
        return ROLE_PERMISSIONS.get(role, [])

    def get_allowed_commands(self, user: User) -> List[str]:
        """
        Get list of commands a user is allowed to execute.

        Args:
            user: User object

        Returns:
            List of command names
        """
        if not user.is_active:
            return []

        user_permissions = self.get_user_permissions(user)
        allowed_commands = []

        for command, required_perm in COMMAND_PERMISSIONS.items():
            if required_perm in user_permissions:
                allowed_commands.append(command)

        return sorted(allowed_commands)

    def can_manage_users(self, user: User) -> bool:
        """Check if user can manage other users."""
        return self.check_permission(user, Permission.USER_CREATE)

    def can_create_projects(self, user: User) -> bool:
        """Check if user can create projects."""
        return self.check_permission(user, Permission.PROJECT_CREATE)

    def can_view_system(self, user: User) -> bool:
        """Check if user can view system monitoring."""
        return self.check_permission(user, Permission.SYSTEM_MONITOR)

    def invalidate_cache(self, user_id: Optional[str] = None) -> None:
        """
        Invalidate permission cache.

        Args:
            user_id: Optional user to invalidate (None = invalidate all)
        """
        if user_id:
            keys_to_remove = [
                k for k in self._permission_cache
                if k.startswith("{}:".format(user_id))
            ]
            for key in keys_to_remove:
                del self._permission_cache[key]
        else:
            self._permission_cache.clear()

    # ========================================
    # Internal Helpers
    # ========================================

    def _check_classification_access(
        self,
        user: User,
        classification: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if user's role allows access to a data classification level.

        Args:
            user: User object
            classification: Data classification (PUBLIC, RESTRICTED, CONFIDENTIAL)

        Returns:
            Tuple of (allowed, reason_if_denied)
        """
        user_permissions = self.get_user_permissions(user)

        if classification == "CONFIDENTIAL":
            if Permission.COMMAND_CONFIDENTIAL not in user_permissions:
                return False, (
                    "Role '{}' cannot access CONFIDENTIAL data. "
                    "Required: ra_professional or admin role.".format(user.role)
                )

        elif classification == "RESTRICTED":
            if Permission.COMMAND_RESTRICTED not in user_permissions:
                return False, (
                    "Role '{}' cannot access RESTRICTED data. "
                    "Required: reviewer, ra_professional, or admin role.".format(
                        user.role
                    )
                )

        return True, None

    def _audit_permission_check(
        self,
        user_id: str,
        permission: Permission,
        allowed: bool,
        reason: Optional[str] = None,
        command: Optional[str] = None
    ) -> None:
        """
        Log a permission check to the RBAC audit trail.

        Args:
            user_id: User that was checked
            permission: Permission that was checked
            allowed: Whether access was granted
            reason: Optional denial reason
            command: Optional command being checked
        """
        event = {
            'timestamp': datetime.now(timezone.utc).isoformat() + 'Z',
            'user_id': user_id,
            'permission': permission.value,
            'allowed': allowed,
            'reason': reason,
            'command': command
        }

        try:
            with open(self.audit_log_path, 'a') as f:
                f.write(json.dumps(event) + '\n')
        except OSError:
            logger.warning(
                "Failed to write RBAC audit event for user '%s'", user_id
            )

    def get_audit_events(
        self,
        user_id: Optional[str] = None,
        allowed: Optional[bool] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Query RBAC audit events.

        Args:
            user_id: Optional user filter
            allowed: Optional allowed/denied filter
            limit: Maximum events to return

        Returns:
            List of audit event dictionaries
        """
        events = []

        if not self.audit_log_path.exists():
            return events

        try:
            with open(self.audit_log_path, 'r') as f:
                for line in f:
                    if len(events) >= limit:
                        break

                    try:
                        event = json.loads(line.strip())
                    except json.JSONDecodeError:
                        continue

                    if user_id and event.get('user_id') != user_id:
                        continue

                    if allowed is not None and event.get('allowed') != allowed:
                        continue

                    events.append(event)
        except OSError:
            pass

        return events


# Global singleton instance
_rbac_manager_instance: Optional[RBACManager] = None


def get_rbac_manager(audit_log_path: Optional[str] = None) -> RBACManager:
    """
    Get global RBACManager instance (singleton pattern).

    Args:
        audit_log_path: Optional path to RBAC audit log

    Returns:
        RBACManager instance
    """
    global _rbac_manager_instance
    if _rbac_manager_instance is None:
        _rbac_manager_instance = RBACManager(audit_log_path)
    return _rbac_manager_instance
