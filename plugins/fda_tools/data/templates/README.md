# HTML Templates Directory

This directory contains HTML templates used by various FDA Tools components.

## Template Files

### competitive_dashboard.html

HTML template for the PMA Competitive Intelligence Dashboard.

**Used by**: `scripts/competitive_dashboard.py`

**Placeholders**:
- `{product_code}` - FDA product code being analyzed
- `{generated_date}` - Date the dashboard was generated (YYYY-MM-DD)
- `{version}` - Dashboard version number
- `{total_pmas}` - Total number of PMAs found
- `{total_applicants}` - Number of unique applicants
- `{approval_rate}` - Percentage of approved PMAs
- `{year_span}` - Year range of PMA activity (e.g., "2010-2024")
- `{market_share_rows}` - HTML table rows for market share data
- `{trend_rows}` - HTML table rows for approval trends
- `{recent_approval_rows}` - HTML table rows for recent approvals
- `{safety_section}` - HTML section for MAUDE safety data
- `{supplement_section}` - HTML section for supplement activity

**Customization**:

To customize the dashboard appearance, edit this template file. Changes will be reflected in all future dashboard exports without modifying Python code.

Example CSS customizations:
- Change colors by modifying the style values (e.g., `#1a237e` for header background)
- Adjust layout by changing grid or flexbox properties
- Add additional sections by inserting new HTML with corresponding placeholders

**Testing**:

After making changes, run:
```bash
python3 -m pytest tests/test_competitive_dashboard_template.py -v
```

To verify the template still contains all required placeholders and renders correctly.

## Template Format

All templates use Python's `str.format()` syntax with curly braces for placeholders:

```html
<div>{placeholder_name}</div>
```

Double braces for literal CSS:
```html
<style>
  .class {{ property: value; }}
</style>
```

## Adding New Templates

1. Create your HTML template file in this directory
2. Use descriptive placeholders with `{placeholder_name}` syntax
3. Add template loading logic in the corresponding Python module
4. Create tests in `tests/` to verify template loading and rendering
5. Document the template in this README

## Template Best Practices

- Use semantic HTML5 elements
- Include proper escaping for dynamic content (handled by Python code)
- Keep CSS inline within `<style>` tags for self-contained output files
- Use comments to mark sections (e.g., `<!-- Key Metrics -->`)
- Validate HTML structure before committing changes
- Ensure templates are UTF-8 encoded
