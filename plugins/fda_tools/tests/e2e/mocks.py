"""
Mock Objects for End-to-End Tests
==================================

Provides mock implementations of external dependencies for E2E testing:
- FDA API clients
- Linear API clients
- File system operations
- Network requests
- External services

Version: 1.0.0
Date: 2026-02-20
Issue: FDA-186
"""

from typing import Any, Dict, List, Optional, Callable
from pathlib import Path
import json
import time
from unittest.mock import Mock, MagicMock


# =============================================================================
# Mock FDA API Client
# =============================================================================

class MockFDAAPIClient:
    """Mock FDA openFDA API client for E2E testing.
    
    Simulates API responses without making real network calls.
    Supports rate limiting, error injection, and response customization.
    """
    
    def __init__(
        self,
        response_data: Optional[Dict[str, Any]] = None,
        error_mode: bool = False,
        rate_limit_mode: bool = False,
        delay_seconds: float = 0.0
    ):
        """Initialize mock FDA API client.
        
        Args:
            response_data: Predefined response data
            error_mode: If True, raise errors on API calls
            rate_limit_mode: If True, simulate rate limiting
            delay_seconds: Simulate API latency
        """
        self.response_data = response_data or {}
        self.error_mode = error_mode
        self.rate_limit_mode = rate_limit_mode
        self.delay_seconds = delay_seconds
        self.call_count = 0
        self.call_history: List[Dict[str, Any]] = []
        
    def query_devices(
        self,
        product_code: Optional[str] = None,
        k_number: Optional[str] = None,
        limit: int = 100,
        **kwargs
    ) -> Dict[str, Any]:
        """Mock device clearance query.
        
        Args:
            product_code: Product code filter
            k_number: K-number filter
            limit: Result limit
            **kwargs: Additional query parameters
            
        Returns:
            Mock API response
            
        Raises:
            Exception: If error_mode is enabled
        """
        self.call_count += 1
        self.call_history.append({
            "method": "query_devices",
            "product_code": product_code,
            "k_number": k_number,
            "limit": limit,
            "kwargs": kwargs,
            "timestamp": time.time()
        })
        
        # Simulate API delay
        if self.delay_seconds > 0:
            time.sleep(self.delay_seconds)
        
        # Simulate errors
        if self.error_mode:
            raise Exception("FDA API Error: Service unavailable")
        
        # Simulate rate limiting
        if self.rate_limit_mode and self.call_count > 5:
            raise Exception("FDA API Error: Rate limit exceeded")
        
        # Return configured response or default
        key = product_code or k_number or "default"
        return self.response_data.get(key, {
            "meta": {"results": {"total": 0}},
            "results": []
        })
    
    def query_recalls(
        self,
        product_code: Optional[str] = None,
        k_number: Optional[str] = None,
        limit: int = 100,
        **kwargs
    ) -> Dict[str, Any]:
        """Mock recall query.
        
        Args:
            product_code: Product code filter
            k_number: K-number filter
            limit: Result limit
            **kwargs: Additional query parameters
            
        Returns:
            Mock API response
        """
        self.call_count += 1
        self.call_history.append({
            "method": "query_recalls",
            "product_code": product_code,
            "k_number": k_number,
            "limit": limit,
            "timestamp": time.time()
        })
        
        if self.error_mode:
            raise Exception("FDA API Error: Service unavailable")
        
        return self.response_data.get(f"{product_code}_recalls", {
            "meta": {"results": {"total": 0}},
            "results": []
        })
    
    def reset(self):
        """Reset call counters and history."""
        self.call_count = 0
        self.call_history.clear()


# =============================================================================
# Mock Configuration Manager
# =============================================================================

class MockConfigManager:
    """Mock configuration manager for E2E tests.
    
    Provides configuration without file I/O.
    """
    
    def __init__(self, config_data: Optional[Dict[str, Any]] = None):
        """Initialize mock config manager.
        
        Args:
            config_data: Configuration data to return
        """
        self.config_data = config_data or {
            "api": {
                "rate_limit": 60,
                "timeout": 30,
                "retry_count": 3
            },
            "paths": {
                "data_dir": "data",
                "draft_dir": "draft",
                "reports_dir": "reports"
            },
            "features": {
                "auto_refresh": False,
                "enable_cache": True,
                "parallel_processing": False
            }
        }
        self.load_count = 0
        self.save_count = 0
    
    def load_config(self, config_path: Optional[Path] = None) -> Dict[str, Any]:
        """Load configuration.
        
        Args:
            config_path: Path to config file (ignored)
            
        Returns:
            Configuration dict
        """
        self.load_count += 1
        return self.config_data.copy()
    
    def save_config(self, config_data: Dict[str, Any], config_path: Optional[Path] = None):
        """Save configuration.
        
        Args:
            config_data: Configuration to save
            config_path: Path to save to (ignored)
        """
        self.save_count += 1
        self.config_data = config_data.copy()
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value.
        
        Args:
            key: Dot-notation key (e.g., "api.rate_limit")
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        keys = key.split(".")
        value = self.config_data
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value


# =============================================================================
# Mock Linear API Client
# =============================================================================

class MockLinearClient:
    """Mock Linear API client for E2E tests."""
    
    def __init__(self, success: bool = True):
        """Initialize mock Linear client.
        
        Args:
            success: If True, operations succeed; if False, they fail
        """
        self.success = success
        self.created_issues: List[Dict[str, Any]] = []
        self.updated_issues: List[Dict[str, Any]] = []
        
    def create_issue(
        self,
        title: str,
        description: str,
        labels: Optional[List[str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Create mock Linear issue.
        
        Args:
            title: Issue title
            description: Issue description
            labels: Issue labels
            **kwargs: Additional fields
            
        Returns:
            Mock issue data
            
        Raises:
            Exception: If success is False
        """
        if not self.success:
            raise Exception("Linear API Error: Failed to create issue")
        
        issue = {
            "id": f"ISSUE-{len(self.created_issues) + 1}",
            "title": title,
            "description": description,
            "labels": labels or [],
            "state": "todo",
            **kwargs
        }
        
        self.created_issues.append(issue)
        return issue
    
    def update_issue(self, issue_id: str, **kwargs) -> Dict[str, Any]:
        """Update mock Linear issue.
        
        Args:
            issue_id: Issue ID to update
            **kwargs: Fields to update
            
        Returns:
            Updated issue data
        """
        if not self.success:
            raise Exception("Linear API Error: Failed to update issue")
        
        update = {"id": issue_id, **kwargs}
        self.updated_issues.append(update)
        return update


# =============================================================================
# Mock Rate Limiter
# =============================================================================

class MockRateLimiter:
    """Mock rate limiter for E2E tests."""
    
    def __init__(self, rate_limit: int = 60, enforce: bool = False):
        """Initialize mock rate limiter.
        
        Args:
            rate_limit: Requests per minute
            enforce: If True, actually enforce rate limiting
        """
        self.rate_limit = rate_limit
        self.enforce = enforce
        self.request_count = 0
        self.request_times: List[float] = []
        
    def acquire(self):
        """Acquire rate limit token.
        
        Raises:
            Exception: If enforce=True and rate limit exceeded
        """
        self.request_count += 1
        current_time = time.time()
        self.request_times.append(current_time)
        
        if self.enforce:
            # Check requests in last minute
            minute_ago = current_time - 60
            recent_requests = [t for t in self.request_times if t > minute_ago]
            
            if len(recent_requests) > self.rate_limit:
                raise Exception("Rate limit exceeded")
    
    def reset(self):
        """Reset rate limiter."""
        self.request_count = 0
        self.request_times.clear()


# =============================================================================
# Mock File System Operations
# =============================================================================

class MockFileSystem:
    """Mock file system for E2E tests.
    
    Simulates file operations in memory without disk I/O.
    """
    
    def __init__(self):
        """Initialize mock file system."""
        self.files: Dict[str, bytes] = {}
        self.directories: set = set()
        
    def write_file(self, path: Path, content: bytes):
        """Write file to mock filesystem.
        
        Args:
            path: File path
            content: File content
        """
        self.files[str(path)] = content
        
        # Add parent directories
        parent = path.parent
        while parent != parent.parent:
            self.directories.add(str(parent))
            parent = parent.parent
    
    def read_file(self, path: Path) -> bytes:
        """Read file from mock filesystem.
        
        Args:
            path: File path
            
        Returns:
            File content
            
        Raises:
            FileNotFoundError: If file doesn't exist
        """
        path_str = str(path)
        if path_str not in self.files:
            raise FileNotFoundError(f"File not found: {path}")
        
        return self.files[path_str]
    
    def exists(self, path: Path) -> bool:
        """Check if file or directory exists.
        
        Args:
            path: Path to check
            
        Returns:
            True if exists
        """
        path_str = str(path)
        return path_str in self.files or path_str in self.directories
    
    def mkdir(self, path: Path, parents: bool = False, exist_ok: bool = False):
        """Create directory in mock filesystem.
        
        Args:
            path: Directory path
            parents: Create parent directories
            exist_ok: Don't raise error if exists
        """
        path_str = str(path)
        
        if path_str in self.directories and not exist_ok:
            raise FileExistsError(f"Directory exists: {path}")
        
        self.directories.add(path_str)
        
        if parents:
            parent = path.parent
            while parent != parent.parent:
                self.directories.add(str(parent))
                parent = parent.parent
    
    def clear(self):
        """Clear all files and directories."""
        self.files.clear()
        self.directories.clear()


# =============================================================================
# Factory Functions
# =============================================================================

def create_mock_fda_client(
    product_code: str = "DQY",
    result_count: int = 5,
    error_mode: bool = False
) -> MockFDAAPIClient:
    """Factory function to create configured mock FDA client.
    
    Args:
        product_code: Product code to mock
        result_count: Number of results to return
        error_mode: Enable error simulation
        
    Returns:
        Configured MockFDAAPIClient
    """
    response_data = {
        product_code: {
            "meta": {"results": {"total": result_count}},
            "results": [
                {
                    "k_number": f"K2024{i:04d}",
                    "device_name": f"Test Device {i}",
                    "applicant": "Test Manufacturer",
                    "decision_date": "2024-01-15",
                    "product_code": product_code
                }
                for i in range(1, result_count + 1)
            ]
        }
    }
    
    return MockFDAAPIClient(
        response_data=response_data,
        error_mode=error_mode
    )


def create_mock_config(
    custom_config: Optional[Dict[str, Any]] = None
) -> MockConfigManager:
    """Factory function to create configured mock config manager.
    
    Args:
        custom_config: Custom configuration to merge with defaults
        
    Returns:
        Configured MockConfigManager
    """
    manager = MockConfigManager()
    
    if custom_config:
        manager.config_data.update(custom_config)
    
    return manager
