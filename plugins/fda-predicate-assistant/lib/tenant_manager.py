"""
Tenant Manager - Multi-Tenancy Data Isolation for FDA Tools Enterprise

Provides per-organization data isolation with:
1. Organization CRUD operations
2. Filesystem path isolation per user/organization
3. Shared resource management (API caches)
4. Cross-tenant collaboration (project sharing)
5. Directory structure initialization

Base directory: /fda-enterprise-data/ (configurable)

Directory layout:
    /fda-enterprise-data/
    +-- organizations/
    |   +-- org_acme/
    |   |   +-- users/
    |   |   |   +-- usr_001/
    |   |   |   |   +-- projects/
    |   |   |   |       +-- ABC001/
    |   |   |   +-- usr_002/
    |   |   +-- shared/
    |   |   |   +-- projects/
    |   |   +-- metadata.json
    |   +-- org_medtech/
    +-- shared/
    |   +-- api_cache/
    |   |   +-- openFDA/
    |   |   +-- MAUDE/
    |   |   +-- recalls/
    |   +-- guidance_cache/
    +-- system/
        +-- audit_logs/
        +-- metrics/

Author: FDA Tools Development Team
Date: 2026-02-16
Version: 1.0.0
"""

import os
import sys
import json
import uuid
import shutil
import threading
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from copy import deepcopy


@dataclass
class Organization:
    """
    Represents an organization (tenant) in the enterprise system.

    Attributes:
        organization_id: Unique identifier (org_<name>)
        name: Organization display name
        created_at: ISO 8601 creation timestamp
        is_active: Whether organization is active
        settings: Organization-specific settings
        user_count: Number of users in organization
        project_count: Number of projects in organization
    """
    organization_id: str
    name: str
    created_at: str
    is_active: bool = True
    settings: Dict[str, Any] = field(default_factory=dict)
    user_count: int = 0
    project_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize organization to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Organization':
        """Deserialize organization from dictionary."""
        return cls(
            organization_id=data['organization_id'],
            name=data['name'],
            created_at=data.get('created_at', ''),
            is_active=data.get('is_active', True),
            settings=data.get('settings', {}),
            user_count=data.get('user_count', 0),
            project_count=data.get('project_count', 0)
        )


@dataclass
class SharedProject:
    """
    Represents a project shared between users within an organization.

    Attributes:
        project_id: Project identifier
        owner_user_id: User who owns the project
        shared_with: List of user IDs the project is shared with
        organization_id: Organization the project belongs to
        shared_at: ISO 8601 share timestamp
        permissions: Sharing permissions (read, write)
    """
    project_id: str
    owner_user_id: str
    shared_with: List[str] = field(default_factory=list)
    organization_id: str = ""
    shared_at: str = ""
    permissions: str = "read"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SharedProject':
        """Deserialize from dictionary."""
        return cls(
            project_id=data['project_id'],
            owner_user_id=data['owner_user_id'],
            shared_with=data.get('shared_with', []),
            organization_id=data.get('organization_id', ''),
            shared_at=data.get('shared_at', ''),
            permissions=data.get('permissions', 'read')
        )


class TenantManager:
    """
    Manages multi-tenant data isolation for FDA Tools enterprise.

    Provides filesystem-level isolation per organization and user,
    with shared resources for API caches and cross-organization
    collaboration support.

    Usage:
        tenant = TenantManager()
        org = tenant.create_organization("Acme Medical Devices")
        path = tenant.get_project_path("usr_001", org.organization_id, "ABC001")
    """

    def __init__(self, data_root: Optional[str] = None):
        """
        Initialize tenant manager.

        Args:
            data_root: Root directory for enterprise data
                      (default: ~/fda-enterprise-data)
        """
        if data_root is None:
            data_root = os.path.expanduser("~/fda-enterprise-data")

        self.data_root = Path(data_root)
        self._lock = threading.Lock()
        self._organizations: Dict[str, Organization] = {}
        self._shared_projects: Dict[str, SharedProject] = {}

        # Initialize directory structure
        self._init_directory_structure()

        # Load existing organizations
        self._load_organizations()

    # ========================================
    # Organization CRUD
    # ========================================

    def create_organization(
        self,
        name: str,
        settings: Optional[Dict[str, Any]] = None
    ) -> Organization:
        """
        Create a new organization.

        Args:
            name: Organization display name
            settings: Optional organization-specific settings

        Returns:
            Created Organization object

        Raises:
            ValueError: If organization name is empty or already exists
        """
        if not name or not name.strip():
            raise ValueError("Organization name is required")

        # Generate organization ID from name
        org_id = "org_{}".format(
            name.lower().replace(' ', '_').replace('-', '_')[:20]
        )

        with self._lock:
            # Check for duplicate
            if org_id in self._organizations:
                raise ValueError(
                    "Organization '{}' already exists".format(name)
                )

            now = datetime.now(timezone.utc).isoformat() + 'Z'

            org = Organization(
                organization_id=org_id,
                name=name.strip(),
                created_at=now,
                is_active=True,
                settings=settings or {},
                user_count=0,
                project_count=0
            )

            # Create directory structure
            self._create_org_directories(org_id)

            # Store
            self._organizations[org_id] = org
            self._save_org_metadata(org)

        return deepcopy(org)

    def get_organization(self, organization_id: str) -> Optional[Organization]:
        """
        Retrieve an organization by ID.

        Args:
            organization_id: Organization identifier

        Returns:
            Organization object or None if not found
        """
        with self._lock:
            org = self._organizations.get(organization_id)
            return deepcopy(org) if org else None

    def update_organization(
        self,
        organization_id: str,
        updates: Dict[str, Any]
    ) -> Organization:
        """
        Update organization attributes.

        Args:
            organization_id: Organization identifier
            updates: Dictionary of attributes to update
                     Allowed: name, is_active, settings

        Returns:
            Updated Organization object

        Raises:
            ValueError: If organization not found or invalid update
        """
        allowed_fields = {'name', 'is_active', 'settings'}

        with self._lock:
            org = self._organizations.get(organization_id)
            if org is None:
                raise ValueError(
                    "Organization not found: {}".format(organization_id)
                )

            for key, value in updates.items():
                if key not in allowed_fields:
                    raise ValueError(
                        "Cannot update field '{}'. Allowed: {}".format(
                            key, ', '.join(sorted(allowed_fields))
                        )
                    )
                setattr(org, key, value)

            self._save_org_metadata(org)

        return deepcopy(org)

    def list_organizations(self) -> List[Organization]:
        """
        List all organizations.

        Returns:
            List of Organization objects
        """
        with self._lock:
            return [deepcopy(org) for org in self._organizations.values()]

    # ========================================
    # Path Isolation
    # ========================================

    def get_user_data_path(
        self,
        user_id: str,
        organization_id: str
    ) -> Path:
        """
        Get the isolated data directory path for a user.

        Args:
            user_id: User identifier
            organization_id: Organization identifier

        Returns:
            Path to user's data directory

        Raises:
            ValueError: If organization not found
        """
        self._validate_org_exists(organization_id)

        path = (
            self.data_root / "organizations" /
            organization_id / "users" / user_id
        )
        path.mkdir(parents=True, exist_ok=True)
        return path

    def get_shared_data_path(self, organization_id: str) -> Path:
        """
        Get the shared data directory for an organization.

        Args:
            organization_id: Organization identifier

        Returns:
            Path to organization's shared directory

        Raises:
            ValueError: If organization not found
        """
        self._validate_org_exists(organization_id)

        path = (
            self.data_root / "organizations" /
            organization_id / "shared"
        )
        path.mkdir(parents=True, exist_ok=True)
        return path

    def get_project_path(
        self,
        user_id: str,
        organization_id: str,
        project_id: str
    ) -> Path:
        """
        Get the path for a specific project.

        Args:
            user_id: User identifier
            organization_id: Organization identifier
            project_id: Project identifier

        Returns:
            Path to project directory

        Raises:
            ValueError: If organization not found
        """
        user_path = self.get_user_data_path(user_id, organization_id)
        project_path = user_path / "projects" / project_id
        project_path.mkdir(parents=True, exist_ok=True)
        return project_path

    def get_shared_cache_path(self) -> Path:
        """
        Get the global shared API cache directory.

        Returns:
            Path to shared cache directory
        """
        path = self.data_root / "shared" / "api_cache"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def get_system_path(self, subdir: str = "") -> Path:
        """
        Get the system directory path.

        Args:
            subdir: Optional subdirectory (audit_logs, metrics)

        Returns:
            Path to system directory
        """
        path = self.data_root / "system"
        if subdir:
            path = path / subdir
        path.mkdir(parents=True, exist_ok=True)
        return path

    def validate_path_access(
        self,
        user_id: str,
        organization_id: str,
        target_path: str
    ) -> bool:
        """
        Validate that a user can access a given path.

        Enforces tenant isolation: users can only access paths within
        their own organization directory or shared resources.

        Args:
            user_id: User attempting access
            organization_id: User's organization
            target_path: Path being accessed

        Returns:
            True if access is allowed
        """
        target = Path(target_path).resolve()
        target_str = str(target)

        # Allow access to user's own directory
        user_dir = str(
            (self.data_root / "organizations" /
             organization_id / "users" / user_id).resolve()
        )
        if target_str.startswith(user_dir):
            return True

        # Allow access to organization shared directory
        shared_dir = str(
            (self.data_root / "organizations" /
             organization_id / "shared").resolve()
        )
        if target_str.startswith(shared_dir):
            return True

        # Allow access to global shared cache
        cache_dir = str(
            (self.data_root / "shared").resolve()
        )
        if target_str.startswith(cache_dir):
            return True

        # Check if user has access via shared project
        for sp in self._shared_projects.values():
            if (sp.organization_id == organization_id and
                    user_id in sp.shared_with):
                owner_project = str(
                    (self.data_root / "organizations" /
                     organization_id / "users" / sp.owner_user_id /
                     "projects" / sp.project_id).resolve()
                )
                if target_str.startswith(owner_project):
                    return True

        return False

    # ========================================
    # Collaboration
    # ========================================

    def share_project(
        self,
        project_id: str,
        from_user: str,
        to_users: List[str],
        organization_id: str,
        permissions: str = "read"
    ) -> bool:
        """
        Share a project from one user to others within the same organization.

        Args:
            project_id: Project to share
            from_user: Owner user ID
            to_users: List of user IDs to share with
            organization_id: Organization both users belong to
            permissions: Sharing permission level (read or write)

        Returns:
            True if shared successfully

        Raises:
            ValueError: If project or users not found
        """
        if permissions not in ('read', 'write'):
            raise ValueError("Permissions must be 'read' or 'write'")

        # Verify project directory exists
        project_path = (
            self.data_root / "organizations" /
            organization_id / "users" / from_user /
            "projects" / project_id
        )

        if not project_path.exists():
            raise ValueError(
                "Project '{}' not found for user '{}'".format(
                    project_id, from_user
                )
            )

        with self._lock:
            share_key = "{}:{}:{}".format(
                organization_id, from_user, project_id
            )

            now = datetime.now(timezone.utc).isoformat() + 'Z'

            if share_key in self._shared_projects:
                # Update existing share
                sp = self._shared_projects[share_key]
                for uid in to_users:
                    if uid not in sp.shared_with:
                        sp.shared_with.append(uid)
                sp.permissions = permissions
            else:
                # Create new share
                sp = SharedProject(
                    project_id=project_id,
                    owner_user_id=from_user,
                    shared_with=to_users,
                    organization_id=organization_id,
                    shared_at=now,
                    permissions=permissions
                )
                self._shared_projects[share_key] = sp

            self._save_shared_projects()

        return True

    def get_shared_projects(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all projects shared with a user.

        Args:
            user_id: User to check shared projects for

        Returns:
            List of shared project info dictionaries
        """
        results = []

        with self._lock:
            for sp in self._shared_projects.values():
                if user_id in sp.shared_with:
                    results.append({
                        'project_id': sp.project_id,
                        'owner_user_id': sp.owner_user_id,
                        'organization_id': sp.organization_id,
                        'permissions': sp.permissions,
                        'shared_at': sp.shared_at,
                        'path': str(
                            self.data_root / "organizations" /
                            sp.organization_id / "users" /
                            sp.owner_user_id / "projects" / sp.project_id
                        )
                    })

        return results

    def unshare_project(
        self,
        project_id: str,
        from_user: str,
        organization_id: str,
        remove_users: Optional[List[str]] = None
    ) -> bool:
        """
        Remove project sharing.

        Args:
            project_id: Project to unshare
            from_user: Owner user ID
            organization_id: Organization ID
            remove_users: Specific users to remove (None = remove all)

        Returns:
            True if unshared successfully
        """
        share_key = "{}:{}:{}".format(
            organization_id, from_user, project_id
        )

        with self._lock:
            sp = self._shared_projects.get(share_key)
            if sp is None:
                return False

            if remove_users:
                sp.shared_with = [
                    uid for uid in sp.shared_with
                    if uid not in remove_users
                ]
                if not sp.shared_with:
                    del self._shared_projects[share_key]
            else:
                del self._shared_projects[share_key]

            self._save_shared_projects()

        return True

    # ========================================
    # Internal Helpers
    # ========================================

    def _init_directory_structure(self) -> None:
        """Initialize the base directory structure."""
        dirs = [
            self.data_root / "organizations",
            self.data_root / "shared" / "api_cache" / "openFDA",
            self.data_root / "shared" / "api_cache" / "MAUDE",
            self.data_root / "shared" / "api_cache" / "recalls",
            self.data_root / "shared" / "guidance_cache",
            self.data_root / "system" / "audit_logs",
            self.data_root / "system" / "metrics",
        ]

        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)

    def _create_org_directories(self, organization_id: str) -> None:
        """Create directory structure for an organization."""
        org_base = self.data_root / "organizations" / organization_id

        dirs = [
            org_base / "users",
            org_base / "shared" / "projects",
        ]

        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)

    def _validate_org_exists(self, organization_id: str) -> None:
        """
        Validate that an organization exists.

        Raises:
            ValueError: If organization not found
        """
        if organization_id not in self._organizations:
            raise ValueError(
                "Organization not found: {}".format(organization_id)
            )

    def _load_organizations(self) -> None:
        """Load organizations from disk."""
        orgs_dir = self.data_root / "organizations"
        if not orgs_dir.exists():
            return

        for org_dir in orgs_dir.iterdir():
            if not org_dir.is_dir():
                continue

            metadata_file = org_dir / "metadata.json"
            if metadata_file.exists():
                try:
                    with open(metadata_file, 'r') as f:
                        data = json.load(f)
                    org = Organization.from_dict(data)
                    self._organizations[org.organization_id] = org
                except (json.JSONDecodeError, KeyError, OSError):
                    continue

        # Load shared projects
        self._load_shared_projects()

    def _save_org_metadata(self, org: Organization) -> None:
        """Save organization metadata to disk."""
        org_dir = (
            self.data_root / "organizations" / org.organization_id
        )
        org_dir.mkdir(parents=True, exist_ok=True)

        metadata_file = org_dir / "metadata.json"
        try:
            with open(metadata_file, 'w') as f:
                json.dump(org.to_dict(), f, indent=2, default=str)
        except OSError as e:
            print(f"Warning: Failed to save organization metadata: {e}", file=sys.stderr)

    def _save_shared_projects(self) -> None:
        """Save shared projects registry to disk."""
        registry_file = self.data_root / "system" / "shared_projects.json"
        try:
            data = {
                'shared_projects': [
                    sp.to_dict() for sp in self._shared_projects.values()
                ],
                'last_modified': datetime.now(timezone.utc).isoformat() + 'Z'
            }
            with open(registry_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except OSError as e:
            print(f"Warning: Failed to save shared projects registry: {e}", file=sys.stderr)

    def _load_shared_projects(self) -> None:
        """Load shared projects registry from disk."""
        registry_file = self.data_root / "system" / "shared_projects.json"
        if not registry_file.exists():
            return

        try:
            with open(registry_file, 'r') as f:
                data = json.load(f)

            for sp_data in data.get('shared_projects', []):
                sp = SharedProject.from_dict(sp_data)
                key = "{}:{}:{}".format(
                    sp.organization_id, sp.owner_user_id, sp.project_id
                )
                self._shared_projects[key] = sp
        except (json.JSONDecodeError, OSError) as e:
            print(f"Warning: Failed to load shared projects registry: {e}", file=sys.stderr)

    @property
    def organization_count(self) -> int:
        """Get total number of organizations."""
        with self._lock:
            return len(self._organizations)


# Global singleton
_tenant_manager_instance: Optional[TenantManager] = None


def get_tenant_manager(data_root: Optional[str] = None) -> TenantManager:
    """
    Get global TenantManager instance (singleton pattern).

    Args:
        data_root: Optional data root directory

    Returns:
        TenantManager instance
    """
    global _tenant_manager_instance
    if _tenant_manager_instance is None:
        _tenant_manager_instance = TenantManager(data_root)
    return _tenant_manager_instance
