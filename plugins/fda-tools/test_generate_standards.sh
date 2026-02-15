#!/bin/bash
# Test script for generate-standards command
# Tests core functionality with 2 product codes

set -e

PLUGIN_ROOT="/home/linux/.claude/plugins/marketplaces/fda-tools/plugins/fda-tools"
OUTPUT_DIR="$PLUGIN_ROOT/data/standards"
VALIDATION_DIR="$PLUGIN_ROOT/data/validation_reports"

mkdir -p "$OUTPUT_DIR"
mkdir -p "$VALIDATION_DIR"

# Test codes
TEST_CODES="DQY OVE"

echo "🧪 Testing Standards Generation Infrastructure"
echo "=============================================="
echo ""

# Test 1: Verify API client can classify codes
echo "Test 1: API Classification"
for CODE in $TEST_CODES; do
    echo "  Testing classification for $CODE..."
    if python3 "$PLUGIN_ROOT/scripts/fda_api_client.py" --classify "$CODE" > "/tmp/test_classification_${CODE}.json" 2>&1; then
        echo "  ✅ Classification successful for $CODE"
        cat "/tmp/test_classification_${CODE}.json" | jq -r '.product_code, .device_class, .device_name' | head -3
    else
        echo "  ❌ Classification failed for $CODE"
        exit 1
    fi
    echo ""
done

# Test 2: Verify standards database exists
echo "Test 2: Standards Database"
if [ -f "$PLUGIN_ROOT/data/fda_standards_database.json" ]; then
    echo "  ✅ Standards database exists"
    STANDARD_COUNT=$(cat "$PLUGIN_ROOT/data/fda_standards_database.json" | jq '.metadata.total_standards')
    echo "  Database contains $STANDARD_COUNT standards across 10 categories"
else
    echo "  ❌ Standards database not found"
    exit 1
fi
echo ""

# Test 3: Verify agents exist
echo "Test 3: Agent Files"
AGENTS="standards-ai-analyzer standards-coverage-auditor standards-quality-reviewer"
for AGENT in $AGENTS; do
    if [ -f "$PLUGIN_ROOT/agents/${AGENT}.md" ]; then
        echo "  ✅ $AGENT exists"
    else
        echo "  ❌ $AGENT not found"
        exit 1
    fi
done
echo ""

# Test 4: Verify markdown_to_html.py works
echo "Test 4: HTML Report Generator"
if python3 "$PLUGIN_ROOT/scripts/markdown_to_html.py" \
    "$PLUGIN_ROOT/README.md" \
    --output "/tmp/test_standards_report.html" \
    --title "Test Standards Report" > /dev/null 2>&1; then
    echo "  ✅ HTML generator works"
    SIZE=$(ls -lh /tmp/test_standards_report.html | awk '{print $5}')
    echo "  Generated test report: $SIZE"
else
    echo "  ❌ HTML generator failed"
    exit 1
fi
echo ""

# Test 5: Directory structure
echo "Test 5: Directory Structure"
echo "  Output directory: $OUTPUT_DIR"
echo "  Validation directory: $VALIDATION_DIR"
echo "  ✅ Directories created successfully"
echo ""

echo "=============================================="
echo "✅ All infrastructure tests PASSED"
echo ""
echo "Note: Full agent-based generation requires manual invocation via:"
echo "  /fda-tools:generate-standards DQY OVE"
echo ""
echo "This would launch the standards-ai-analyzer agent for each code"
echo "and generate JSON files with AI-determined standards."
