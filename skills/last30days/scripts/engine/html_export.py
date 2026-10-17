"""HTML report generator: exports interactive, styled single-file HTML briefs."""

import html
import re
from typing import Any, Dict, List

from . import config
from .sources.base import SearchResult


def markdown_to_html_simple(md_text: str) -> str:
    """Minimal stdlib markdown to HTML converter for beautiful briefing documents."""
    lines = md_text.split("\n")
    html_lines = []
    in_list = False
    in_table = False

    for line in lines:
        stripped = line.strip()

        # Table rows
        if stripped.startswith("|") and stripped.endswith("|"):
            if not in_table:
                in_table = True
                html_lines.append('<div class="table-container"><table>')
            # Check for separator
            if re.match(r"^\|(\s*:?-+:?\s*\|)+$", stripped):
                continue
            cells = [c.strip() for c in stripped[1:-1].split("|")]
            cell_html = "".join(f"<td>{markdown_inline(c)}</td>" for c in cells)
            html_lines.append(f"<tr>{cell_html}</tr>")
            continue
        elif in_table:
            in_table = False
            html_lines.append("</table></div>")

        # Headings
        if stripped.startswith("# "):
            html_lines.append(f"<h1>{markdown_inline(stripped[2:])}</h1>")
        elif stripped.startswith("## "):
            html_lines.append(f"<h2>{markdown_inline(stripped[3:])}</h2>")
        elif stripped.startswith("### "):
            html_lines.append(f"<h3>{markdown_inline(stripped[4:])}</h3>")
        # Blockquote
        elif stripped.startswith("> "):
            html_lines.append(f"<blockquote>{markdown_inline(stripped[2:])}</blockquote>")
        # Unordered list
        elif stripped.startswith("- "):
            if not in_list:
                in_list = True
                html_lines.append("<ul>")
            html_lines.append(f"<li>{markdown_inline(stripped[2:])}</li>")
        # Horizontal rule
        elif stripped == "---":
            if in_list:
                in_list = False
                html_lines.append("</ul>")
            html_lines.append("<hr/>")
        elif not stripped:
            if in_list:
                in_list = False
                html_lines.append("</ul>")
            html_lines.append("<br/>")
        else:
            if in_list:
                in_list = False
                html_lines.append("</ul>")
            html_lines.append(f"<p>{markdown_inline(stripped)}</p>")

    if in_list:
        html_lines.append("</ul>")
    if in_table:
        html_lines.append("</table></div>")

    return "\n".join(html_lines)


def markdown_inline(text: str) -> str:
    """Convert inline markdown (links, bold, code) to HTML."""
    # Links [text](url)
    text = re.sub(
        r'\[(.*?)\]\((https?://[^\s\)]+)\)',
        r'<a href="\2" target="_blank" rel="noopener noreferrer">\1</a>',
        text,
    )
    # Bold **text**
    text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
    # Italic *text*
    text = re.sub(r'\*(.*?)\*', r'<em>\1</em>', text)
    # Inline code `code`
    text = re.sub(r'`(.*?)`', r'<code>\1</code>', text)
    return text


class HtmlExporter:
    @classmethod
    def export_html(cls, markdown_report: str, title: str = "Research Brief") -> str:
        """Render markdown report into a standalone, styled dark-mode HTML page."""
        body_html = markdown_to_html_simple(markdown_report)

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(title)} - last30days Dossier</title>
    <style>
        :root {{
            --bg-primary: #0d1117;
            --bg-secondary: #161b22;
            --border-color: #30363d;
            --text-primary: #c9d1d9;
            --text-heading: #58a6ff;
            --accent: #238636;
            --link: #58a6ff;
            --code-bg: #1f242c;
        }}
        body {{
            background-color: var(--bg-primary);
            color: var(--text-primary);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            line-height: 1.6;
            padding: 2rem;
            margin: 0;
            display: flex;
            justify-content: center;
        }}
        .container {{
            max-width: 900px;
            width: 100%;
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 2.5rem;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
        }}
        h1 {{
            color: #ffffff;
            border-bottom: 2px solid var(--border-color);
            padding-bottom: 0.5rem;
            font-size: 2rem;
        }}
        h2 {{
            color: var(--text-heading);
            margin-top: 2rem;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 0.3rem;
            font-size: 1.4rem;
        }}
        h3 {{
            color: #79c0ff;
            margin-top: 1.2rem;
            font-size: 1.1rem;
        }}
        a {{
            color: var(--link);
            text-decoration: none;
        }}
        a:hover {{
            text-decoration: underline;
        }}
        blockquote {{
            border-left: 4px solid var(--text-heading);
            margin: 1rem 0;
            padding: 0.5rem 1rem;
            background: #111822;
            color: #8b949e;
            border-radius: 0 6px 6px 0;
        }}
        code {{
            background: var(--code-bg);
            color: #ff7b72;
            padding: 0.2rem 0.4rem;
            border-radius: 4px;
            font-size: 0.9em;
        }}
        ul {{
            padding-left: 1.5rem;
        }}
        li {{
            margin-bottom: 0.5rem;
        }}
        hr {{
            border: 0;
            border-top: 1px solid var(--border-color);
            margin: 2rem 0;
        }}
        .table-container {{
            overflow-x: auto;
            margin: 1.5rem 0;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        th, td {{
            border: 1px solid var(--border-color);
            padding: 0.6rem 0.8rem;
            text-align: left;
        }}
        th {{
            background: #1e2630;
            color: #ffffff;
        }}
        tr:nth-child(even) {{
            background: #12171f;
        }}
    </style>
</head>
<body>
    <div class="container">
        {body_html}
    </div>
</body>
</html>
"""
