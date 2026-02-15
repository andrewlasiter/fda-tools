#!/usr/bin/env python3
"""
Simple Markdown to HTML Converter for FDA Standards Validation Reports

Converts markdown validation reports to HTML with basic Bootstrap styling.
No external dependencies beyond Python stdlib.
"""

import re
import sys
from pathlib import Path
from datetime import datetime


def markdown_to_html(md_content):
    """Convert markdown to HTML with basic formatting.

    Supports:
    - Headers (# ## ###)
    - Bold (**text**)
    - Lists (- item, 1. item)
    - Code blocks (```)
    - Tables (| col | col |)
    - Horizontal rules (---)
    """
    html = md_content

    # Headers
    html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)

    # Bold
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)

    # Status badges
    html = re.sub(r'✅ GREEN', r'<span class="badge bg-success">GREEN</span>', html)
    html = re.sub(r'⚠️\s*YELLOW', r'<span class="badge bg-warning">YELLOW</span>', html)
    html = re.sub(r'❌ RED', r'<span class="badge bg-danger">RED</span>', html)
    html = re.sub(r'✓', r'<span class="text-success">✓</span>', html)
    html = re.sub(r'✗', r'<span class="text-danger">✗</span>', html)

    # Code blocks
    html = re.sub(r'```([a-z]*)\n(.*?)\n```', r'<pre><code class="language-\1">\2</code></pre>', html, flags=re.DOTALL)

    # Tables - simple conversion
    lines = html.split('\n')
    in_table = False
    table_html = []

    for line in lines:
        if '|' in line and not line.strip().startswith('<'):
            if not in_table:
                in_table = True
                table_html.append('<table class="table table-bordered table-striped">')

            # Header row
            if re.match(r'\|[\s\-:]+\|', line):
                continue  # Skip separator line

            cells = [cell.strip() for cell in line.split('|')[1:-1]]

            if len(table_html) == 1:  # First data row = header
                table_html.append('<thead><tr>')
                for cell in cells:
                    table_html.append(f'<th>{cell}</th>')
                table_html.append('</tr></thead><tbody>')
            else:
                table_html.append('<tr>')
                for cell in cells:
                    table_html.append(f'<td>{cell}</td>')
                table_html.append('</tr>')
        else:
            if in_table:
                table_html.append('</tbody></table>')
                in_table = False
                table_html.append(line)
            else:
                table_html.append(line)

    if in_table:
        table_html.append('</tbody></table>')

    html = '\n'.join(table_html)

    # Lists
    html = re.sub(r'^\s*[-•]\s+(.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)
    html = re.sub(r'(<li>.*</li>)', r'<ul>\1</ul>', html, flags=re.DOTALL)
    html = re.sub(r'</ul>\n+<ul>', '', html)  # Merge consecutive lists

    # Horizontal rules
    html = re.sub(r'^[-=]{3,}$', r'<hr>', html, flags=re.MULTILINE)

    # Paragraphs
    paragraphs = html.split('\n\n')
    formatted_paragraphs = []
    for p in paragraphs:
        p = p.strip()
        if p and not p.startswith('<'):
            formatted_paragraphs.append(f'<p>{p}</p>')
        else:
            formatted_paragraphs.append(p)

    html = '\n\n'.join(formatted_paragraphs)

    return html


def generate_html_report(md_files, output_file, title="FDA Standards Validation Report"):
    """Generate combined HTML report from markdown files.

    Args:
        md_files: List of Path objects or strings to markdown files
        output_file: Path to output HTML file
        title: Report title
    """
    # Read all markdown files
    combined_md = []

    for md_file in md_files:
        md_path = Path(md_file)
        if md_path.exists():
            with open(md_path, 'r') as f:
                content = f.read()
                combined_md.append(f'<section id="{md_path.stem}">')
                combined_md.append(markdown_to_html(content))
                combined_md.append('</section>')
                combined_md.append('<hr class="my-5">')
        else:
            print(f"Warning: {md_file} not found, skipping...")

    # Generate HTML template
    html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f8f9fa;
        }}
        .container {{
            max-width: 1200px;
            margin: 40px auto;
            background: white;
            padding: 40px;
            box-shadow: 0 0 20px rgba(0,0,0,0.1);
            border-radius: 8px;
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
            margin-bottom: 30px;
        }}
        h2 {{
            color: #34495e;
            margin-top: 40px;
            margin-bottom: 20px;
            border-left: 4px solid #3498db;
            padding-left: 15px;
        }}
        h3 {{
            color: #7f8c8d;
            margin-top: 30px;
            margin-bottom: 15px;
        }}
        table {{
            margin: 20px 0;
        }}
        .table-bordered {{
            border: 1px solid #dee2e6;
        }}
        .badge {{
            font-size: 0.9em;
            padding: 0.4em 0.8em;
        }}
        pre {{
            background-color: #f5f5f5;
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 15px;
            overflow-x: auto;
        }}
        code {{
            font-family: "Monaco", "Menlo", "Ubuntu Mono", monospace;
            font-size: 0.9em;
        }}
        .report-header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            margin: -40px -40px 40px -40px;
            border-radius: 8px 8px 0 0;
        }}
        .report-header h1 {{
            color: white;
            border: none;
            margin: 0;
        }}
        .report-meta {{
            font-size: 0.9em;
            opacity: 0.9;
            margin-top: 10px;
        }}
        section {{
            margin-bottom: 40px;
        }}
        .text-success {{
            color: #28a745;
        }}
        .text-danger {{
            color: #dc3545;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="report-header">
            <h1>{title}</h1>
            <div class="report-meta">
                Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
            </div>
        </div>

        {''.join(combined_md)}

        <footer class="text-center text-muted mt-5 pt-4 border-top">
            <p>FDA Standards Validation System | Auto-generated Report</p>
        </footer>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>"""

    # Write output file
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w') as f:
        f.write(html_template)

    print(f"✅ HTML report generated: {output_path}")
    print(f"   Size: {output_path.stat().st_size:,} bytes")
    print(f"   Open in browser: file://{output_path.absolute()}")


def main():
    """CLI for markdown to HTML conversion."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Convert FDA validation markdown reports to HTML",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Convert single report
  python3 markdown_to_html.py coverage_report.md --output report.html

  # Convert multiple reports into one HTML file
  python3 markdown_to_html.py coverage.md quality.md consensus.md --output validation.html

  # Custom title
  python3 markdown_to_html.py *.md --output full_report.html --title "Complete Validation Report"
        """
    )

    parser.add_argument('markdown_files', nargs='+', help='Markdown files to convert')
    parser.add_argument('--output', '-o', required=True, help='Output HTML file')
    parser.add_argument('--title', '-t', default='FDA Standards Validation Report', help='Report title')

    args = parser.parse_args()

    generate_html_report(args.markdown_files, args.output, args.title)


if __name__ == '__main__':
    main()
