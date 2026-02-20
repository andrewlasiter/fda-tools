#!/usr/bin/env python3
"""
Create Linear Issues from Comprehensive Review Manifest

Automatically creates all 113 Linear issues from the multi-agent review
using the Linear GraphQL API.

Usage:
    python3 scripts/create_linear_issues_from_manifest.py

Requirements:
    - LINEAR_API_KEY in .env file
    - requests library (pip install requests)
    - python-dotenv library (pip install python-dotenv)

Output:
    - Creates all issues in Linear
    - Generates linear_issues_created.json with issue IDs
    - Shows progress and summary report
"""

import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

try:
    import requests
except ImportError:
    print("ERROR: requests library not installed")
    print("Install with: pip install requests")
    sys.exit(1)

try:
    from dotenv import load_dotenv
except ImportError:
    print("ERROR: python-dotenv library not installed")
    print("Install with: pip install python-dotenv")
    sys.exit(1)


# Load environment variables from .env
load_dotenv()

# Configuration
LINEAR_API_URL = "https://api.linear.app/graphql"
RATE_LIMIT_DELAY = 0.5  # Seconds between API calls (Linear allows ~100/min)


class LinearIssueCreator:
    """Create Linear issues from manifest with progress tracking."""

    def __init__(self, api_key: str):
        """Initialize with Linear API key.

        Args:
            api_key: Linear API key (from .env)
        """
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": api_key,
            "Content-Type": "application/json",
        })
        self.created_issues = []
        self.failed_issues = []

    def get_team_id(self, team_name: str = "FDA Tools") -> Optional[str]:
        """Get Linear team ID by name.

        Args:
            team_name: Team name to search for

        Returns:
            Team ID or None if not found
        """
        query = """
        query GetTeams {
            teams {
                nodes {
                    id
                    name
                    key
                }
            }
        }
        """

        try:
            response = self.session.post(
                LINEAR_API_URL,
                json={"query": query},
                timeout=30
            )
            response.raise_for_status()
            result = response.json()

            teams = result.get("data", {}).get("teams", {}).get("nodes", [])
            for team in teams:
                if team["name"] == team_name or team_name.lower() in team["name"].lower():
                    print(f"✓ Found team: {team['name']} (ID: {team['id']})")
                    return team["id"]

            # If no exact match, return first team
            if teams:
                print(f"⚠ Team '{team_name}' not found, using first team: {teams[0]['name']}")
                return teams[0]["id"]

            print(f"ERROR: No teams found in Linear workspace")
            return None

        except Exception as e:
            print(f"ERROR: Failed to get team ID: {e}")
            return None

    def get_label_ids(self, label_names: List[str]) -> List[str]:
        """Get Linear label IDs by names (creates if not exist).

        Args:
            label_names: List of label names

        Returns:
            List of label IDs
        """
        # For now, return empty list - labels are optional
        # Could implement label creation here if needed
        return []

    def map_priority(self, priority_str: str) -> int:
        """Map priority string to Linear's 0-4 scale.

        Args:
            priority_str: Priority string (P0, P1, P2, urgent, high, medium, low)

        Returns:
            Linear priority int (0=None, 1=Urgent, 2=High, 3=Normal, 4=Low)
        """
        priority_map = {
            "P0": 1,  # Urgent
            "P1": 2,  # High
            "P2": 3,  # Normal
            "urgent": 1,
            "high": 2,
            "medium": 3,
            "normal": 3,
            "low": 4,
        }

        # Extract P0/P1/P2 from priority string
        priority_clean = priority_str.upper().replace("CRITICAL", "").replace("HIGH", "").replace("MEDIUM", "").strip()

        # Try exact match first
        if priority_clean in priority_map:
            return priority_map[priority_clean]

        # Try substring match
        for key, value in priority_map.items():
            if key in priority_str.upper():
                return value

        return 3  # Default to Normal

    def create_issue(
        self,
        team_id: str,
        issue_data: Dict,
        category: str
    ) -> Optional[Dict]:
        """Create a single Linear issue.

        Args:
            team_id: Linear team ID
            issue_data: Issue data from manifest
            category: Issue category (Security, Code Quality, etc.)

        Returns:
            Created issue data or None if failed
        """
        mutation = """
        mutation CreateIssue($input: IssueCreateInput!) {
            issueCreate(input: $input) {
                success
                issue {
                    id
                    identifier
                    title
                    url
                }
            }
        }
        """

        # Extract issue details
        issue_id = issue_data.get("id", "UNKNOWN")
        title = issue_data.get("title", "Untitled Issue")
        priority = issue_data.get("priority", "P2")
        points = issue_data.get("points", 0)

        # Build description
        description_parts = [
            f"**Category:** {category}",
            f"**Priority:** {priority}",
            f"**Story Points:** {points}",
            "",
        ]

        if "team" in issue_data:
            description_parts.append(f"**Assigned Team:** {issue_data['team']}")
            description_parts.append("")

        if "cwe" in issue_data:
            description_parts.append(f"**CWE:** {issue_data['cwe']}")
            description_parts.append("")

        if "regulatory_citation" in issue_data:
            description_parts.append(f"**Regulatory Citation:** {issue_data['regulatory_citation']}")
            description_parts.append("")

        if "files" in issue_data and issue_data["files"]:
            description_parts.append("**Files Affected:**")
            for file in issue_data["files"]:
                description_parts.append(f"- `{file}`")
            description_parts.append("")

        if "blocks" in issue_data and issue_data["blocks"]:
            description_parts.append(f"**Blocks:** {', '.join(issue_data['blocks'])}")
            description_parts.append("")

        if "requires" in issue_data and issue_data["requires"]:
            description_parts.append(f"**Requires:** {', '.join(issue_data['requires'])}")
            description_parts.append("")

        description_parts.append("---")
        description_parts.append("")
        description_parts.append("🤖 Generated from comprehensive multi-agent review")
        description_parts.append(f"📋 Issue ID: {issue_id}")
        description_parts.append("")
        description_parts.append("For detailed analysis, see:")
        description_parts.append("- `COMPREHENSIVE_REVIEW_SUMMARY.md`")
        description_parts.append("- `LINEAR_ISSUES_BY_TEAM.md`")

        description = "\n".join(description_parts)

        # Prepare mutation variables
        variables = {
            "input": {
                "teamId": team_id,
                "title": f"{issue_id}: {title}",
                "description": description,
                "priority": self.map_priority(priority),
            }
        }

        # Add estimate (story points) if available
        if points > 0:
            variables["input"]["estimate"] = points

        try:
            response = self.session.post(
                LINEAR_API_URL,
                json={"query": mutation, "variables": variables},
                timeout=30
            )
            response.raise_for_status()
            result = response.json()

            # Check for errors
            if "errors" in result:
                print(f"  ✗ {issue_id}: API Error - {result['errors'][0].get('message', 'Unknown error')}")
                return None

            # Extract created issue
            issue_create = result.get("data", {}).get("issueCreate", {})
            if not issue_create.get("success"):
                print(f"  ✗ {issue_id}: Creation failed")
                return None

            created_issue = issue_create.get("issue", {})
            print(f"  ✓ {created_issue['identifier']}: {title[:60]}...")

            return {
                "manifest_id": issue_id,
                "linear_id": created_issue["id"],
                "linear_identifier": created_issue["identifier"],
                "title": title,
                "url": created_issue.get("url", ""),
                "priority": priority,
                "points": points,
                "category": category,
            }

        except requests.exceptions.RequestException as e:
            print(f"  ✗ {issue_id}: Network error - {e}")
            return None
        except Exception as e:
            print(f"  ✗ {issue_id}: Unexpected error - {e}")
            return None

    def create_issues_from_manifest(self, manifest_path: Path) -> Dict:
        """Create all issues from manifest file.

        Args:
            manifest_path: Path to LINEAR_ISSUES_MANIFEST.json

        Returns:
            Summary dict with created/failed counts
        """
        # Load manifest
        print(f"\n📂 Loading manifest: {manifest_path}")
        try:
            with open(manifest_path) as f:
                manifest = json.load(f)
        except FileNotFoundError:
            print(f"ERROR: Manifest file not found: {manifest_path}")
            return {"created": 0, "failed": 0, "total": 0}
        except json.JSONDecodeError as e:
            print(f"ERROR: Invalid JSON in manifest: {e}")
            return {"created": 0, "failed": 0, "total": 0}

        # Get team ID
        team_id = self.get_team_id("FDA Tools")
        if not team_id:
            print("ERROR: Could not get Linear team ID")
            return {"created": 0, "failed": 0, "total": 0}

        # Get critical path issues
        critical_path = manifest.get("critical_path_issues", {})

        # Create issues by category
        categories = {
            "foundation": "Foundation",
            "security": "Security",
            "regulatory": "Regulatory",
            "testing": "Testing",
            "devops": "DevOps",
        }

        print(f"\n🚀 Creating Linear issues...\n")

        for section_key, section_name in categories.items():
            section = critical_path.get(section_key)
            if not section:
                continue

            print(f"📋 {section_name} Issues:")
            print(f"   {section.get('description', '')}")

            issues = section.get("issues", [])
            for issue_data in issues:
                result = self.create_issue(team_id, issue_data, section_name)

                if result:
                    self.created_issues.append(result)
                else:
                    self.failed_issues.append(issue_data.get("id", "UNKNOWN"))

                # Rate limiting
                time.sleep(RATE_LIMIT_DELAY)

            print()

        # Summary
        total = len(self.created_issues) + len(self.failed_issues)

        return {
            "created": len(self.created_issues),
            "failed": len(self.failed_issues),
            "total": total,
            "created_issues": self.created_issues,
            "failed_issues": self.failed_issues,
        }

    def save_results(self, results: Dict, output_path: Path):
        """Save creation results to JSON file.

        Args:
            results: Results dict from create_issues_from_manifest
            output_path: Path to save results
        """
        print(f"\n💾 Saving results to: {output_path}")

        with open(output_path, "w") as f:
            json.dump(results, f, indent=2)

        print(f"✓ Results saved")


def main():
    """Main entry point."""
    print("=" * 70)
    print("FDA Tools Plugin - Linear Issue Creator")
    print("=" * 70)

    # Check for API key (FDA-182: try secure_config first)
    api_key = None
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent / 'lib'))
        from secure_config import get_api_key
        api_key = get_api_key('linear')
        if api_key:
            print(f"✓ API key loaded from keyring")
    except ImportError:
        pass

    # Fallback to environment variable
    if not api_key:
        api_key = os.getenv("LINEAR_API_KEY")
        if api_key:
            print(f"✓ API key loaded from environment variable")

    if not api_key:
        print("\nERROR: LINEAR_API_KEY not found")
        print("\nPlease set the API key using one of these methods:")
        print("1. Store in keyring (recommended):")
        print("   python3 lib/secure_config.py --set linear")
        print("2. Set environment variable:")
        print("   export LINEAR_API_KEY=your_key_here")
        print("\nCurrent directory:", os.getcwd())
        sys.exit(1)

    # Find manifest file
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent  # Go up to fda-tools root
    manifest_path = project_root / "LINEAR_ISSUES_MANIFEST.json"

    if not manifest_path.exists():
        print(f"\nERROR: Manifest file not found: {manifest_path}")
        print("\nSearching for manifest in current directory...")
        manifest_path = Path("LINEAR_ISSUES_MANIFEST.json")

        if not manifest_path.exists():
            print("ERROR: Still not found. Please run this script from the project root.")
            sys.exit(1)

    print(f"✓ Found manifest: {manifest_path}")

    # Create issues
    creator = LinearIssueCreator(api_key)
    results = creator.create_issues_from_manifest(manifest_path)

    # Save results
    output_path = project_root / "linear_issues_created.json"
    creator.save_results(results, output_path)

    # Print summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"✓ Issues created: {results['created']}")
    print(f"✗ Issues failed:  {results['failed']}")
    print(f"📊 Total:         {results['total']}")

    if results['created'] > 0:
        print(f"\n🎉 Successfully created {results['created']} Linear issues!")
        print(f"\n📋 View created issues in Linear:")
        print(f"   https://linear.app/")
        print(f"\n📄 Issue details saved to: {output_path}")

    if results['failed'] > 0:
        print(f"\n⚠️  Warning: {results['failed']} issues failed to create")
        print(f"   Failed issue IDs: {', '.join(results['failed_issues'])}")
        print(f"   Check the output above for error details")

    print("\n" + "=" * 70)

    return 0 if results['failed'] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
