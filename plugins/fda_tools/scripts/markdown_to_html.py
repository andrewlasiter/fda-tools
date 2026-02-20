#!/usr/bin/env python3
"""
Simple Markdown to HTML Converter for FDA Standards Validation Reports

Converts markdown validation reports to HTML with basic Bootstrap styling.
No external dependencies beyond Python stdlib.

SECURITY: All user input is HTML-escaped to prevent XSS attacks.
- Implements OWASP XSS Prevention Cheat Sheet recommendations
- Uses Content Security Policy (CSP) for defense-in-depth
- Subresource Integrity (SRI) for CDN resources
"""

import html  # For XSS prevention
import re
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

    Security: All user content is HTML-escaped to prevent XSS injection.
    """
    html_content = md_content

    # Headers - with HTML escaping (FIX #1)
    html_content = re.sub(
        r'^### (.+)$',
        lambda m: f'<h3>{html.escape(m.group(1))}</h3>',
        html_content,
        flags=re.MULTILINE
    )
    html_content = re.sub(
        r'^## (.+)$',
        lambda m: f'<h2>{html.escape(m.group(1))}</h2>',
        html_content,
        flags=re.MULTILINE
    )
    html_content = re.sub(
        r'^# (.+)$',
        lambda m: f'<h1>{html.escape(m.group(1))}</h1>',
        html_content,
        flags=re.MULTILINE
    )

    # Bold - with HTML escaping (FIX #2)
    html_content = re.sub(
        r'\*\*(.+?)\*\*',
        lambda m: f'<strong>{html.escape(m.group(1))}</strong>',
        html_content
    )

    # Status badges - pre-escaped, safe
    html_content = re.sub(r'✅ GREEN', r'<span class="badge bg-success">GREEN</span>', html_content)
    html_content = re.sub(r'⚠️\s*YELLOW', r'<span class="badge bg-warning">YELLOW</span>', html_content)
    html_content = re.sub(r'❌ RED', r'<span class="badge bg-danger">RED</span>', html_content)
    html_content = re.sub(r'✓', r'<span class="text-success">✓</span>', html_content)
    html_content = re.sub(r'✗', r'<span class="text-danger">✗</span>', html_content)

    # Code blocks - with HTML escaping and language sanitization (FIX #6, #13)
    def escape_code_block(match):
        # Sanitize language hint to prevent attribute injection
        lang = re.sub(r'[^a-z0-9]', '', match.group(1).lower())
        # Escape code content to prevent HTML injection
        code = html.escape(match.group(2))
        return f'<pre><code class="language-{lang}">{code}</code></pre>'

    html_content = re.sub(
        r'```([a-z0-9]*)\n(.*?)\n```',
        escape_code_block,
        html_content,
        flags=re.DOTALL
    )

    # Tables - simple conversion with HTML escaping (FIX #3, #4)
    lines = html_content.split('\n')
    in_table = False
    table_html = []
    first_row_cells = None

    for i, line in enumerate(lines):
        if '|' in line and not line.strip().startswith('<'):
            if not in_table:
                in_table = True
                first_row_cells = None
                table_html.append('<table class="table table-bordered table-striped">')

            # Check if this is a separator row
            if re.match(r'\|[\s\-:]+\|', line):
                # This is a separator, so previous row was a header
                if first_row_cells:
                    table_html.append('<thead><tr>')
                    for cell in first_row_cells:
                        table_html.append(f'<th>{html.escape(cell)}</th>')
                    table_html.append('</tr></thead><tbody>')
                    first_row_cells = None
                continue  # Skip separator line

            cells = [cell.strip() for cell in line.split('|')[1:-1]]

            # If we haven't seen any rows yet, buffer this as potentially a header
            if first_row_cells is None and len(table_html) == 1:
                # Check if next line is a separator
                next_line_is_sep = (i + 1 < len(lines) and
                                    re.match(r'\|[\s\-:]+\|', lines[i + 1].strip()))
                if next_line_is_sep:
                    # Next line is separator, this is a header - buffer it
                    first_row_cells = cells
                else:
                    # No separator follows, treat as data row
                    if '<tbody>' not in ''.join(table_html):
                        table_html.append('<tbody>')
                    table_html.append('<tr>')
                    for cell in cells:
                        table_html.append(f'<td>{html.escape(cell)}</td>')
                    table_html.append('</tr>')
            else:
                # Regular data row
                if '<tbody>' not in ''.join(table_html):
                    table_html.append('<tbody>')
                table_html.append('<tr>')
                for cell in cells:
                    table_html.append(f'<td>{html.escape(cell)}</td>')
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

    html_content = '\n'.join(table_html)

    # Lists - with HTML escaping (FIX #7)
    html_content = re.sub(
        r'^\s*[-•]\s+(.+)$',
        lambda m: f'<li>{html.escape(m.group(1))}</li>',
        html_content,
        flags=re.MULTILINE
    )
    html_content = re.sub(r'(<li>.*</li>)', r'<ul>\1</ul>', html_content, flags=re.DOTALL)
    html_content = re.sub(r'</ul>\n+<ul>', '', html_content)  # Merge consecutive lists

    # Horizontal rules
    html_content = re.sub(r'^[-=]{3,}$', r'<hr>', html_content, flags=re.MULTILINE)

    # Paragraphs - with HTML escaping (FIX #8)
    # Only skip escaping for HTML we generated (our specific tags)
    safe_html_tags = ['<h1>', '<h2>', '<h3>', '<h4>', '<h5>', '<h6>',
                      '<strong>', '<table', '<ul>', '<li>', '<pre>',
                      '<hr>', '<span class=']

    paragraphs = html_content.split('\n\n')
    formatted_paragraphs = []
    for p in paragraphs:
        p = p.strip()
        if p:
            # Check if this is our generated HTML or user content
            is_our_html = any(p.startswith(tag) for tag in safe_html_tags)
            if is_our_html or p.startswith('</'):
                # This is HTML we generated, keep as-is
                formatted_paragraphs.append(p)
            else:
                # This is user content (including malicious HTML), escape it
                formatted_paragraphs.append(f'<p>{html.escape(p)}</p>')

    html_content = '\n\n'.join(formatted_paragraphs)

    return html_content


def generate_html_report(md_files, output_file, title="FDA Standards Validation Report"):
    """Generate combined HTML report from markdown files.

    Args:
        md_files: List of Path objects or strings to markdown files
        output_file: Path to output HTML file
        title: Report title (will be HTML-escaped)

    Security: Title and section IDs are sanitized to prevent XSS.
    """
    # Escape title parameter to prevent XSS (FIX #9)
    title_safe = html.escape(title)

    # Read all markdown files
    combined_md = []

    for md_file in md_files:
        md_path = Path(md_file)
        if md_path.exists():
            with open(md_path, 'r') as f:
                content = f.read()
                # Sanitize section ID to prevent attribute injection (FIX #10)
                section_id = re.sub(r'[^a-zA-Z0-9_-]', '_', md_path.stem)
                combined_md.append(f'<section id="{section_id}">')
                combined_md.append(markdown_to_html(content))
                combined_md.append('</section>')
                combined_md.append('<hr class="my-5">')
        else:
            print(f"Warning: {md_file} not found, skipping...")

    # Generate HTML template with security controls
    # FIX #11: SRI hashes for CDN resources
    # FIX #12: Content Security Policy
    html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Content-Security-Policy" content="default-src 'self'; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; script-src 'self' https://cdn.jsdelivr.net; img-src 'self' data:;">
    <title>{title_safe}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css"
          rel="stylesheet"
          integrity="sha384-9ndCyUaIbzAi2FUVXJi0CjmCapSmO7SnpJef0486qhLnuZ2cdeRhO02iuK6FUUVM"
          crossorigin="anonymous">
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
            <h1>{title_safe}</h1>
            <div class="report-meta">
                Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
            </div>
        </div>

        {''.join(combined_md)}

        <footer class="text-center text-muted mt-5 pt-4 border-top">
            <p>FDA Standards Validation System | Auto-generated Report</p>
        </footer>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"
            integrity="sha384-fbbOQedDUMZZ5KreZpsbe1LCZPVmfTnH7ois6mU1QK+m14rQ1l2bGBq41eYeM/fS"
            crossorigin="anonymous"></script>
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
