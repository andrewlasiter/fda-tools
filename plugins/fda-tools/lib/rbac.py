#!/usr/bin/env python3
"""
Role-Based Access Control (RBAC) Module (FDA-173 / REG-006).

This module provides function-level access control through decorators
and permission checking utilities for the 21 CFR Part 11 authentication system.

Regulatory Compliance:
  - 21 CFR 11.300(a): Limit system access to authorized individuals
  - 21 CFR 11.10(g): Authority checks to ensure valid permissions
  - 21 CFR 11.50: Electronic signatures tied to specific individuals

Permission Model:
  ADMIN Role:
    - user:create, user:read, user:update, user:delete
    - user:lock, user:unlock, user:reset_password
    - system:configure, system:audit, system:export
    - submission:create, submission:read, submission:update, submission:delete
    - data:import, data:export

  ANALYST Role:
    - submission:create, submission:read, submission:update
    - data:import, data:export
    - user:read (own account only)

  VIEWER Role:
    - submission:read
    - user:read (own account only)

Usage:
    from lib.rbac import require_role, require_permission, check_permission
    from lib.auth import Role, User

    @require_role(Role.ADMIN)
    def delete_user(username: str):
        # Only admins can execute this function
        pass

    @require_permission("submission:delete")
    def delete_submission(submission_id: str):
        # Requires submission:delete permission
        pass

    # Manual permission check
    if check_permission(user, "user:update"):
        # User has permission
        pass

Architecture:
    - Decorator-based access control
    - Role-to-permission mapping
    - Integration with AuthManager for session validation
    - Audit logging for access denials

Version: 1.0.0 (FDA-173)
"""

import functools
import logging
from typing import Callable, Dict, Optional, Set

from lib.auth import AuthManager, Role, User, AuditEventType

logger = logging.getLogger(__name__)

# ============================================================
# Permission Definitions
# ============================================================

# Role-to-permissions mapping
ROLE_PERMISSIONS: Dict[Role, Set[str]] = {
    Role.ADMIN: {
        # User management
        "user:create",
        "user:read",
        "user:update",
        "user:delete",
        "user:lock",
        "user:unlock",
        "user:reset_password",
        "user:change_role",
        # System administration
        "system:configure",
        "system:audit",
        "system:export",
        "system:import",
        # Submission management
        "submission:create",
        "submission:read",
        "submission:update",
        "submission:delete",
        "submission:submit",
        # Data operations
        "data:import",
        "data:export",
        "data:purge",
    },
    Role.ANALYST: {
        # Submission operations
        "submission:create",
        "submission:read",
        "submission:update",
        "submission:draft",
        # Data operations
        "data:import",
        "data:export",
        # Limited user permissions
        "user:read",  # Own account only
        "user:update_password",  # Own password only
    },
    Role.VIEWER: {
        # Read-only access
        "submission:read",
        "data:export",  # Export reports
        # Limited user permissions
        "user:read",  # Own account only
        "user:update_password",  # Own password only
    },
}


def get_role_permissions(role: Role) -> Set[str]:
    """Get all permissions for a role.

    Args:
        role: User role

    Returns:
        Set of permission strings

    Examples:
        >>> perms = get_role_permissions(Role.ADMIN)
        >>> "user:create" in perms
        True
        >>> perms = get_role_permissions(Role.VIEWER)
        >>> "user:delete" in perms
        False
    """
    return ROLE_PERMISSIONS.get(role, set())


def has_permission(user: User, permission: str) -> bool:
    """Check if user has specific permission.

    Args:
        user: User object
        permission: Permission string (e.g., "user:create")

    Returns:
        True if user has permission, False otherwise

    Examples:
        >>> admin = User(username="admin", role=Role.ADMIN)
        >>> has_permission(admin, "user:create")
        True
        >>> viewer = User(username="viewer", role=Role.VIEWER)
        >>> has_permission(viewer, "user:create")
        False
    """
    if not user or not user.is_active:
        return False

    if user.is_locked:
        return False

    role_perms = get_role_permissions(user.role)
    return permission in role_perms


def check_permission(user: Optional[User], permission: str) -> bool:
    """Check permission with null safety.

    Args:
        user: User object or None
        permission: Permission string

    Returns:
        True if user exists and has permission, False otherwise

    Examples:
        >>> check_permission(None, "user:create")
        False
        >>> admin = User(username="admin", role=Role.ADMIN)
        >>> check_permission(admin, "user:create")
        True
    """
    if user is None:
        return False
    return has_permission(user, permission)


# ============================================================
# Decorators
# ============================================================

def require_role(*allowed_roles: Role):
    """Decorator to require specific role(s) for function execution.

    This decorator validates that the authenticated user has one of the
    specified roles before allowing function execution. It integrates with
    the AuthManager session system and logs access denials to the audit trail.

    Args:
        *allowed_roles: One or more Role enums

    Raises:
        PermissionError: User not authenticated or lacks required role

    Usage:
        @require_role(Role.ADMIN)
        def admin_only_function():
            pass

        @require_role(Role.ADMIN, Role.ANALYST)
        def admin_or_analyst_function():
            pass

    Integration:
        The decorated function should receive a 'session_token' parameter
        or have it available in the calling context. The decorator will
        validate the session and extract the user.

    Examples:
        >>> @require_role(Role.ADMIN)
        ... def create_user(session_token: str, username: str):
        ...     return f"Creating user {username}"
        >>> create_user("valid_admin_token", "newuser")
        'Creating user newuser'
        >>> create_user("viewer_token", "newuser")  # doctest: +SKIP
        Traceback (most recent call last):
        PermissionError: Insufficient permissions
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Extract session_token from kwargs or args
            session_token = kwargs.get('session_token')
            if not session_token and args:
                # Try to extract from positional args
                # Assume first arg might be session_token if string
                if isinstance(args[0], str) and len(args[0]) == 128:
                    session_token = args[0]

            if not session_token:
                logger.warning(
                    f"Access denied to {func.__name__}: No session token provided"
                )
                raise PermissionError("Authentication required")

            # Validate session and get user
            auth = AuthManager()
            user = auth.validate_session(session_token)

            if not user:
                logger.warning(
                    f"Access denied to {func.__name__}: Invalid session token"
                )
                auth.log_audit_event(
                    None,
                    AuditEventType.ACCESS_DENIED,
                    f"Invalid session for {func.__name__}"
                )
                raise PermissionError("Invalid or expired session")

            # Check role
            if user.role not in allowed_roles:
                logger.warning(
                    f"Access denied to {func.__name__}: "
                    f"User {user.username} has role {user.role.value}, "
                    f"requires one of {[r.value for r in allowed_roles]}"
                )
                auth.log_audit_event(
                    user,
                    AuditEventType.ACCESS_DENIED,
                    f"Insufficient role for {func.__name__}"
                )
                raise PermissionError(
                    f"Requires one of: {', '.join(r.value for r in allowed_roles)}"
                )

            # Inject user into kwargs for convenience
            kwargs['_authenticated_user'] = user

            return func(*args, **kwargs)

        return wrapper
    return decorator


def require_permission(permission: str):
    """Decorator to require specific permission for function execution.

    This decorator validates that the authenticated user has the specified
    permission before allowing function execution. It provides finer-grained
    access control than role-based checks.

    Args:
        permission: Permission string (e.g., "user:create")

    Raises:
        PermissionError: User not authenticated or lacks required permission

    Usage:
        @require_permission("submission:delete")
        def delete_submission(session_token: str, submission_id: str):
            pass

    Examples:
        >>> @require_permission("user:create")
        ... def create_user(session_token: str, username: str):
        ...     return f"Creating user {username}"
        >>> create_user("admin_token", "newuser")  # doctest: +SKIP
        'Creating user newuser'
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Extract session_token from kwargs or args
            session_token = kwargs.get('session_token')
            if not session_token and args:
                if isinstance(args[0], str) and len(args[0]) == 128:
                    session_token = args[0]

            if not session_token:
                logger.warning(
                    f"Access denied to {func.__name__}: No session token provided"
                )
                raise PermissionError("Authentication required")

            # Validate session and get user
            auth = AuthManager()
            user = auth.validate_session(session_token)

            if not user:
                logger.warning(
                    f"Access denied to {func.__name__}: Invalid session token"
                )
                auth.log_audit_event(
                    None,
                    AuditEventType.ACCESS_DENIED,
                    f"Invalid session for {func.__name__}"
                )
                raise PermissionError("Invalid or expired session")

            # Check permission
            if not has_permission(user, permission):
                logger.warning(
                    f"Access denied to {func.__name__}: "
                    f"User {user.username} lacks permission '{permission}'"
                )
                auth.log_audit_event(
                    user,
                    AuditEventType.ACCESS_DENIED,
                    f"Lacks permission '{permission}' for {func.__name__}"
                )
                raise PermissionError(f"Requires permission: {permission}")

            # Inject user into kwargs for convenience
            kwargs['_authenticated_user'] = user

            return func(*args, **kwargs)

        return wrapper
    return decorator


# ============================================================
# Permission Utilities
# ============================================================

def list_all_permissions() -> Dict[str, list]:
    """List all permissions organized by category.

    Returns:
        Dictionary mapping category to list of permissions

    Examples:
        >>> perms = list_all_permissions()
        >>> "user" in perms
        True
        >>> "user:create" in perms["user"]
        True
    """
    # Collect all unique permissions across roles
    all_perms = set()
    for role_perms in ROLE_PERMISSIONS.values():
        all_perms.update(role_perms)

    # Organize by category (prefix before colon)
    categorized: Dict[str, list] = {}
    for perm in sorted(all_perms):
        if ':' in perm:
            category, action = perm.split(':', 1)
            if category not in categorized:
                categorized[category] = []
            categorized[category].append(perm)

    return categorized


def get_permission_summary(user: User) -> Dict[str, int]:
    """Get permission summary for a user.

    Args:
        user: User object

    Returns:
        Dictionary with permission counts by category

    Examples:
        >>> admin = User(username="admin", role=Role.ADMIN)
        >>> summary = get_permission_summary(admin)
        >>> summary["user"] > 0
        True
    """
    user_perms = get_role_permissions(user.role)
    summary: Dict[str, int] = {}

    for perm in user_perms:
        if ':' in perm:
            category = perm.split(':', 1)[0]
            summary[category] = summary.get(category, 0) + 1

    return summary


def format_permissions(user: User) -> str:
    """Format user permissions as human-readable string.

    Args:
        user: User object

    Returns:
        Formatted permission string

    Examples:
        >>> admin = User(username="admin", role=Role.ADMIN)
        >>> output = format_permissions(admin)
        >>> "user:create" in output
        True
    """
    perms = get_role_permissions(user.role)
    categorized = {}

    for perm in sorted(perms):
        if ':' in perm:
            category, action = perm.split(':', 1)
            if category not in categorized:
                categorized[category] = []
            categorized[category].append(action)

    lines = [f"Role: {user.role.value.upper()}", ""]
    for category, actions in sorted(categorized.items()):
        lines.append(f"{category.capitalize()}:")
        for action in sorted(actions):
            lines.append(f"  - {action}")
        lines.append("")

    return "\n".join(lines)
