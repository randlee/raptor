#!/usr/bin/env python3
"""
Documentation Extraction Pipeline
Extracts requirements and ADRs from markdown documentation files.

Architecture: Three-agent system
- Agent 1: File Processing & Metadata Extraction
- Agent 2: Content Parsing & Cross-Reference Building
- Agent 3: Validation & Index Building
"""

import os
import re
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import markdown
import sys
import argparse
import tomllib

# Windows compatibility: Configure UTF-8 output encoding
if sys.platform == 'win32':
    try:
        # Try to reconfigure stdout to use UTF-8 on Windows
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        # If reconfigure fails, continue (will use ASCII fallbacks if needed)
        pass

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from schema.record import Record


# ============================================================================
# DOMAIN MAPPING CONFIGURATION
# ============================================================================

# Maps domain directory names to short domain codes
# Used for domain attribution in test plan parsing
DOMAIN_MAP = {
    'calibration': 'cal',
    'camera': 'cam',
    'database': 'db',
    'avalonia': 'avui',    'performance': 'perf',
    'regions': 'reg',
    'sequencer': 'seq',
    'ui': 'ui',
}


def derive_domain_from_path(file_path: str, project_root: str) -> str:
    """
    Derives domain code from file path using DOMAIN_MAP.

    Extracts the first path component after project root and maps it to
    the corresponding domain code (cal, cam, db, perf, reg, seq, ui).

    Args:
        file_path: Absolute or relative path to the test plan file
        project_root: Path to project root directory

    Returns:
        Domain code string (e.g., 'cal', 'cam') or 'unknown' if not mapped

    Examples:
        /project/calibration/test/test-dark.md → 'cal'
        /project/camera/test/test-focus.md → 'cam'
        /project/unknown_folder/test/test-x.md → 'unknown'
    """
    try:
        # Convert to Path objects for cross-platform compatibility
        file_path_obj = Path(file_path)
        project_root_obj = Path(project_root)

        # Get relative path from project root
        relative_path = file_path_obj.relative_to(project_root_obj)

        # Extract first path component (domain folder)
        # Example: calibration/test/test-dark.md → 'calibration'
        domain_folder = relative_path.parts[0]

        # Map to domain code using DOMAIN_MAP
        domain_code = DOMAIN_MAP.get(domain_folder, 'unknown')

        return domain_code

    except (ValueError, IndexError) as e:
        # ValueError: file_path not relative to project_root
        # IndexError: empty path parts
        print(f"Warning: Could not derive domain from path {file_path}: {e}")
        return 'unknown'


# ============================================================================
# PROJECT ROOT & PATH UTILITIES
# ============================================================================

def get_project_root() -> Path:
    """
    Derives the project root dynamically from the script location.

    Script is in /scripts/ directory, so project root is one level up.

    Returns: Path object pointing to project root
    """
    script_path = Path(__file__).resolve()
    project_root = script_path.parents[1]  # Go up two levels: script -> scripts/ -> project/
    return project_root


def get_doc_paths(project_root: Path, domain: str) -> Dict[str, List[str]]:
    """
    Returns paths for requirements, test, and design folders for a given domain.

    Args:
        project_root: Path to project root directory
        domain: Domain name (cal, cam, db, perf, reg, seq, ui, mcp)

    Returns:
        Dict with 'target_dirs' list containing all relevant documentation directories
    """
    # Domain name mapping (short names to full directory names)
    domain_map = {
        'cal': 'calibration',
        'cam': 'camera',
        'db': 'database',
        'perf': 'performance',
        'reg': 'regions',
        'seq': 'sequencer',
        'ui': 'ui',
        'mcp': 'mcp'
    }

    # Get full domain directory name
    domain_dir = domain_map.get(domain, domain)

    # Standard subdirectories to check
    subdirs = ['requirements', 'architecture', 'design', 'test', 'schema']

    # Build target directories (only include those that exist)
    target_dirs = []
    for subdir in subdirs:
        path = project_root / domain_dir / subdir
        if path.exists():
            target_dirs.append(str(path))

    return {'target_dirs': target_dirs, 'domain_dir': domain_dir}


def validate_project_root(project_root: Path) -> bool:
    """
    Validates that the provided path looks like a valid project root.

    Checks for presence of expected directories/files:
    - calibration/, database/, performance/, etc.
    - scripts/ directory

    Args:
        project_root: Path to validate

    Returns:
        True if valid, False otherwise
    """
    # Check for at least one domain directory
    expected_domains = ['calibration', 'database', 'performance', 'camera', 'regions', 'sequencer', 'ui', 'mcp', 'avalonia']
    has_domain = any((project_root / domain).exists() for domain in expected_domains)

    # Check for scripts directory
    has_scripts = (project_root / 'scripts').exists()

    return has_domain and has_scripts


# ============================================================================
# AGENT 1: File Processing & Metadata Extraction
# ============================================================================

def is_test_plan(file_path: str) -> bool:
    """
    Determines if a file is a test plan based on path and filename.

    Test plans are identified by:
    - Located in /calibration/test/ directory
    - Filename starts with "test-"
    - Has .md extension

    Returns: True if file is a test plan, False otherwise
    """
    # Normalize path using Path for cross-platform compatibility
    # Path.parts splits the path into components regardless of separator (/ or \)
    # Note: We normalize separators first to handle paths from different systems
    normalized_path = file_path.replace('\\', '/')
    path = Path(normalized_path)

    # Check if 'test' is in any part of the path (works on Windows, macOS, Linux)
    # This replaces string check '/test/' which only works on Unix-like systems
    if 'test' not in path.parts:
        return False

    # Check if filename starts with "test-" using Path.name (platform-independent)
    # Path.name returns the final component of the path
    if not path.name.startswith('test-'):
        return False

    # Check if it's a markdown file using Path.suffix (platform-independent)
    # Path.suffix returns the file extension including the dot
    if path.suffix != '.md':
        return False

    return True


def discover_markdown_files(base_dirs: List[str]) -> List[Tuple[str, str]]:
    """
    Discovers all .md files in target directories.

    Target directories:
    - calibration/requirements/, calibration/architecture/
    - database/requirements/, database/architecture/
    - performance/requirements/, performance/architecture/, performance/design/
    - mcp/requirements/, mcp/architecture/, mcp/design/
    - camera/requirements/, camera/architecture/, camera/design/
    - regions/requirements/, regions/architecture/, regions/design/
    - sequencer/requirements/, sequencer/architecture/, sequencer/design/
    - ui/requirements/, ui/architecture/, ui/design/

    Returns: List of (file_path, domain) tuples
    """
    files = []

    # Domain mapping for path to domain name
    domain_map = {
        "calibration": "calibration",
        "database": "database",
        "performance": "performance",
        "mcp": "mcp",
        "camera": "camera",
        "regions": "regions",
        "sequencer": "sequencer",
        "ui": "ui",
        "avalonia": "avalonia"
    }
    for base_dir in base_dirs:
        if not os.path.exists(base_dir):
            print(f"Warning: Directory not found: {base_dir}")
            continue

        # Determine domain from path by checking path segments (cross-platform)
        # Use Path.parts instead of string matching for Windows compatibility
        base_path = Path(base_dir)
        domain = None
        for domain_name in domain_map.keys():
            if domain_name in base_path.parts:
                domain = domain_map[domain_name]
                break

        if not domain:
            domain = base_path.name

        # Recursively find all .md files
        for root, dirs, filenames in os.walk(base_dir):
            for filename in filenames:
                if filename.endswith('.md'):
                    file_path = os.path.join(root, filename)
                    files.append((file_path, domain))
                    print(f"Discovered: {file_path} (domain: {domain})")

    return files


def extract_test_plans(doc_folder: str) -> List[str]:
    """
    Finds all test plan files recursively across ALL domains.

    P2-1 Enhancement: Recursive test plan discovery
    - Uses Path.rglob() for cross-platform recursive file discovery
    - Searches entire project root (not just calibration/)
    - Filters using 'test' in path.parts to ensure test directories only
    - Domain attribution handled by parse_test_plan() (P2-1a)

    Args:
        doc_folder: Project root directory path

    Returns: List of test plan file paths
    """
    test_plans = []
    doc_root = Path(doc_folder)

    # P2-1: Recursive discovery across ALL domains using rglob()
    # This finds test-*.md files in any domain (calibration, camera, database, etc.)
    for file_path in doc_root.rglob('test-*.md'):
        # Filter: only include if 'test' is in path parts (ensures it's in a test/ directory)
        # This reuses the P1-2 logic from is_test_plan() for consistency
        if 'test' in file_path.parts:
            # Verify it's actually a test plan using our validation function
            if is_test_plan(str(file_path)):
                # P2-1a: Derive domain code for logging
                domain_code = derive_domain_from_path(str(file_path), doc_folder)

                # Get relative path for cleaner logging
                try:
                    rel_path = file_path.relative_to(doc_root)
                except ValueError:
                    rel_path = file_path

                test_plans.append(str(file_path))
                # P2-1a: Show domain attribution in logs
                print(f"✓ {rel_path} → {domain_code}")

    return test_plans


def parse_test_plan_id(id_string: str) -> Dict[str, any]:
    """
    Parses test plan ID string into canonical ID and range components.

    P2-4 Enhancement: Test plan ID normalization
    Separates canonical ID (for URLs) from range display (for UI).

    Args:
        id_string: Raw ID string from metadata (e.g., "TEST-CAL-1001 through TEST-CAL-1050")

    Returns:
        Dict with:
        - canonical_id: Canonical ID for URLs (e.g., "TEST-CAL-1001")
        - id_range: Full range string for display (e.g., "TEST-CAL-1001 through TEST-CAL-1050")
        - id_range_expanded: List of all IDs in range (e.g., 50 items)
        - range_start: Starting number (e.g., 1001)
        - range_end: Ending number (e.g., 1050)

    Examples:
        "TEST-CAL-1001 through TEST-CAL-1050" -> canonical_id="TEST-CAL-1001", range_start=1001, range_end=1050
        "TEST-CAL-1001" -> canonical_id="TEST-CAL-1001", range_start=1001, range_end=1001
    """
    # Check for range format: "TEST-XXX-#### through TEST-XXX-####"
    # Also handle "to" as an alternative to "through"
    range_match = re.match(r'^(TEST-[A-Z]+-\d{4})\s+(?:through|to)\s+(TEST-[A-Z]+-\d{4})$', id_string, re.IGNORECASE)

    if range_match:
        start_id = range_match.group(1)
        end_id = range_match.group(2)  # Now correctly group 2 (non-capturing group for "through|to")

        # Extract start and end numbers
        start_num_match = re.match(r'^TEST-[A-Z]+-(\d{4})$', start_id)
        end_num_match = re.match(r'^TEST-[A-Z]+-(\d{4})$', end_id)

        start_num = int(start_num_match.group(1)) if start_num_match else None
        end_num = int(end_num_match.group(1)) if end_num_match else None

        # Expand the range to full list of IDs
        id_range_expanded = expand_id_range(start_id, end_id)

        return {
            'canonical_id': start_id,  # Use start ID as canonical
            'id_range': id_string,  # Full range string for display
            'id_range_expanded': id_range_expanded,  # Array of all IDs in range
            'range_start': start_num,
            'range_end': end_num
        }
    else:
        # Single ID (no range)
        # Extract number from ID
        num_match = re.match(r'^TEST-[A-Z]+-(\d{4})$', id_string)
        num = int(num_match.group(1)) if num_match else None

        return {
            'canonical_id': id_string,
            'id_range': id_string,  # Same as canonical for single IDs
            'id_range_expanded': [id_string],  # Single item array
            'range_start': num,
            'range_end': num
        }


def extract_test_plan_id(file_content: str) -> Optional[str]:
    """
    Extracts Test Plan ID from metadata header.

    Example: **Test Plan ID:** TEST-CAL-1001 through TEST-CAL-1050

    Returns: Test Plan ID string or None
    """
    lines = file_content.split('\n')[:50]  # Check first 50 lines (header section)
    for line in lines:
        match = re.search(r'\*\*Test Plan ID:\*\*\s*(.+)', line)
        if match:
            return match.group(1).strip()
    return None


def expand_id_range(start_id: str, end_id: str) -> List[str]:
    """
    Expands an ID range into a full list of IDs.

    P2-2 Enhancement: Coverage range expansion
    Handles ranges like "REQ-CAL-1001" through "REQ-CAL-1050"

    Args:
        start_id: Starting ID (e.g., 'REQ-CAL-1001')
        end_id: Ending ID (e.g., 'REQ-CAL-1050')

    Returns:
        List of all IDs in the range (e.g., ['REQ-CAL-1001', 'REQ-CAL-1002', ...])

    Examples:
        expand_id_range('REQ-CAL-1001', 'REQ-CAL-1050') -> 50 IDs
        expand_id_range('ADR-DB-2010', 'ADR-DB-2020') -> 11 IDs
    """
    # Parse the IDs to extract prefix and numbers
    # Expected format: PREFIX-DOMAIN-NUMBER (e.g., REQ-CAL-1001)
    start_match = re.match(r'^([A-Z]+)-([A-Z]+)-(\d+)$', start_id)
    end_match = re.match(r'^([A-Z]+)-([A-Z]+)-(\d+)$', end_id)

    if not start_match or not end_match:
        # Invalid format, return both IDs as-is
        return [start_id, end_id]

    start_prefix = start_match.group(1)
    start_domain = start_match.group(2)
    start_num = int(start_match.group(3))

    end_prefix = end_match.group(1)
    end_domain = end_match.group(2)
    end_num = int(end_match.group(3))

    # Verify that prefix and domain match
    if start_prefix != end_prefix or start_domain != end_domain:
        # Mismatched prefix/domain, return both IDs as-is
        return [start_id, end_id]

    # Verify that end_num >= start_num
    if end_num < start_num:
        # Invalid range, return both IDs as-is
        return [start_id, end_id]

    # Generate the range
    prefix = f"{start_prefix}-{start_domain}"
    num_digits = len(start_match.group(3))  # Preserve leading zeros (e.g., 0001)

    expanded = []
    for num in range(start_num, end_num + 1):
        id_str = f"{prefix}-{num:0{num_digits}d}"
        expanded.append(id_str)

    return expanded


def parse_requirement_range(content: str) -> List[str]:
    """
    Parses requirement IDs from content, expanding ranges into full arrays.

    P2-2 Enhancement: Coverage range expansion
    Supports multiple formats:
    - Single IDs: REQ-CAL-1001
    - Comma lists: REQ-CAL-1001, REQ-CAL-1002
    - Ranges: REQ-CAL-1001 through REQ-CAL-1050
    - Markdown links: [REQ-CAL-1001](...)

    Args:
        content: Text content containing requirement IDs

    Returns:
        List of expanded requirement IDs (all ranges expanded to individual IDs)

    Examples:
        "REQ-CAL-1001 through REQ-CAL-1050" -> 50 IDs
        "REQ-CAL-1001, REQ-CAL-1002" -> 2 IDs
        "REQ-CAL-1001" -> 1 ID
    """
    requirements = []

    # Pattern 1: Range format "REQ-XXX-#### through REQ-XXX-####"
    range_pattern = r'((?:REQ|NFR)-[A-Z]+-\d{4})\s+through\s+((?:REQ|NFR)-[A-Z]+-\d{4})'
    range_matches = re.findall(range_pattern, content, re.IGNORECASE)

    for start_id, end_id in range_matches:
        # Expand the range
        expanded = expand_id_range(start_id, end_id)
        requirements.extend(expanded)

    # Pattern 2: Individual IDs (not part of a range)
    # Extract all REQ-XXX-#### patterns, but exclude those already in ranges
    all_ids = re.findall(r'((?:REQ|NFR)-[A-Z]+-\d{4})', content)

    # Remove IDs that are part of ranges (already expanded above)
    range_ids = set()
    for start_id, end_id in range_matches:
        range_ids.add(start_id)
        range_ids.add(end_id)

    # Add individual IDs that aren't part of ranges
    for req_id in all_ids:
        if req_id not in range_ids and req_id not in requirements:
            requirements.append(req_id)

    return requirements


def extract_covered_requirements(file_content: str) -> List[str]:
    """
    Extracts requirement IDs from "Covers Requirements:" field.

    P2-2 Enhancement: Now uses parse_requirement_range() to expand ranges

    Example: **Covers Requirements:** [REQ-CAL-1001](...) through [REQ-CAL-1104](...)
             Returns 104 individual IDs in array

    Returns: List of requirement ID strings (ranges expanded)
    """
    requirements = []
    lines = file_content.split('\n')[:50]

    # Find the line with Covers Requirements and collect all content
    found = False
    content_lines = []
    for i, line in enumerate(lines):
        if re.search(r'\*\*Covers Requirements:\*\*', line):
            found = True
            # Get the content after the colon on the same line
            match = re.search(r'\*\*Covers Requirements:\*\*\s*(.+)', line)
            if match:
                content_lines.append(match.group(1).strip())
            # Continue collecting until we hit the next ** field or ---
            for j in range(i + 1, len(lines)):
                if re.match(r'^\*\*[A-Za-z ]+:\*\*', lines[j]) or re.match(r'^---', lines[j]):
                    break
                if lines[j].strip():
                    content_lines.append(lines[j].strip())
            break

    if found:
        full_content = ' '.join(content_lines)
        # P2-2: Use parse_requirement_range() to handle ranges and individual IDs
        requirements = parse_requirement_range(full_content)

    return requirements


def parse_adr_range(content: str) -> List[str]:
    """
    Parses ADR IDs from content, expanding ranges into full arrays.

    P2-2 Enhancement: Coverage range expansion for ADRs
    Supports multiple formats:
    - Single IDs: ADR-CAL-1001
    - Comma lists: ADR-CAL-1001, ADR-CAL-1002
    - Ranges: ADR-CAL-1001 through ADR-CAL-1010
    - Markdown links: [ADR-CAL-1001](...)

    Args:
        content: Text content containing ADR IDs

    Returns:
        List of expanded ADR IDs (all ranges expanded to individual IDs)

    Examples:
        "ADR-CAL-1001 through ADR-CAL-1010" -> 10 IDs
        "ADR-CAL-1001, ADR-CAL-1002" -> 2 IDs
        "ADR-CAL-1001" -> 1 ID
    """
    adrs = []

    # Pattern 1: Range format "ADR-XXX-#### through ADR-XXX-####"
    range_pattern = r'(ADR-[A-Z]+-\d{4})\s+through\s+(ADR-[A-Z]+-\d{4})'
    range_matches = re.findall(range_pattern, content, re.IGNORECASE)

    for start_id, end_id in range_matches:
        # Expand the range
        expanded = expand_id_range(start_id, end_id)
        adrs.extend(expanded)

    # Pattern 2: Individual IDs (not part of a range)
    # Extract all ADR-XXX-#### patterns, but exclude those already in ranges
    all_ids = re.findall(r'(ADR-[A-Z]+-\d{4})', content)

    # Remove IDs that are part of ranges (already expanded above)
    range_ids = set()
    for start_id, end_id in range_matches:
        range_ids.add(start_id)
        range_ids.add(end_id)

    # Add individual IDs that aren't part of ranges
    for adr_id in all_ids:
        if adr_id not in range_ids and adr_id not in adrs:
            adrs.append(adr_id)

    return adrs


def extract_covered_adrs(file_content: str) -> List[str]:
    """
    Extracts ADR IDs from "Covers ADRs:" field.

    P2-2 Enhancement: Now uses parse_adr_range() to expand ranges

    Example: **Covers ADRs:** [ADR-CAL-1001](...) through [ADR-CAL-1010](...)
             Returns 10 individual IDs in array

    Returns: List of ADR ID strings (ranges expanded)
    """
    adrs = []
    lines = file_content.split('\n')[:50]

    # Find the line with Covers ADRs and collect all content
    found = False
    content_lines = []
    for i, line in enumerate(lines):
        if re.search(r'\*\*Covers ADRs:\*\*', line):
            found = True
            # Get the content after the colon on the same line
            match = re.search(r'\*\*Covers ADRs:\*\*\s*(.+)', line)
            if match:
                content_lines.append(match.group(1).strip())
            # Continue collecting until we hit the next ** field or ---
            for j in range(i + 1, len(lines)):
                if re.match(r'^\*\*[A-Za-z ]+:\*\*', lines[j]) or re.match(r'^---', lines[j]):
                    break
                if lines[j].strip():
                    content_lines.append(lines[j].strip())
            break

    if found:
        full_content = ' '.join(content_lines)
        # P2-2: Use parse_adr_range() to handle ranges and individual IDs
        adrs = parse_adr_range(full_content)

    return adrs


def extract_test_cases(file_content: str) -> List[Dict]:
    """
    Extracts test case IDs and titles from H4 headings.

    Example: #### TEST-CAL-1001: Dark Frame Subtraction Correctness

    Returns: List of test case dicts with id and title
    """
    test_cases = []
    lines = file_content.split('\n')

    for line in lines:
        # Match H4 headings with TEST-XXX-#### pattern
        match = re.match(r'^####\s+(TEST-[A-Z]+-\d{4}):\s*(.+)$', line.strip())
        if match:
            test_cases.append({
                'id': match.group(1),
                'title': match.group(2).strip()
            })

    return test_cases


def parse_traceability_matrix_row(row: str) -> Optional[Dict]:
    """
    Parses a single traceability matrix row with 6 columns.

    6-Column Format:
    | Requirement/ADR | Test Type | Test Case ID | Status | Description | Notes |

    Args:
        row: Single pipe-delimited row string

    Returns:
        Dict with parsed columns or None if invalid

    Example:
        "| REQ-CAL-1001 | Unit | TEST-CAL-1001 | Pending | Validates dark frame | Uses test images |"
        ->
        {
            'requirement_adr': 'REQ-CAL-1001',
            'test_type': 'Unit',
            'test_case_id': 'TEST-CAL-1001',
            'status': 'Pending',
            'description': 'Validates dark frame',
            'notes': 'Uses test images'
        }
    """
    # Pattern: 6 pipe-delimited columns
    # Regex: \|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|
    row_pattern = r'\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|'

    match = re.match(row_pattern, row)
    if not match:
        return None

    # Extract 6 columns
    columns = [match.group(i).strip() for i in range(1, 7)]

    # Extract requirement/ADR ID from markdown link
    # Example: [REQ-CAL-1001: Dark Frame Subtraction](path)
    requirement_adr = columns[0]
    req_id_match = re.search(r'\[([A-Z]+-[A-Z]+-\d{4})', requirement_adr)
    if req_id_match:
        requirement_adr = req_id_match.group(1)

    # Extract test type (handle "(Planned)" suffix)
    test_type = columns[1]
    is_planned = "(Planned)" in test_type
    test_type = re.sub(r'\s*\(Planned\)\s*', '', test_type).strip()

    # Extract test case ID from markdown link
    # Example: [TEST-CAL-1001: Dark Frame Subtraction](...)
    test_case_id = columns[2]
    test_id_match = re.search(r'\[([A-Z]+-[A-Z]+-\d{4})', test_case_id)
    if test_id_match:
        test_case_id = test_id_match.group(1)

    # Extract status
    status = columns[3].strip()

    # Extract description (NEW 6th column)
    description = columns[4].strip()

    # Extract notes
    notes = columns[5].strip()

    return {
        'requirement_adr': requirement_adr,
        'test_type': test_type,
        'is_planned': is_planned,
        'test_case_id': test_case_id,
        'status': status,
        'description': description,
        'notes': notes
    }


def extract_traceability_matrix(file_content: str) -> List[Dict]:
    """
    Extracts traceability matrix rows from test plan document.

    Documentation phase: 6-column traceability matrix parsing
    Supports 6-column format: Requirement/ADR | Test Type | Test Case ID | Status | Description | Notes

    Algorithm:
    1. Find markdown table header (starts with |)
    2. Skip separator row (dashes)
    3. Parse each data row with parse_traceability_matrix_row()
    4. Aggregate test case breakdown (unit/benchmark/hitl counts)

    Args:
        file_content: Markdown document content

    Returns:
        List of parsed traceability rows with test_case_breakdown

    Examples:
        Returns list with entries like:
        {
            'requirement_adr': 'REQ-CAL-1001',
            'test_type': 'Unit',
            'test_case_id': 'TEST-CAL-1001',
            'status': 'Pending',
            'description': 'Validates dark frame',
            'notes': 'Uses test images'
        }

        Plus breakdown object:
        {
            'unit': 16,
            'benchmark': 4,
            'hitl': 0
        }
    """
    rows = []
    lines = file_content.split('\n')

    # Find first table (look for lines starting with |)
    table_start = -1
    for i, line in enumerate(lines):
        if line.strip().startswith('|') and '|' in line:
            # Check if this looks like a table header (has content between pipes)
            if any(c.isalpha() or c.isdigit() for c in line):
                table_start = i
                break

    if table_start == -1:
        return []

    # Skip header line, find and skip separator line
    i = table_start + 1
    if i < len(lines):
        # Skip separator line (dashes between pipes)
        separator = lines[i].strip()
        if re.match(r'^\|[\s\-|]+\|$', separator):
            i += 1

    # Parse data rows
    test_type_counts = {'unit': 0, 'benchmark': 0, 'hitl': 0}

    while i < len(lines):
        line = lines[i].strip()

        # Stop at end of table (blank line or non-pipe line after table content)
        if not line or not line.startswith('|'):
            break

        # Try to parse row
        parsed = parse_traceability_matrix_row(line)
        if parsed:
            rows.append(parsed)

            # Count test types for breakdown
            test_type_lower = parsed['test_type'].lower()
            if test_type_lower == 'unit':
                test_type_counts['unit'] += 1
            elif test_type_lower == 'benchmark':
                test_type_counts['benchmark'] += 1
            elif test_type_lower == 'hitl':
                test_type_counts['hitl'] += 1

        i += 1

    # Add breakdown to each row and as summary
    return {
        'rows': rows,
        'test_case_breakdown': {
            'unit': test_type_counts['unit'],
            'benchmark': test_type_counts['benchmark'],
            'hitl': test_type_counts['hitl'],
            'total': sum(test_type_counts.values())
        }
    }


def parse_test_plan(file_path: str, project_root: Optional[str] = None) -> Optional[Dict]:
    """
    Parses a test plan file and extracts metadata.

    Documentation phase: Enhanced with traceability matrix parsing
    - Extracts 6-column traceability matrix with description field
    - Computes test_case_breakdown (unit/benchmark/hitl counts)

    Args:
        file_path: Path to test plan file
        project_root: Project root path for domain derivation (optional, auto-detected if not provided)

    Returns: Test plan dict or None if parsing fails
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract document title
        title = extract_document_title(content)

        # Extract metadata using document extraction function
        metadata = extract_document_metadata(content, file_path)

        # Extract test plan specific fields
        test_plan_id_raw = extract_test_plan_id(content)
        covered_requirements = extract_covered_requirements(content)
        covered_adrs = extract_covered_adrs(content)
        test_cases = extract_test_cases(content)

        # Documentation phase: Extract traceability matrix with 6-column format
        traceability_matrix_data = extract_traceability_matrix(content)
        traceability_rows = traceability_matrix_data.get('rows', []) if isinstance(traceability_matrix_data, dict) else []
        test_case_breakdown = traceability_matrix_data.get('test_case_breakdown', {
            'unit': 0, 'benchmark': 0, 'hitl': 0, 'total': 0
        }) if isinstance(traceability_matrix_data, dict) else {
            'unit': 0, 'benchmark': 0, 'hitl': 0, 'total': 0
        }

        # P2-4: Parse test plan ID into canonical ID and range components
        test_plan_id_parsed = parse_test_plan_id(test_plan_id_raw) if test_plan_id_raw else {
            'canonical_id': None,
            'id_range': None,
            'id_range_expanded': [],
            'range_start': None,
            'range_end': None
        }

        # Derive domain from file path using DOMAIN_MAP
        # If project_root not provided, auto-detect it
        if not project_root:
            project_root = str(get_project_root())

        # Use derive_domain_from_path() to get domain code (cal, cam, db, etc.)
        domain = derive_domain_from_path(file_path, project_root)

        # Make file path relative to project root
        rel_path = os.path.relpath(file_path, start=project_root)

        # P2-4: Store both canonical ID (for lookups) and full range info (for display)
        test_plan = {
            'id': test_plan_id_parsed['canonical_id'],  # Canonical ID for URLs and lookups
            'id_range': test_plan_id_parsed['id_range'],  # Full range string for display
            'id_range_expanded': test_plan_id_parsed['id_range_expanded'],  # Array of all IDs
            'range_start': test_plan_id_parsed['range_start'],  # Starting number
            'range_end': test_plan_id_parsed['range_end'],  # Ending number
            'title': title,
            'status': metadata['status'],
            'domain': domain,  # Now derived from derive_domain_from_path()
            'file': rel_path,
            'metadata': {
                'created': metadata['created'],
                'last_updated': metadata['last_updated'],
                'owner': metadata['owner'],
                'version': None  # Could be extracted if needed
            },
            'coverage': {
                'requirements': covered_requirements,
                'adrs': covered_adrs
            },
            'test_cases': test_cases,
            'test_case_count': len(test_cases),
            # Documentation phase: Add traceability matrix and breakdown
            'traceability_matrix': traceability_rows,
            'test_case_breakdown': test_case_breakdown
        }

        return test_plan

    except Exception as e:
        print(f"Error parsing test plan {file_path}: {e}")
        return None


def extract_document_title(file_content: str) -> Optional[str]:
    """
    Extracts document H1 title (first # heading).

    Returns title string or None if not found.
    """
    lines = file_content.split('\n')
    for line in lines:
        if line.startswith('# '):
            return line[2:].strip()
    return None


def extract_range_description(title: str, id_range: Optional[str]) -> str:
    """
    Parses range description from ID Range field or document title.

    Prioritizes description from ID Range field (most authoritative) over title.

    Examples from ID Range:
    - "REQ-CAL-5001 through REQ-CAL-5099 (Base Unpacker)" -> "Base Unpacker"
    - "REQ-CAL-01XX: Calibration Cache Requirements" -> "Calibration Cache Requirements"

    Examples from title:
    - "Unpacker Requirements" -> "Unpacker Requirements"
    - "Bad Pixel Replacement Requirements (Bayer-Specific)" -> "Bad Pixel Replacement (Bayer-Specific)"

    Returns descriptive text suitable for UI display.
    """
    # Try to extract from ID Range first (highest priority - it's the authoritative source)
    if id_range:
        # Look for description in parentheses: "REQ-CAL-5001 through REQ-CAL-5099 (Base Unpacker)"
        match = re.search(r'\(([^)]+)\)$', id_range)
        if match:
            return match.group(1).strip()

        # Try to extract from range format with colon: "REQ-CAL-01XX: Description"
        match = re.match(r'^(?:REQ|NFR|ADR)-[A-Z]+(?:-\d{2,4}X+)?:\s*(.+)$', id_range)
        if match:
            return match.group(1).strip()

    # Fall back to title if no description in ID Range
    if not title:
        return "Requirement Range"

    # Remove range ID prefix if present (e.g., "REQ-CAL-01XX: ")
    match = re.match(r'^(?:REQ|NFR|ADR)-[A-Z]+(?:-\d{2,4}X+)?:\s*(.+)$', title)
    if match:
        return match.group(1).strip()

    return title


def extract_document_metadata(file_content: str, file_path: str) -> Dict:
    """
    Extracts document-level metadata from file header.

    Looks for YAML-style or markdown fields:
    - **Status:** value
    - **ID Range:** value
    - **Created:** YYYY-MM-DD
    - **Last Updated:** YYYY-MM-DD
    - **Owner:** value

    Returns metadata dict with normalized values.
    """
    metadata = {
        'status': 'Draft',
        'id_range': None,
        'range_description': None,
        'created': None,
        'last_updated': None,
        'owner': 'Unknown'
    }

    # Extract document title
    title = extract_document_title(file_content)

    # Extract first 50 lines for header metadata
    lines = file_content.split('\n')[:50]

    for line in lines:
        # Match **Field:** value or Field: value patterns
        match = re.search(r'\*\*([^:]+):\*\*\s*(.+)', line)
        if not match:
            match = re.search(r'^([^:]+):\s*(.+)', line)

        if match:
            field = match.group(1).strip().lower()
            value = match.group(2).strip()

            if field == 'status':
                metadata['status'] = normalize_status(value)
            elif field == 'id range':
                metadata['id_range'] = value
            elif field == 'created':
                metadata['created'] = value
            elif field in ['last updated', 'updated']:
                metadata['last_updated'] = value
            elif field == 'owner':
                metadata['owner'] = value

    # Extract range description from title
    if title:
        metadata['range_description'] = extract_range_description(title, metadata.get('id_range'))

    # Use file modification date as fallback
    if not metadata['created'] or not metadata['last_updated']:
        mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
        date_str = mod_time.strftime('%Y-%m-%d')
        if not metadata['created']:
            metadata['created'] = date_str
        if not metadata['last_updated']:
            metadata['last_updated'] = date_str

    return metadata


def normalize_status(status: str) -> str:
    """
    Normalizes status to valid enum values.

    Valid: Draft, Proposed, Active, Approved, Deprecated, Superseded, Accepted
    """
    status_map = {
        'draft': 'Draft',
        'proposed': 'Proposed',
        'active': 'Active',
        'approved': 'Approved',
        'accepted': 'Approved',  # Normalize Accepted to Approved
        'deprecated': 'Deprecated',
        'superseded': 'Superseded'
    }

    normalized = status_map.get(status.lower().strip())
    if not normalized:
        print(f"Warning: Invalid status '{status}', defaulting to Draft")
        return 'Draft'
    return normalized


def parse_file_content(file_path: str, domain: str) -> Dict:
    """
    Reads file and returns (metadata, raw_sections).

    Returns dict with file_path, domain, metadata, and raw_sections.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    metadata = extract_document_metadata(content, file_path)

    # Extract H2 sections (## heading)
    raw_sections = []
    lines = content.split('\n')

    i = 0
    while i < len(lines):
        line = lines[i]

        # Match H2 headings: ## REQ-XXX-0001: Title or ## NFR-XXX-0001: Title or ## ADR-XXX-0001: Title
        if re.match(r'^##\s+(REQ|NFR|ADR)-[A-Z]+-\d{4}:', line):
            heading = line
            line_number = i + 1

            # Collect content until next H2 or EOF
            section_content = []
            i += 1
            while i < len(lines) and not re.match(r'^##\s+(REQ|NFR|ADR)-[A-Z]+-\d{4}:', lines[i]):
                section_content.append(lines[i])
                i += 1

            raw_sections.append({
                'heading': heading,
                'line_number': line_number,
                'content': '\n'.join(section_content)
            })
        else:
            i += 1

    return {
        'file_path': file_path,
        'domain': domain,
        'metadata': metadata,
        'raw_sections': raw_sections
    }


# ============================================================================
# AGENT 2: Content Parsing & Cross-Reference Building
# ============================================================================

def extract_requirement_id_and_title(heading_line: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Parses "## REQ-CAL-0001: Some Title" into (id, title).

    Returns: (id_str, title_str) or (None, None) if invalid
    """
    match = re.match(r'^##\s+([A-Z]+-[A-Z]+-\d{4}):\s*(.+)$', heading_line)
    if match:
        return match.group(1), match.group(2).strip()
    return None, None


def parse_subsections(content: str) -> List[Dict]:
    """
    Extracts H3/H4 subsection structure from requirement content.

    Returns list of subsection dicts.
    """
    subsections = []
    lines = content.split('\n')

    for line in lines:
        # Match H3, H4, H5 headings
        match = re.match(r'^(#{3,5})\s+(.+)$', line)
        if match:
            level = len(match.group(1))
            heading_text = match.group(2).strip()
            subsections.append({
                'heading': heading_text,
                'level': level,
                'content_length': 0  # Could be enhanced to track content
            })

    return subsections


def find_cross_references(content: str) -> Dict:
    """
    Scans content for references to other requirements/ADRs.

    Patterns: REQ-[A-Z]+-NNNN or ADR-[A-Z]+-NNNN

    Returns dict with references and references_with_context.
    """
    pattern = r'(REQ|NFR|ADR)-([A-Z]{2,3})-(\d{4})'

    references = set()
    references_with_context = []

    lines = content.split('\n')
    for line in lines:
        matches = re.finditer(pattern, line)
        for match in matches:
            ref_id = match.group(0)
            references.add(ref_id)
            references_with_context.append({
                'id': ref_id,
                'context': line.strip()
            })

    return {
        'references': sorted(list(references)),
        'references_with_context': references_with_context
    }


def markdown_to_html(markdown_text: str) -> str:
    """
    Converts markdown to HTML using markdown library.

    Uses extensions: tables, fenced_code
    """
    md = markdown.Markdown(extensions=['tables', 'fenced_code'])
    return md.convert(markdown_text)


def process_requirement(
    raw_section: Dict, file_path: str, domain: str, doc_metadata: Dict, project_root: str
) -> Optional[Dict]:
    """
    Transforms raw section into structured requirement object.

    Returns complete requirement dict or None if invalid.
    """
    req_id, title = extract_requirement_id_and_title(raw_section['heading'])

    if not req_id or not title:
        print(f"Warning: Invalid heading format at {file_path}:{raw_section['line_number']}")
        return None

    # Determine type from ID prefix
    req_type = 'ADR' if req_id.startswith('ADR-') else ('NFR' if req_id.startswith('NFR-') else 'REQ')

    # Parse content
    content = raw_section['content']
    subsections = parse_subsections(content)
    cross_refs = find_cross_references(content)

    # Check for requirement-level status override
    status = doc_metadata['status']
    status_match = re.search(r'\*\*Status:\*\*\s*(\w+)', content)
    if status_match:
        status = normalize_status(status_match.group(1))

    # Convert markdown to HTML
    html_content = markdown_to_html(content)

    # Create summary (first 200 chars)
    summary = content.strip()[:200]
    if len(content.strip()) > 200:
        summary += '...'

    # Build relationships from cross-references
    relationships_refs = []
    for ref in cross_refs['references_with_context']:
        relationships_refs.append({
            'target_id': ref['id'],
            'type': 'mentions',
            'context': ref['context']
        })

    # Make file path relative to the repository being scanned.
    rel_path = os.path.relpath(file_path, start=project_root)

    requirement = {
        'id': req_id,
        'title': title,
        'type': req_type,
        'status': status,
        'domain': domain,

        'document_metadata': {
            'created': doc_metadata['created'],
            'last_updated': doc_metadata['last_updated'],
            'owner': doc_metadata['owner'],
            'id_range': doc_metadata['id_range'],
            'range_description': doc_metadata.get('range_description')
        },

        'source': {
            'file': rel_path,
            'section_line': raw_section['line_number']
        },

        'content': {
            'markdown': content.strip(),
            'html': html_content,
            'summary': summary
        },

        'relationships': {
            'references': relationships_refs,
            'referenced_by': [],  # Built later
            'family': {
                'id_range': doc_metadata['id_range'],
                'members_count': 0  # Populated later
            }
        },

        'subsections': subsections
    }

    return requirement


def build_bidirectional_relationships(requirements_list: List[Dict]) -> List[Dict]:
    """
    Builds bidirectional relationships.

    For each requirement that references others, adds to referenced_by of targets.
    """
    # Build ID to index map
    id_to_idx = {req['id']: idx for idx, req in enumerate(requirements_list)}

    # Build referenced_by lists
    for req in requirements_list:
        for ref in req['relationships']['references']:
            target_id = ref['target_id']
            if target_id in id_to_idx:
                target_idx = id_to_idx[target_id]
                requirements_list[target_idx]['relationships']['referenced_by'].append({
                    'source_id': req['id'],
                    'type': 'mentioned_by',
                    'context': ref['context']
                })

    return requirements_list


def compute_family_members(requirements_list: List[Dict]) -> List[Dict]:
    """
    For each requirement, populates family.members_count.

    Family = all requirements with same ID Range.
    """
    # Count members per ID range
    range_counts = {}
    for req in requirements_list:
        id_range = req['document_metadata'].get('id_range')
        if id_range:
            range_counts[id_range] = range_counts.get(id_range, 0) + 1

    # Update each requirement
    for req in requirements_list:
        id_range = req['document_metadata'].get('id_range')
        if id_range:
            req['relationships']['family']['members_count'] = range_counts.get(id_range, 0)

    return requirements_list


def build_indexes(requirements_list: List[Dict]) -> Dict:
    """
    Creates lookup indexes for fast querying.

    Returns dict with by_id, by_domain, by_status, by_id_range indexes.
    """
    indexes = {
        'by_id': {},
        'by_domain': {},
        'by_status': {},
        'by_id_range': {}
    }

    for idx, req in enumerate(requirements_list):
        # Index by ID
        indexes['by_id'][req['id']] = idx

        # Index by domain
        domain = req['domain']
        if domain not in indexes['by_domain']:
            indexes['by_domain'][domain] = []
        indexes['by_domain'][domain].append(idx)

        # Index by status
        status = req['status']
        if status not in indexes['by_status']:
            indexes['by_status'][status] = []
        indexes['by_status'][status].append(idx)

        # Index by ID range
        id_range = req['document_metadata'].get('id_range')
        if id_range:
            if id_range not in indexes['by_id_range']:
                indexes['by_id_range'][id_range] = []
            indexes['by_id_range'][id_range].append(idx)

    return indexes


def compute_statistics(requirements_list: List[Dict]) -> Dict:
    """
    Computes aggregate statistics.

    Returns statistics dict.
    """
    stats = {
        'counts': {
            'by_domain': {},
            'by_status': {},
            'by_type': {'REQ': 0, 'NFR': 0, 'ADR': 0}
        },
        'ranges': []
    }

    # Count by domain and type
    for req in requirements_list:
        domain = req['domain']
        req_type = req['type']

        if domain not in stats['counts']['by_domain']:
            stats['counts']['by_domain'][domain] = {'REQ': 0, 'NFR': 0, 'ADR': 0}

        stats['counts']['by_domain'][domain][req_type] += 1
        stats['counts']['by_type'][req_type] += 1

    # Count by status
    for req in requirements_list:
        status = req['status']
        stats['counts']['by_status'][status] = stats['counts']['by_status'].get(status, 0) + 1

    # Aggregate range information
    ranges_info = {}
    for req in requirements_list:
        id_range = req['document_metadata'].get('id_range')
        if id_range:
            if id_range not in ranges_info:
                ranges_info[id_range] = {
                    'range': id_range,
                    'file': os.path.basename(req['source']['file']),
                    'description': req['title'],  # Use first requirement's title as description
                    'count': 0
                }
            ranges_info[id_range]['count'] += 1

    stats['ranges'] = list(ranges_info.values())

    return stats


def compute_test_plan_metrics(test_plans: List[Dict]) -> Dict:
    """
    Computes test plan discovery metrics by domain.

    P2-1 Enhancement: Tracks test plan discovery across all domains.

    Args:
        test_plans: List of test plan dicts with 'domain' field

    Returns:
        Dict with total count and per-domain breakdown
    """
    metrics = {
        'total': len(test_plans),
        'by_domain': {}
    }

    # Count test plans by domain
    for test_plan in test_plans:
        domain = test_plan.get('domain', 'unknown')
        metrics['by_domain'][domain] = metrics['by_domain'].get(domain, 0) + 1

    return metrics


def generate_json_output(requirements: List[Dict], indexes: Dict, statistics: Dict, metadata: Dict, validation: Dict = None, test_plans: List[Dict] = None) -> Dict:
    """
    Generates final requirements-index.json structure.

    Enhanced to include detailed per-file validation data from ValidationRunner.
    Enhanced to include test_plans array.
    Enhanced to include test plan discovery metrics (P2-1).

    Returns dict ready for json.dumps().
    """
    output = {
        'metadata': metadata,
        'requirements': requirements,
        'indexes': indexes,
        'statistics': statistics
    }

    # Include test plans if provided
    if test_plans:
        output['test_plans'] = test_plans
        # P2-1: Add test plan discovery metrics
        output['test_plan_discovery'] = compute_test_plan_metrics(test_plans)

    # Include validation data if provided
    if validation:
        output['validation'] = {
            'report_file': 'validation-report.json',
            'generated_at': validation.get('generated_at'),
            'documents_scanned': validation.get('documents_scanned', 0),
            'summary': validation.get('summary', {})
        }

    return output


def generate_extraction_report(
    results: Dict, validation: Dict, statistics: Dict, requirement_count: int
) -> str:
    """
    Generates human-readable extraction-report.txt.

    Returns report string.
    """
    report_lines = []
    report_lines.append("=" * 80)
    report_lines.append("DOCUMENTATION EXTRACTION REPORT")
    report_lines.append("=" * 80)
    report_lines.append(f"Generated: {datetime.now(timezone.utc).isoformat()}")
    report_lines.append("")

    # Summary
    report_lines.append("SUMMARY")
    report_lines.append("-" * 80)
    report_lines.append(f"Files discovered: {results['files_discovered']}")
    report_lines.append(f"Files processed: {results['files_processed']}")
    report_lines.append(f"Requirements extracted (REQ): {statistics['counts']['by_type']['REQ']}")
    report_lines.append(f"Non-functional requirements (NFR): {statistics['counts']['by_type']['NFR']}")
    report_lines.append(f"Architecture decisions (ADR): {statistics['counts']['by_type']['ADR']}")
    report_lines.append(f"Total items: {requirement_count}")
    report_lines.append("")

    # Validation
    report_lines.append("VALIDATION")
    report_lines.append("-" * 80)
    summary = validation.get('summary', {}) if validation else {}
    report_lines.append(f"Critical errors: {summary.get('total_errors', 0)}")
    report_lines.append(f"Warnings: {summary.get('total_warnings', 0)}")
    report_lines.append(f"Report file: {validation.get('report_file', 'validation-report.json')}")
    report_lines.append("")

    # Statistics by domain
    report_lines.append("STATISTICS BY DOMAIN")
    report_lines.append("-" * 80)
    for domain, counts in statistics['counts']['by_domain'].items():
        report_lines.append(f"{domain.upper()}:")
        report_lines.append(f"  REQ: {counts['REQ']}")
        report_lines.append(f"  NFR: {counts['NFR']}")
        report_lines.append(f"  ADR: {counts['ADR']}")
        report_lines.append(f"  Total: {counts['REQ'] + counts['NFR'] + counts['ADR']}")
    report_lines.append("")

    # Statistics by status
    report_lines.append("STATISTICS BY STATUS")
    report_lines.append("-" * 80)
    for status, count in sorted(statistics['counts']['by_status'].items()):
        report_lines.append(f"{status}: {count}")
    report_lines.append("")

    # ID Ranges
    report_lines.append("ID RANGES")
    report_lines.append("-" * 80)
    for range_info in statistics['ranges']:
        report_lines.append(f"{range_info['range']}")
        report_lines.append(f"  File: {range_info['file']}")
        report_lines.append(f"  Count: {range_info['count']}")
    report_lines.append("")

    # Errors
    files = validation.get('files', []) if validation else []
    if files:
        report_lines.append("ERRORS BY FILE (first 10)")
        report_lines.append("-" * 80)
        for file_entry in files[:10]:
            if not file_entry['errors']:
                continue
            report_lines.append(f"{file_entry['filepath']} ({file_entry['total_errors']} errors)")
            for error in file_entry['errors'][:5]:
                report_lines.append(f"  - {error['rule_id']}: {error['message']}")
            if file_entry['total_errors'] > 5:
                report_lines.append("    ...")
            report_lines.append("")

    # Warnings summary
    total_warnings = summary.get('total_warnings', 0)
    if total_warnings:
        report_lines.append("WARNINGS SUMMARY")
        report_lines.append("-" * 80)
        report_lines.append(f"Total warnings: {total_warnings}")
        report_lines.append("")

    report_lines.append("=" * 80)
    report_lines.append("END OF REPORT")
    report_lines.append("=" * 80)

    return '\n'.join(report_lines)


# ============================================================================
# MAIN PIPELINE
# ============================================================================

def main():
    """
    Main extraction pipeline.

    Steps:
    1. Parse CLI arguments and validate project root
    2. Discover files and extract metadata
    3. Parse content and build relationships
    4. Validate records and build indexes
    5. Generate outputs
    6. Print summary

    Repository configuration is optional and local to the scanned repository.
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Documentation extraction pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        'root',
        nargs='?',
        help='Repository root path (overrides --project-root)'
    )
    parser.add_argument(
        '--project-root',
        type=str,
        default=None,
        help='Override project root path (default: auto-detect from script location)'
    )
    parser.add_argument(
        '--domain',
        type=str,
        default='all',
        help='Domain to process (default: all)'
    )
    parser.add_argument('--domains', nargs='+', help='Domain directories to scan; overrides repository configuration')
    parser.add_argument(
        '--output-dir',
        type=str,
        default=None,
        help='Output directory for generated files (default: {project_root}/.build)'
    )
    parser.add_argument('--output', type=str, help='Output JSON path (overrides --output-dir)')

    args = parser.parse_args()

    print("=" * 80)
    print("Documentation extraction pipeline")
    print("=" * 80)
    print()

    # Determine project root
    root_arg = args.root or args.project_root
    if root_arg:
        project_root = Path(root_arg).resolve()
        print(f"Using specified project root: {project_root}")
    else:
        working_root = Path.cwd().resolve()
        project_root = working_root if (working_root / '.raptor' / 'raptor.toml').exists() else get_project_root()
        print(f"Auto-detected project root: {project_root}")

    # Validate project root
    config_path = project_root / '.raptor' / 'raptor.toml'
    if not config_path.exists() and not validate_project_root(project_root):
        print(f"ERROR: Invalid project root: {project_root}")
        print("Expected directories not found (calibration/, database/, scripts/, etc.)")
        return 1

    print(f"Project root validated: {project_root}")
    print()

    # Convert project_root to string for compatibility with existing code
    project_root_str = str(project_root)

    # Define target directories based on domain selection
    # Domains: calibration, database, performance, mcp, camera, regions, sequencer, ui
    target_dirs = []

    configured_files = []
    allowed_types = {}
    configured_test_plans = False
    if config_path.exists() and not root_arg and args.domain == 'all' and not args.domains:
        manifest = tomllib.loads(config_path.read_text(encoding='utf-8'))
        source_file = config_path.parent / manifest['files']['scan']
        routing_file = config_path.parent / manifest['files']['routing']
        artifact_types = {
            'requirement': 'REQ',
            'non_functional_requirement': 'NFR',
            'architecture_decision': 'ADR',
        }
        routes = {}
        for route in tomllib.loads(routing_file.read_text(encoding='utf-8'))['routes']:
            route_types = set()
            for artifact_type in route['artifact_types']:
                if artifact_type in artifact_types:
                    route_types.add(artifact_types[artifact_type])
                elif artifact_type == 'test_plan':
                    configured_test_plans = True
                elif artifact_type != 'design_document':
                    print(f"ERROR: {routing_file}: unknown artifact type {artifact_type}", file=sys.stderr)
                    return 1
            routes[route['source']] = route_types
        for source in tomllib.loads(source_file.read_text(encoding='utf-8'))['sources']:
            source_root = project_root / source['root']
            excluded = {path for pattern in source.get('exclude', []) for path in source_root.glob(pattern)}
            for pattern in source['include']:
                for path in source_root.glob(pattern):
                    if path.is_file() and path.suffix == '.md' and path not in excluded and '.git' not in path.parts and '.raptor' not in path.parts:
                        configured_files.append((str(path), source['name']))
            allowed_types[source['name']] = routes[source['name']]
        configured_files = sorted(set(configured_files))
    elif args.domain == 'all':
        # Process all domains
        domains = args.domains or ['calibration', 'database', 'performance', 'mcp', 'camera', 'regions', 'sequencer', 'ui', 'avalonia']
        for domain in domains:
            # Add standard subdirectories for each domain
            for subdir in ['requirements', 'architecture', 'design', 'schema']:
                path = os.path.join(project_root_str, domain, subdir)
                if os.path.exists(path):
                    target_dirs.append(path)
    else:
        # Process single domain
        doc_paths = get_doc_paths(project_root, args.domain)
        target_dirs = doc_paths['target_dirs']
        print(f"Processing domain: {doc_paths['domain_dir']}")
        print()

    # STEP 1: AGENT 1 - Discover and extract metadata
    print("STEP 1: Discovering markdown files...")
    print("-" * 80)
    files = configured_files or discover_markdown_files(target_dirs)
    print(f"\nTotal files discovered: {len(files)}")
    print()

    # STEP 2: AGENT 2 - Parse content and build requirements
    print("STEP 2: Parsing content and extracting requirements...")
    print("-" * 80)
    all_requirements = []
    files_processed = 0

    for file_path, domain in files:
        print(f"Processing: {file_path}")
        parsed = parse_file_content(file_path, domain)

        for raw_section in parsed['raw_sections']:
            req = process_requirement(raw_section, file_path, domain, parsed['metadata'], project_root_str)
            if req and (not allowed_types or req['type'] in allowed_types[domain]):
                all_requirements.append(req)

        files_processed += 1

    print(f"\nTotal requirements extracted: {len(all_requirements)}")
    print()

    # STEP 2A: Extract test plans
    print("STEP 2A: Extracting test plans...")
    print("-" * 80)
    test_plan_files = extract_test_plans(project_root_str) if not configured_files or configured_test_plans else []
    all_test_plans = []

    for test_plan_file in test_plan_files:
        # P2-1a: Pass project_root to enable domain derivation
        test_plan = parse_test_plan(test_plan_file, project_root=project_root_str)
        if test_plan:
            all_test_plans.append(test_plan)

    # P2-1: Compute and display test plan discovery metrics
    test_plan_metrics = compute_test_plan_metrics(all_test_plans)
    print(f"\nTotal test plans extracted: {test_plan_metrics['total']}")
    if test_plan_metrics['by_domain']:
        print("By domain:")
        for domain, count in sorted(test_plan_metrics['by_domain'].items()):
            print(f"  {domain}: {count}")
    print()

    # STEP 3: Build relationships
    print("STEP 3: Building relationships...")
    print("-" * 80)
    all_requirements = build_bidirectional_relationships(all_requirements)
    all_requirements = compute_family_members(all_requirements)
    print("Bidirectional relationships built")
    print("Family members computed")
    print()

    failures = []
    for item in all_requirements:
        try:
            Record.model_validate(item)
        except Exception as error:
            field = error.errors()[0]['loc'][0] if getattr(error, 'errors', None) else 'record'
            failures.append(f"{item['source']['file']}: {item['id']}: {field}")
    if failures:
        print('\n'.join(failures), file=sys.stderr)
        return 1
    validation = {'documents_scanned': files_processed, 'summary': {'total_errors': 0, 'total_warnings': 0}}
    summary = validation['summary']

    # STEP 5: Build indexes
    print("STEP 5: Building indexes...")
    print("-" * 80)
    indexes = build_indexes(all_requirements)
    print(f"Indexed by ID: {len(indexes['by_id'])} entries")
    print(f"Indexed by domain: {len(indexes['by_domain'])} domains")
    print(f"Indexed by status: {len(indexes['by_status'])} statuses")
    print(f"Indexed by ID range: {len(indexes['by_id_range'])} ranges")
    print()

    # STEP 6: Compute statistics
    print("STEP 6: Computing statistics...")
    print("-" * 80)
    statistics = compute_statistics(all_requirements)
    print(f"REQ count: {statistics['counts']['by_type']['REQ']}")
    print(f"NFR count: {statistics['counts']['by_type']['NFR']}")
    print(f"ADR count: {statistics['counts']['by_type']['ADR']}")
    print()

    # STEP 7: Generate outputs
    print("STEP 7: Generating outputs...")
    print("-" * 80)

    # Determine output directory
    if args.output_dir:
        outputs_dir = args.output_dir
    else:
        outputs_dir = os.path.join(project_root_str, '.build')
    os.makedirs(outputs_dir, exist_ok=True)

    json_path = args.output or os.path.join(outputs_dir, 'requirements-index.json')
    reports_dir = os.path.join(project_root_str, 'reports')
    os.makedirs(reports_dir, exist_ok=True)

    # Generate JSON output
    metadata = {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'version': '1.0.0',
        'phase': 1,
        'total_requirements': len(all_requirements),
        'total_files': files_processed
    }

    json_output = generate_json_output(all_requirements, indexes, statistics, metadata, validation, all_test_plans)

    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_output, f, indent=2, ensure_ascii=False)
    print(f"Generated: {json_path}")

    # Generate extraction report
    results = {
        'files_discovered': len(files),
        'files_processed': files_processed
    }

    report_text = generate_extraction_report(
        results, validation, statistics, requirement_count=len(all_requirements)
    )
    report_path = os.path.join(reports_dir, 'extraction-report.txt')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report_text)
    print(f"Generated: {report_path}")
    print()

    # Print summary
    print("=" * 80)
    print("EXTRACTION COMPLETE")
    print("=" * 80)
    print(f"Files processed: {files_processed}")
    print(f"Requirements extracted: {len(all_requirements)}")
    print(f"  - REQ: {statistics['counts']['by_type']['REQ']}")
    print(f"  - NFR: {statistics['counts']['by_type']['NFR']}")
    print(f"  - ADR: {statistics['counts']['by_type']['ADR']}")
    print(f"Validation errors: {summary.get('total_errors', 0)}")
    print(f"Validation warnings: {summary.get('total_warnings', 0)}")
    print()

    # Exit with success code even if there are validation warnings/errors
    # The JSON file was successfully generated and can be used
    if summary.get('total_errors', 0) > 0:
        print("WARNING: Validation errors found. Please review extraction-report.txt")
    else:
        print("SUCCESS: Phase 1 complete and ready for Phase 2")
    return 0


# ============================================================================
# CROSS-PLATFORM PATH HANDLING TESTS
# ============================================================================

def test_cross_platform_paths():
    """
    Tests path handling functions with various path formats.

    Verifies that is_test_plan() works correctly on:
    - Unix-style paths (/)
    - Windows-style paths (\)
    - Absolute and relative paths
    - Mixed separators
    """
    print("Running cross-platform path tests...")
    print("-" * 80)

    # Test Case 1: Unix relative path
    unix_relative = 'calibration/test/test-dark.md'
    result1 = is_test_plan(unix_relative)
    assert result1 == True, f"Unix relative path failed: {unix_relative}"
    print(f"✓ Unix relative: {unix_relative} -> {result1}")

    # Test Case 2: Windows relative path
    windows_relative = r'calibration\test\test-dark.md'
    result2 = is_test_plan(windows_relative)
    assert result2 == True, f"Windows relative path failed: {windows_relative}"
    print(f"✓ Windows relative: {windows_relative} -> {result2}")

    # Test Case 3: Unix absolute path
    unix_absolute = '/home/user/proj/calibration/test/test-dark.md'
    result3 = is_test_plan(unix_absolute)
    assert result3 == True, f"Unix absolute path failed: {unix_absolute}"
    print(f"✓ Unix absolute: {unix_absolute} -> {result3}")

    # Test Case 4: Windows absolute path
    windows_absolute = r'C:\Users\user\proj\calibration\test\test-dark.md'
    result4 = is_test_plan(windows_absolute)
    assert result4 == True, f"Windows absolute path failed: {windows_absolute}"
    print(f"✓ Windows absolute: {windows_absolute} -> {result4}")

    # Test Case 5: Negative test - not in test directory
    not_test = 'calibration/requirements/req-dark.md'
    result5 = is_test_plan(not_test)
    assert result5 == False, f"Should reject non-test path: {not_test}"
    print(f"✓ Non-test path: {not_test} -> {result5}")

    # Test Case 6: Negative test - wrong prefix
    wrong_prefix = 'calibration/test/dark-test.md'
    result6 = is_test_plan(wrong_prefix)
    assert result6 == False, f"Should reject wrong prefix: {wrong_prefix}"
    print(f"✓ Wrong prefix: {wrong_prefix} -> {result6}")

    # Test Case 7: Negative test - wrong extension
    wrong_ext = 'calibration/test/test-dark.txt'
    result7 = is_test_plan(wrong_ext)
    assert result7 == False, f"Should reject wrong extension: {wrong_ext}"
    print(f"✓ Wrong extension: {wrong_ext} -> {result7}")

    # Test Case 8: Windows path with mixed separators
    mixed = r'calibration/test\test-thermal.md'
    result8 = is_test_plan(mixed)
    assert result8 == True, f"Mixed separators failed: {mixed}"
    print(f"✓ Mixed separators: {mixed} -> {result8}")

    print("-" * 80)
    print("All cross-platform path tests passed!")
    print()


if __name__ == '__main__':
    exit(main())
