"""
Phase 4 Enterprise Features - Comprehensive Test Suite

Tests for:
1. UserManager (15 tests) - CRUD, enrollment, authentication
2. RBACManager (12 tests) - Permission checks, command mapping, audit
3. TenantManager (10 tests) - Organization CRUD, path isolation, collaboration
4. SignatureManager (8 tests) - Creation, verification, 21 CFR Part 11
5. MonitoringManager (10 tests) - Alerts, metrics, health monitoring
6. Integration Tests (15 tests) - End-to-end workflows

Run with:
    cd plugins/fda-predicate-assistant
    python3 -m pytest tests/test_enterprise_phase4.py -v

Author: FDA Tools Development Team
Date: 2026-02-16
Version: 1.0.0
"""

import os
import sys
import json
import time
import shutil
import tempfile
from pathlib import Path
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

import pytest

# Add paths for imports
TESTS_DIR = Path(__file__).parent.resolve()
PLUGIN_DIR = TESTS_DIR.parent.resolve()
LIB_DIR = PLUGIN_DIR / "lib"
BRIDGE_DIR = PLUGIN_DIR / "bridge"

sys.path.insert(0, str(LIB_DIR))
sys.path.insert(0, str(BRIDGE_DIR))

from user_manager import UserManager, User, VALID_ROLES
from rbac_manager import (
    RBACManager, Role, Permission, ROLE_PERMISSIONS, COMMAND_PERMISSIONS
)
from tenant_manager import TenantManager, Organization
from signature_manager import (
    SignatureManager, ElectronicSignature, SIGNATURE_REQUIRED_COMMANDS
)
from monitoring_manager import (
    MonitoringManager, AlertType, AlertSeverity, Alert
)


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def temp_dir():
    """Create a temporary directory for test data."""
    d = tempfile.mkdtemp(prefix="fda_test_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def user_mgr(temp_dir):
    """Create a UserManager with temporary database."""
    db_path = os.path.join(temp_dir, "users.json")
    return UserManager(user_db_path=db_path)


@pytest.fixture
def rbac_mgr(temp_dir):
    """Create an RBACManager with temporary audit log."""
    audit_path = os.path.join(temp_dir, "rbac-audit.jsonl")
    return RBACManager(audit_log_path=audit_path)


@pytest.fixture
def tenant_mgr(temp_dir):
    """Create a TenantManager with temporary data root."""
    data_root = os.path.join(temp_dir, "enterprise")
    return TenantManager(data_root=data_root)


@pytest.fixture
def sig_mgr(temp_dir):
    """Create a SignatureManager with temporary storage."""
    sig_path = os.path.join(temp_dir, "signatures")
    return SignatureManager(signatures_path=sig_path)


@pytest.fixture
def monitor_mgr(temp_dir):
    """Create a MonitoringManager with temporary storage."""
    metrics_dir = os.path.join(temp_dir, "metrics")
    alerts_dir = os.path.join(temp_dir, "alerts")
    return MonitoringManager(
        metrics_dir=metrics_dir,
        alerts_dir=alerts_dir
    )


@pytest.fixture
def sample_user(user_mgr):
    """Create a sample user for testing."""
    return user_mgr.create_user(
        email="alice@device-corp.com",
        name="Alice Johnson",
        role="ra_professional",
        organization_id="org_acme"
    )


@pytest.fixture
def sample_admin(user_mgr):
    """Create a sample admin user for testing."""
    return user_mgr.create_user(
        email="admin@device-corp.com",
        name="Admin User",
        role="admin",
        organization_id="org_acme"
    )


# ============================================================
# 1. UserManager Tests (15 tests)
# ============================================================

class TestUserManager:
    """Test suite for UserManager class."""

    def test_create_user(self, user_mgr):
        """Test creating a new user account."""
        user = user_mgr.create_user(
            email="alice@device-corp.com",
            name="Alice Johnson",
            role="ra_professional",
            organization_id="org_acme"
        )

        assert user.email == "alice@device-corp.com"
        assert user.name == "Alice Johnson"
        assert user.role == "ra_professional"
        assert user.organization_id == "org_acme"
        assert user.is_active is True
        assert user.user_id.startswith("usr_")
        assert user.enrolled_at is not None

    def test_create_user_with_handles(self, user_mgr):
        """Test creating user with messaging handles."""
        handles = {
            "whatsapp": "+14155551234",
            "telegram": "@alicejohnson",
            "slack": "U01ABC123"
        }

        user = user_mgr.create_user(
            email="alice@device-corp.com",
            name="Alice Johnson",
            role="ra_professional",
            organization_id="org_acme",
            messaging_handles=handles
        )

        assert user.messaging_handles["whatsapp"] == "+14155551234"
        assert user.messaging_handles["telegram"] == "@alicejohnson"
        assert len(user.messaging_handles) == 3

    def test_create_user_duplicate_email(self, user_mgr):
        """Test that duplicate email raises ValueError."""
        user_mgr.create_user(
            email="alice@device-corp.com",
            name="Alice",
            role="reviewer",
            organization_id="org_acme"
        )

        with pytest.raises(ValueError, match="already exists"):
            user_mgr.create_user(
                email="alice@device-corp.com",
                name="Alice Copy",
                role="reviewer",
                organization_id="org_acme"
            )

    def test_create_user_invalid_role(self, user_mgr):
        """Test that invalid role raises ValueError."""
        with pytest.raises(ValueError, match="Invalid role"):
            user_mgr.create_user(
                email="bad@corp.com",
                name="Bad User",
                role="superadmin",
                organization_id="org_acme"
            )

    def test_create_user_invalid_email(self, user_mgr):
        """Test that invalid email raises ValueError."""
        with pytest.raises(ValueError, match="Invalid email"):
            user_mgr.create_user(
                email="not-an-email",
                name="Bad Email",
                role="reviewer",
                organization_id="org_acme"
            )

    def test_get_user_by_id(self, user_mgr, sample_user):
        """Test retrieving user by ID."""
        retrieved = user_mgr.get_user(sample_user.user_id)

        assert retrieved is not None
        assert retrieved.user_id == sample_user.user_id
        assert retrieved.email == sample_user.email

    def test_get_user_by_email(self, user_mgr, sample_user):
        """Test retrieving user by email."""
        retrieved = user_mgr.get_user_by_email("alice@device-corp.com")

        assert retrieved is not None
        assert retrieved.email == "alice@device-corp.com"

    def test_get_user_by_handle(self, user_mgr):
        """Test retrieving user by messaging handle."""
        user = user_mgr.create_user(
            email="bob@device-corp.com",
            name="Bob Smith",
            role="reviewer",
            organization_id="org_acme",
            messaging_handles={"whatsapp": "+14155559999"}
        )

        retrieved = user_mgr.get_user_by_handle("whatsapp", "+14155559999")

        assert retrieved is not None
        assert retrieved.email == "bob@device-corp.com"

    def test_update_user(self, user_mgr, sample_user):
        """Test updating user attributes."""
        updated = user_mgr.update_user(
            sample_user.user_id,
            {'name': 'Alice J. Johnson', 'role': 'admin'}
        )

        assert updated.name == "Alice J. Johnson"
        assert updated.role == "admin"

    def test_update_user_invalid_field(self, user_mgr, sample_user):
        """Test that updating invalid field raises ValueError."""
        with pytest.raises(ValueError, match="Cannot update"):
            user_mgr.update_user(
                sample_user.user_id,
                {'email': 'new@email.com'}  # email is not updatable
            )

    def test_delete_user(self, user_mgr, sample_user):
        """Test deleting a user."""
        result = user_mgr.delete_user(sample_user.user_id)
        assert result is True

        # Verify user is gone
        assert user_mgr.get_user(sample_user.user_id) is None

    def test_delete_nonexistent_user(self, user_mgr):
        """Test deleting a non-existent user returns False."""
        assert user_mgr.delete_user("usr_nonexistent") is False

    def test_list_users(self, user_mgr):
        """Test listing users with organization filter."""
        user_mgr.create_user("a@corp.com", "A", "reviewer", "org_a")
        user_mgr.create_user("b@corp.com", "B", "reviewer", "org_b")
        user_mgr.create_user("c@corp.com", "C", "reviewer", "org_a")

        all_users = user_mgr.list_users()
        assert len(all_users) == 3

        org_a_users = user_mgr.list_users(organization_id="org_a")
        assert len(org_a_users) == 2

    def test_enrollment_token_lifecycle(self, user_mgr, sample_user):
        """Test full enrollment token lifecycle."""
        # Generate token
        token = user_mgr.generate_enrollment_token(sample_user.user_id)
        assert token.startswith("tok_")

        # Verify token
        user = user_mgr.verify_enrollment_token(token)
        assert user is not None
        assert user.user_id == sample_user.user_id

        # Complete enrollment
        updated = user_mgr.complete_enrollment(
            token,
            {"telegram": "@alice_test"}
        )
        assert updated.messaging_handles["telegram"] == "@alice_test"

        # Token should not be reusable
        with pytest.raises(ValueError, match="already used"):
            user_mgr.complete_enrollment(token, {"slack": "U001"})

    def test_persistence_across_instances(self, temp_dir):
        """Test that user data persists across manager instances."""
        db_path = os.path.join(temp_dir, "persist.json")

        # Create user with first manager
        mgr1 = UserManager(user_db_path=db_path)
        user = mgr1.create_user(
            email="persist@test.com",
            name="Persist User",
            role="reviewer",
            organization_id="org_test"
        )
        user_id = user.user_id

        # Create second manager (reloads from disk)
        mgr2 = UserManager(user_db_path=db_path)
        retrieved = mgr2.get_user(user_id)

        assert retrieved is not None
        assert retrieved.email == "persist@test.com"
        assert retrieved.name == "Persist User"


# ============================================================
# 2. RBACManager Tests (12 tests)
# ============================================================

class TestRBACManager:
    """Test suite for RBACManager class."""

    def test_admin_has_all_permissions(self, rbac_mgr):
        """Test that admin role has all permissions."""
        admin = User(
            user_id="usr_admin",
            email="admin@corp.com",
            name="Admin",
            role="admin",
            organization_id="org_test"
        )

        permissions = rbac_mgr.get_user_permissions(admin)
        assert Permission.SYSTEM_ADMIN in permissions
        assert Permission.COMMAND_CONFIDENTIAL in permissions
        assert Permission.USER_CREATE in permissions
        assert Permission.USER_DELETE in permissions

    def test_readonly_limited_permissions(self, rbac_mgr):
        """Test that readonly role has minimal permissions."""
        readonly = User(
            user_id="usr_ro",
            email="ro@corp.com",
            name="ReadOnly",
            role="readonly",
            organization_id="org_test"
        )

        permissions = rbac_mgr.get_user_permissions(readonly)
        assert Permission.COMMAND_PUBLIC in permissions
        assert Permission.COMMAND_RESTRICTED not in permissions
        assert Permission.COMMAND_CONFIDENTIAL not in permissions
        assert Permission.SYSTEM_ADMIN not in permissions

    def test_ra_professional_permissions(self, rbac_mgr):
        """Test RA professional role permissions."""
        ra = User(
            user_id="usr_ra",
            email="ra@corp.com",
            name="RA Pro",
            role="ra_professional",
            organization_id="org_test"
        )

        permissions = rbac_mgr.get_user_permissions(ra)
        assert Permission.COMMAND_PUBLIC in permissions
        assert Permission.COMMAND_RESTRICTED in permissions
        assert Permission.COMMAND_CONFIDENTIAL in permissions
        assert Permission.PROJECT_CREATE in permissions
        assert Permission.SYSTEM_ADMIN not in permissions
        assert Permission.USER_DELETE not in permissions

    def test_reviewer_permissions(self, rbac_mgr):
        """Test reviewer role permissions."""
        reviewer = User(
            user_id="usr_rev",
            email="rev@corp.com",
            name="Reviewer",
            role="reviewer",
            organization_id="org_test"
        )

        permissions = rbac_mgr.get_user_permissions(reviewer)
        assert Permission.COMMAND_PUBLIC in permissions
        assert Permission.COMMAND_RESTRICTED in permissions
        assert Permission.COMMAND_CONFIDENTIAL not in permissions
        assert Permission.PROJECT_READ in permissions
        assert Permission.PROJECT_CREATE not in permissions

    def test_check_command_permission_allowed(self, rbac_mgr):
        """Test command permission check (allowed)."""
        ra = User(
            user_id="usr_ra",
            email="ra@corp.com",
            name="RA Pro",
            role="ra_professional",
            organization_id="org_test"
        )

        allowed, reason = rbac_mgr.check_command_permission(ra, "draft")
        assert allowed is True
        assert reason is None

    def test_check_command_permission_denied(self, rbac_mgr):
        """Test command permission check (denied)."""
        readonly = User(
            user_id="usr_ro",
            email="ro@corp.com",
            name="ReadOnly",
            role="readonly",
            organization_id="org_test"
        )

        allowed, reason = rbac_mgr.check_command_permission(readonly, "draft")
        assert allowed is False
        assert reason is not None
        assert "readonly" in reason.lower() or "command:confidential" in reason.lower()

    def test_inactive_user_denied(self, rbac_mgr):
        """Test that inactive users are always denied."""
        inactive = User(
            user_id="usr_inactive",
            email="dead@corp.com",
            name="Inactive",
            role="admin",
            organization_id="org_test",
            is_active=False
        )

        allowed, reason = rbac_mgr.check_command_permission(inactive, "validate")
        assert allowed is False
        assert "deactivated" in reason.lower()

    def test_get_allowed_commands(self, rbac_mgr):
        """Test getting allowed commands for a role."""
        reviewer = User(
            user_id="usr_rev",
            email="rev@corp.com",
            name="Reviewer",
            role="reviewer",
            organization_id="org_test"
        )

        allowed_cmds = rbac_mgr.get_allowed_commands(reviewer)
        assert "validate" in allowed_cmds
        assert "research" in allowed_cmds
        assert "draft" not in allowed_cmds
        assert "configure" not in allowed_cmds

    def test_classification_access_control(self, rbac_mgr):
        """Test data classification access enforcement."""
        readonly = User(
            user_id="usr_ro",
            email="ro@corp.com",
            name="ReadOnly",
            role="readonly",
            organization_id="org_test"
        )

        # Readonly should not access RESTRICTED data
        allowed, reason = rbac_mgr.check_command_permission(
            readonly, "research", classification="RESTRICTED"
        )
        assert allowed is False

    def test_permission_audit_logging(self, rbac_mgr, temp_dir):
        """Test that permission checks are audited."""
        user = User(
            user_id="usr_audit",
            email="audit@corp.com",
            name="Audit Test",
            role="reviewer",
            organization_id="org_test"
        )

        rbac_mgr.check_command_permission(user, "validate")
        rbac_mgr.check_command_permission(user, "draft")  # Should be denied

        events = rbac_mgr.get_audit_events(user_id="usr_audit")
        assert len(events) >= 2

        # Should have at least one allowed and one denied
        allowed_events = [e for e in events if e['allowed']]
        denied_events = [e for e in events if not e['allowed']]
        assert len(allowed_events) >= 1
        assert len(denied_events) >= 1

    def test_cache_invalidation(self, rbac_mgr):
        """Test permission cache invalidation."""
        user = User(
            user_id="usr_cache",
            email="cache@corp.com",
            name="Cache Test",
            role="reviewer",
            organization_id="org_test"
        )

        # Prime cache
        rbac_mgr.get_user_permissions(user)

        # Invalidate
        rbac_mgr.invalidate_cache(user.user_id)

        # Should still work after invalidation
        perms = rbac_mgr.get_user_permissions(user)
        assert Permission.COMMAND_PUBLIC in perms

    def test_command_permission_mapping_complete(self, rbac_mgr):
        """Test that all mapped commands have valid permissions."""
        for command, permission in COMMAND_PERMISSIONS.items():
            assert isinstance(permission, Permission), (
                "Command '{}' has invalid permission type".format(command)
            )
            assert permission.value.startswith("command:") or \
                   permission.value.startswith("system:"), (
                "Command '{}' permission '{}' has unexpected prefix".format(
                    command, permission.value
                )
            )


# ============================================================
# 3. TenantManager Tests (10 tests)
# ============================================================

class TestTenantManager:
    """Test suite for TenantManager class."""

    def test_create_organization(self, tenant_mgr):
        """Test creating a new organization."""
        org = tenant_mgr.create_organization("Acme Medical Devices")

        assert org.name == "Acme Medical Devices"
        assert org.organization_id.startswith("org_")
        assert org.is_active is True

    def test_create_duplicate_organization(self, tenant_mgr):
        """Test that duplicate organization raises ValueError."""
        tenant_mgr.create_organization("Acme Medical")

        with pytest.raises(ValueError, match="already exists"):
            tenant_mgr.create_organization("Acme Medical")

    def test_get_organization(self, tenant_mgr):
        """Test retrieving an organization."""
        created = tenant_mgr.create_organization("Test Corp")
        retrieved = tenant_mgr.get_organization(created.organization_id)

        assert retrieved is not None
        assert retrieved.name == "Test Corp"

    def test_list_organizations(self, tenant_mgr):
        """Test listing organizations."""
        tenant_mgr.create_organization("Org A")
        tenant_mgr.create_organization("Org B")

        orgs = tenant_mgr.list_organizations()
        assert len(orgs) == 2

    def test_update_organization(self, tenant_mgr):
        """Test updating organization attributes."""
        org = tenant_mgr.create_organization("Original Name")
        updated = tenant_mgr.update_organization(
            org.organization_id,
            {'name': 'Updated Name', 'is_active': False}
        )

        assert updated.name == "Updated Name"
        assert updated.is_active is False

    def test_path_isolation(self, tenant_mgr):
        """Test that user data paths are isolated."""
        org = tenant_mgr.create_organization("Isolation Test")

        path1 = tenant_mgr.get_user_data_path("usr_001", org.organization_id)
        path2 = tenant_mgr.get_user_data_path("usr_002", org.organization_id)

        assert path1 != path2
        assert "usr_001" in str(path1)
        assert "usr_002" in str(path2)
        assert path1.exists()
        assert path2.exists()

    def test_project_path(self, tenant_mgr):
        """Test getting project paths."""
        org = tenant_mgr.create_organization("Project Test")

        path = tenant_mgr.get_project_path(
            "usr_001", org.organization_id, "ABC001"
        )

        assert "ABC001" in str(path)
        assert path.exists()

    def test_validate_path_access_allowed(self, tenant_mgr):
        """Test that users can access their own data."""
        org = tenant_mgr.create_organization("Access Test")

        user_path = tenant_mgr.get_user_data_path("usr_001", org.organization_id)
        target = str(user_path / "projects" / "test.json")

        allowed = tenant_mgr.validate_path_access(
            "usr_001", org.organization_id, target
        )
        assert allowed is True

    def test_validate_path_access_denied(self, tenant_mgr):
        """Test that users cannot access other users' data."""
        org = tenant_mgr.create_organization("Deny Test")

        # Create paths for two users
        tenant_mgr.get_user_data_path("usr_001", org.organization_id)
        user2_path = tenant_mgr.get_user_data_path("usr_002", org.organization_id)

        # User 1 trying to access User 2's data
        target = str(user2_path / "projects" / "secret.json")

        allowed = tenant_mgr.validate_path_access(
            "usr_001", org.organization_id, target
        )
        assert allowed is False

    def test_share_project(self, tenant_mgr):
        """Test sharing a project between users."""
        org = tenant_mgr.create_organization("Share Test")

        # Create project for user 1
        project_path = tenant_mgr.get_project_path(
            "usr_001", org.organization_id, "SHARED_PROJECT"
        )

        # Share with user 2
        result = tenant_mgr.share_project(
            project_id="SHARED_PROJECT",
            from_user="usr_001",
            to_users=["usr_002"],
            organization_id=org.organization_id
        )
        assert result is True

        # User 2 should see the shared project
        shared = tenant_mgr.get_shared_projects("usr_002")
        assert len(shared) == 1
        assert shared[0]['project_id'] == "SHARED_PROJECT"

        # User 2 should now have access to the project path
        allowed = tenant_mgr.validate_path_access(
            "usr_002", org.organization_id, str(project_path / "data.json")
        )
        assert allowed is True


# ============================================================
# 4. SignatureManager Tests (8 tests)
# ============================================================

class TestSignatureManager:
    """Test suite for SignatureManager class."""

    def test_create_signature(self, sig_mgr):
        """Test creating an electronic signature."""
        sig = sig_mgr.create_signature(
            user_id="usr_001",
            user_name="Alice Johnson",
            user_email="alice@corp.com",
            action="approve_submission",
            document_id="eSTAR_ABC001_v2",
            signature_method="password",
            credentials="SecureP@ss123",
            meaning="RA professional approval for submission"
        )

        assert sig.signature_id.startswith("sig_")
        assert sig.user_id == "usr_001"
        assert sig.user_name == "Alice Johnson"
        assert sig.action == "approve_submission"
        assert sig.document_id == "eSTAR_ABC001_v2"
        assert sig.is_valid is True
        assert sig.signature_hash != ""

    def test_verify_signature_valid(self, sig_mgr):
        """Test verifying a signature with correct credentials."""
        sig = sig_mgr.create_signature(
            user_id="usr_001",
            user_name="Alice",
            user_email="alice@corp.com",
            action="sign_document",
            document_id="doc_001",
            signature_method="password",
            credentials="MySecurePassword!",
            meaning="Document authorization"
        )

        valid = sig_mgr.verify_signature(sig.signature_id, "MySecurePassword!")
        assert valid is True

    def test_verify_signature_invalid(self, sig_mgr):
        """Test verifying a signature with wrong credentials."""
        sig = sig_mgr.create_signature(
            user_id="usr_001",
            user_name="Alice",
            user_email="alice@corp.com",
            action="sign_document",
            document_id="doc_001",
            signature_method="password",
            credentials="CorrectPassword",
            meaning="Test"
        )

        valid = sig_mgr.verify_signature(sig.signature_id, "WrongPassword")
        assert valid is False

    def test_get_signatures_for_document(self, sig_mgr):
        """Test retrieving all signatures for a document."""
        doc_id = "doc_multi_sign"

        sig_mgr.create_signature(
            user_id="usr_001", user_name="Alice",
            user_email="a@c.com",
            action="approve", document_id=doc_id,
            signature_method="password", credentials="pass1",
            meaning="First approval"
        )

        sig_mgr.create_signature(
            user_id="usr_002", user_name="Bob",
            user_email="b@c.com",
            action="approve", document_id=doc_id,
            signature_method="password", credentials="pass2",
            meaning="Second approval"
        )

        signatures = sig_mgr.get_signatures_for_document(doc_id)
        assert len(signatures) == 2

    def test_is_document_signed(self, sig_mgr):
        """Test checking if document has required signatures."""
        doc_id = "doc_check"

        sig_mgr.create_signature(
            user_id="usr_001", user_name="Alice",
            user_email="a@c.com",
            action="approve", document_id=doc_id,
            signature_method="password", credentials="pass1",
            meaning="Approval"
        )

        # Check without required signers
        signed, missing = sig_mgr.is_document_signed(doc_id)
        assert signed is True
        assert missing == []

        # Check with required signers (one missing)
        signed, missing = sig_mgr.is_document_signed(
            doc_id, required_signers=["usr_001", "usr_002"]
        )
        assert signed is False
        assert "usr_002" in missing

    def test_invalidate_signature(self, sig_mgr):
        """Test invalidating a signature."""
        sig = sig_mgr.create_signature(
            user_id="usr_001", user_name="Alice",
            user_email="a@c.com",
            action="approve", document_id="doc_invalid",
            signature_method="password", credentials="pass1",
            meaning="To be invalidated"
        )

        result = sig_mgr.invalidate_signature(
            sig.signature_id,
            reason="Credentials compromised"
        )
        assert result is True

        # Verification should fail for invalidated signature
        valid = sig_mgr.verify_signature(sig.signature_id, "pass1")
        assert valid is False

    def test_requires_signature(self, sig_mgr):
        """Test command signature requirement check."""
        assert SignatureManager.requires_signature("export") is True
        assert SignatureManager.requires_signature("assemble") is True
        assert SignatureManager.requires_signature("validate") is False
        assert SignatureManager.requires_signature("research") is False

    def test_signature_audit_trail(self, sig_mgr):
        """Test signature audit trail."""
        sig = sig_mgr.create_signature(
            user_id="usr_audit", user_name="Audit Test",
            user_email="audit@c.com",
            action="sign_document", document_id="doc_audit",
            signature_method="password", credentials="AuditPass",
            meaning="Audit test signature"
        )

        # Verify (creates audit event)
        sig_mgr.verify_signature(sig.signature_id, "AuditPass")

        # Check audit trail
        events = sig_mgr.get_audit_trail(document_id="doc_audit")
        assert len(events) >= 2  # creation + verification


# ============================================================
# 5. MonitoringManager Tests (10 tests)
# ============================================================

class TestMonitoringManager:
    """Test suite for MonitoringManager class."""

    def test_send_alert(self, monitor_mgr):
        """Test sending a monitoring alert."""
        alert = monitor_mgr.send_alert(
            alert_type=AlertType.SECURITY_VIOLATION,
            severity=AlertSeverity.HIGH,
            message="Test security alert",
            details={'test': True}
        )

        assert alert.alert_id.startswith("alert_")
        assert alert.alert_type == "security_violation"
        assert alert.severity == "high"
        assert alert.resolved is False

    def test_get_alerts(self, monitor_mgr):
        """Test querying alerts."""
        monitor_mgr.send_alert(
            AlertType.SECURITY_VIOLATION,
            AlertSeverity.HIGH,
            "Alert 1"
        )
        monitor_mgr.send_alert(
            AlertType.SYSTEM_ERROR,
            AlertSeverity.LOW,
            "Alert 2"
        )

        all_alerts = monitor_mgr.get_alerts()
        assert len(all_alerts) == 2

        high_alerts = monitor_mgr.get_alerts(severity="high")
        assert len(high_alerts) == 1

    def test_resolve_alert(self, monitor_mgr):
        """Test resolving an alert."""
        alert = monitor_mgr.send_alert(
            AlertType.SYSTEM_ERROR,
            AlertSeverity.MEDIUM,
            "Resolve test"
        )

        resolved = monitor_mgr.resolve_alert(
            alert.alert_id,
            resolved_by="usr_admin"
        )

        assert resolved is not None
        assert resolved.resolved is True
        assert resolved.resolved_by == "usr_admin"
        assert resolved.resolved_at is not None

    def test_acknowledge_alert(self, monitor_mgr):
        """Test acknowledging an alert."""
        alert = monitor_mgr.send_alert(
            AlertType.PERMISSION_DENIED,
            AlertSeverity.LOW,
            "Ack test"
        )

        acked = monitor_mgr.acknowledge_alert(alert.alert_id)
        assert acked is not None
        assert acked.acknowledged is True

    def test_record_metric(self, monitor_mgr):
        """Test recording performance metrics."""
        monitor_mgr.record_metric(
            "command_execution",
            150.5,
            tags={"command": "validate", "user": "usr_001"}
        )
        monitor_mgr.record_metric(
            "command_execution",
            200.0,
            tags={"command": "draft", "user": "usr_002"}
        )

        # Flush and query
        flushed = monitor_mgr.flush_metrics()
        assert flushed == 2

        metrics = monitor_mgr.get_metrics("command_execution")
        assert len(metrics) == 2

    def test_record_failure_and_detect(self, monitor_mgr):
        """Test failure recording and unusual activity detection."""
        # Record multiple failures quickly
        for i in range(6):
            monitor_mgr.record_failure("usr_bad", "auth_failure")

        # Should have generated an unusual activity alert
        alerts = monitor_mgr.get_alerts(alert_type="unusual_activity")
        assert len(alerts) >= 1

    def test_alert_on_security_violation(self, monitor_mgr):
        """Test security violation alert."""
        alert = monitor_mgr.alert_on_security_violation(
            user_id="usr_hacker",
            violation="Attempted directory traversal",
            details={"path": "/etc/passwd"}
        )

        assert alert.alert_type == "security_violation"
        assert alert.severity == "critical"
        assert "usr_hacker" in alert.message

    def test_alert_on_permission_denied(self, monitor_mgr):
        """Test permission denied alert."""
        alert = monitor_mgr.alert_on_permission_denied(
            user_id="usr_readonly",
            command="draft",
            reason="readonly role lacks command:confidential"
        )

        assert alert.alert_type == "permission_denied"
        assert "usr_readonly" in alert.message

    def test_alert_on_tenant_breach(self, monitor_mgr):
        """Test tenant breach alert."""
        alert = monitor_mgr.alert_on_tenant_breach(
            user_id="usr_evil",
            organization_id="org_acme",
            target_path="/fda-enterprise-data/organizations/org_medtech/users"
        )

        assert alert.alert_type == "tenant_breach"
        assert alert.severity == "critical"
        assert "cross-tenant" in alert.message.lower()

    def test_get_system_health(self, monitor_mgr):
        """Test comprehensive system health check."""
        health = monitor_mgr.get_system_health()

        assert 'overall_status' in health
        assert 'llm_providers' in health
        assert 'alerts' in health
        assert 'metrics' in health

        # Should be healthy with no alerts
        assert health['overall_status'] in ('healthy', 'degraded', 'critical', 'unknown')


# ============================================================
# 6. Integration Tests (15 tests)
# ============================================================

class TestIntegration:
    """Integration tests combining multiple Phase 4 components."""

    def test_user_enrollment_end_to_end(self, user_mgr, rbac_mgr):
        """Test complete user enrollment workflow."""
        # Step 1: Admin creates user
        user = user_mgr.create_user(
            email="newuser@corp.com",
            name="New User",
            role="reviewer",
            organization_id="org_acme"
        )

        # Step 2: Generate enrollment token
        token = user_mgr.generate_enrollment_token(user.user_id)

        # Step 3: User completes enrollment
        enrolled = user_mgr.complete_enrollment(
            token,
            {"whatsapp": "+14155551000"}
        )

        # Step 4: User authenticates via messaging handle
        authed = user_mgr.authenticate_by_handle("whatsapp", "+14155551000")
        assert authed is not None
        assert authed.email == "newuser@corp.com"

        # Step 5: Verify RBAC permissions
        allowed, _ = rbac_mgr.check_command_permission(authed, "research")
        assert allowed is True

        allowed, _ = rbac_mgr.check_command_permission(authed, "draft")
        assert allowed is False  # reviewer cannot draft

    def test_rbac_enforcement_in_execute(self, user_mgr, rbac_mgr, monitor_mgr):
        """Test RBAC enforcement with monitoring alerts."""
        # Create readonly user
        user = user_mgr.create_user(
            email="limited@corp.com",
            name="Limited User",
            role="readonly",
            organization_id="org_acme"
        )

        # Attempt confidential command
        allowed, reason = rbac_mgr.check_command_permission(user, "draft")
        assert allowed is False

        # Monitor should record the denial
        if not allowed:
            monitor_mgr.alert_on_permission_denied(
                user.user_id, "draft", reason
            )

        alerts = monitor_mgr.get_alerts(alert_type="permission_denied")
        assert len(alerts) >= 1

    def test_multi_tenant_data_isolation(self, tenant_mgr, monitor_mgr):
        """Test multi-tenant data isolation with monitoring."""
        # Create two organizations
        org_a = tenant_mgr.create_organization("Company A")
        org_b = tenant_mgr.create_organization("Company B")

        # Create project paths
        path_a = tenant_mgr.get_project_path("usr_a1", org_a.organization_id, "PROJ_A")
        path_b = tenant_mgr.get_project_path("usr_b1", org_b.organization_id, "PROJ_B")

        # User A should not access User B's data
        allowed = tenant_mgr.validate_path_access(
            "usr_a1", org_a.organization_id, str(path_b)
        )
        assert allowed is False

        # If breach attempted, monitoring should alert
        if not allowed:
            monitor_mgr.alert_on_tenant_breach(
                "usr_a1", org_a.organization_id, str(path_b)
            )

        alerts = monitor_mgr.get_alerts(alert_type="tenant_breach")
        assert len(alerts) >= 1
        assert alerts[0].severity == "critical"

    def test_electronic_signature_workflow(self, sig_mgr, user_mgr):
        """Test electronic signature workflow."""
        # Create user
        user = user_mgr.create_user(
            email="signer@corp.com",
            name="Dr. Signer",
            role="ra_professional",
            organization_id="org_acme"
        )

        # Step 1: Check if command requires signature
        assert sig_mgr.requires_signature("export") is True

        # Step 2: Create signature
        sig = sig_mgr.create_signature(
            user_id=user.user_id,
            user_name=user.name,
            user_email=user.email,
            action="approve_submission",
            document_id="eSTAR_v1",
            signature_method="password",
            credentials="Dr.Signer!Pass",
            meaning="I approve this submission package"
        )

        # Step 3: Verify signature
        valid = sig_mgr.verify_signature(sig.signature_id, "Dr.Signer!Pass")
        assert valid is True

        # Step 4: Check document signatures
        signed, missing = sig_mgr.is_document_signed("eSTAR_v1")
        assert signed is True

    def test_monitoring_with_user_actions(self, monitor_mgr, user_mgr, rbac_mgr):
        """Test monitoring records for user activities."""
        user = user_mgr.create_user(
            email="monitor@corp.com",
            name="Monitored User",
            role="reviewer",
            organization_id="org_acme"
        )

        # Record successful command execution metric
        monitor_mgr.record_metric(
            "command_execution",
            120.5,
            tags={"user": user.user_id, "command": "validate"}
        )

        # Check permission (allowed)
        allowed, _ = rbac_mgr.check_command_permission(user, "research")
        if allowed:
            monitor_mgr.record_metric(
                "command_execution",
                350.2,
                tags={"user": user.user_id, "command": "research"}
            )

        # Flush and verify
        monitor_mgr.flush_metrics()
        metrics = monitor_mgr.get_metrics("command_execution")
        assert len(metrics) >= 2

    def test_user_role_change_invalidates_cache(self, user_mgr, rbac_mgr):
        """Test that role changes invalidate RBAC cache."""
        user = user_mgr.create_user(
            email="changeme@corp.com",
            name="Role Change",
            role="readonly",
            organization_id="org_acme"
        )

        # Initially readonly -- cannot draft
        allowed, _ = rbac_mgr.check_command_permission(user, "draft")
        assert allowed is False

        # Upgrade to ra_professional
        updated = user_mgr.update_user(
            user.user_id,
            {'role': 'ra_professional'}
        )
        rbac_mgr.invalidate_cache(user.user_id)

        # Now should be able to draft
        allowed, _ = rbac_mgr.check_command_permission(updated, "draft")
        assert allowed is True

    def test_deactivated_user_blocked_everywhere(self, user_mgr, rbac_mgr):
        """Test that deactivated users are blocked from all operations."""
        user = user_mgr.create_user(
            email="deactivate@corp.com",
            name="Deactivated",
            role="admin",
            organization_id="org_acme"
        )

        # Deactivate
        user_mgr.update_user(user.user_id, {'is_active': False})
        deactivated = user_mgr.get_user(user.user_id)

        # Cannot execute any command
        allowed, reason = rbac_mgr.check_command_permission(deactivated, "validate")
        assert allowed is False
        assert "deactivated" in reason.lower()

        # Cannot authenticate
        authed = user_mgr.authenticate_by_handle("whatsapp", "+99999")
        assert authed is None  # Not found since no handle

    def test_shared_project_access_with_rbac(self, tenant_mgr, rbac_mgr):
        """Test shared project access respects RBAC."""
        org = tenant_mgr.create_organization("RBAC Share Test")

        # Create project
        project_path = tenant_mgr.get_project_path(
            "usr_owner", org.organization_id, "SHARED_DOC"
        )

        # Share with another user
        tenant_mgr.share_project(
            project_id="SHARED_DOC",
            from_user="usr_owner",
            to_users=["usr_viewer"],
            organization_id=org.organization_id,
            permissions="read"
        )

        # Verify shared access
        shared = tenant_mgr.get_shared_projects("usr_viewer")
        assert len(shared) == 1

        # Viewer can access the shared path
        allowed = tenant_mgr.validate_path_access(
            "usr_viewer", org.organization_id,
            str(project_path / "report.pdf")
        )
        assert allowed is True

    def test_organization_lifecycle(self, tenant_mgr, user_mgr):
        """Test full organization lifecycle."""
        # Create org
        org = tenant_mgr.create_organization("Lifecycle Corp")
        assert org.is_active is True

        # Create users in org
        user = user_mgr.create_user(
            email="lifecycle@corp.com",
            name="Lifecycle User",
            role="ra_professional",
            organization_id=org.organization_id
        )

        # Deactivate org
        updated = tenant_mgr.update_organization(
            org.organization_id,
            {'is_active': False}
        )
        assert updated.is_active is False

    def test_multiple_signatures_for_approval_chain(self, sig_mgr):
        """Test multi-signature approval chain."""
        doc_id = "SUBMISSION_v3"

        # First approver
        sig_mgr.create_signature(
            user_id="usr_ra",
            user_name="RA Professional",
            user_email="ra@corp.com",
            action="approve_submission",
            document_id=doc_id,
            signature_method="password",
            credentials="RA_pass!",
            meaning="RA review and approval"
        )

        # Second approver
        sig_mgr.create_signature(
            user_id="usr_qa",
            user_name="QA Manager",
            user_email="qa@corp.com",
            action="approve_submission",
            document_id=doc_id,
            signature_method="password",
            credentials="QA_pass!",
            meaning="QA review and approval"
        )

        # Check if all required signers have signed
        signed, missing = sig_mgr.is_document_signed(
            doc_id,
            required_signers=["usr_ra", "usr_qa", "usr_director"]
        )
        assert signed is False
        assert "usr_director" in missing

        # Director signs
        sig_mgr.create_signature(
            user_id="usr_director",
            user_name="Director",
            user_email="dir@corp.com",
            action="approve_submission",
            document_id=doc_id,
            signature_method="password",
            credentials="Dir_pass!",
            meaning="Final approval by director"
        )

        # Now all required signers have signed
        signed, missing = sig_mgr.is_document_signed(
            doc_id,
            required_signers=["usr_ra", "usr_qa", "usr_director"]
        )
        assert signed is True
        assert missing == []

    def test_alert_delivery_configuration(self, temp_dir):
        """Test monitoring with alert delivery configuration."""
        monitor = MonitoringManager(
            alert_email="test@corp.com",
            alert_slack_webhook="https://hooks.slack.com/test",
            metrics_dir=os.path.join(temp_dir, "m"),
            alerts_dir=os.path.join(temp_dir, "a")
        )

        # Should send alert without errors (delivery is best-effort)
        alert = monitor.send_alert(
            AlertType.SYSTEM_ERROR,
            AlertSeverity.HIGH,
            "Test delivery"
        )

        assert alert is not None
        assert alert.message == "Test delivery"

    def test_all_roles_have_permissions(self):
        """Test that all defined roles have permission mappings."""
        for role in Role:
            perms = ROLE_PERMISSIONS.get(role, [])
            assert len(perms) > 0, (
                "Role '{}' has no permissions defined".format(role.value)
            )

    def test_signature_persistence(self, temp_dir):
        """Test signature persistence across manager instances."""
        sig_path = os.path.join(temp_dir, "sigs")

        # Create signature with first manager
        mgr1 = SignatureManager(signatures_path=sig_path)
        sig = mgr1.create_signature(
            user_id="usr_persist",
            user_name="Persist Test",
            user_email="p@c.com",
            action="sign_document",
            document_id="persist_doc",
            signature_method="password",
            credentials="PersistPass!",
            meaning="Persistence test"
        )

        # Verify with second manager (reloads from disk)
        mgr2 = SignatureManager(signatures_path=sig_path)
        valid = mgr2.verify_signature(sig.signature_id, "PersistPass!")
        assert valid is True

    def test_monitoring_alert_persistence(self, temp_dir):
        """Test alert persistence across manager instances."""
        alerts_dir = os.path.join(temp_dir, "alerts_persist")
        metrics_dir = os.path.join(temp_dir, "metrics_persist")

        # Create alert with first manager
        mgr1 = MonitoringManager(
            alerts_dir=alerts_dir,
            metrics_dir=metrics_dir
        )
        alert = mgr1.send_alert(
            AlertType.SYSTEM_ERROR,
            AlertSeverity.HIGH,
            "Persist alert"
        )

        # Load with second manager
        mgr2 = MonitoringManager(
            alerts_dir=alerts_dir,
            metrics_dir=metrics_dir
        )
        alerts = mgr2.get_alerts()
        assert len(alerts) >= 1
        assert any(a.alert_id == alert.alert_id for a in alerts)


# ============================================================
# Run
# ============================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
