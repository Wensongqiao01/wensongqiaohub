"""简易 Markdown 渲染器"""

import re


def render_markdown(text: str) -> str:
    """将 Markdown 文本渲染为安全的 HTML"""
    # 转义 HTML
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    lines = text.split("\n")
    html_lines: list[str] = []
    in_code_block = False
    code_buffer: list[str] = []
    in_list = False
    in_ordered_list = False

    i = 0
    while i < len(lines):
        line = lines[i]

        # 代码块
        if line.strip().startswith("```"):
            if in_code_block:
                _code_content = _escape_html("\n".join(code_buffer))
                html_lines.append(f"<pre><code>{_code_content}</code></pre>")
                code_buffer = []
                in_code_block = False
            else:
                in_code_block = True
            i += 1
            continue

        if in_code_block:
            code_buffer.append(line)
            i += 1
            continue

        # 空行
        if not line.strip():
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            if in_ordered_list:
                html_lines.append("</ol>")
                in_ordered_list = False
            i += 1
            continue

        # 标题
        heading_match = re.match(r"^(#{1,3})\s+(.+)$", line)
        if heading_match:
            level = len(heading_match.group(1))
            content = heading_match.group(2)
            html_lines.append(f"<h{level}>{content}</h{level}>")
            i += 1
            continue

        # 引用
        if line.startswith("> "):
            html_lines.append(f"<blockquote>{line[2:]}</blockquote>")
            i += 1
            continue

        # 无序列表
        if re.match(r"^[-*+]\s+", line):
            if in_ordered_list:
                html_lines.append("</ol>")
                in_ordered_list = False
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
            item = re.sub(r"^[-*+]\s+", "", line)
            html_lines.append(f"<li>{_inline_markdown(item)}</li>")
            i += 1
            continue

        # 有序列表
        if re.match(r"^\d+\.\s+", line):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            if not in_ordered_list:
                html_lines.append("<ol>")
                in_ordered_list = True
            item = re.sub(r"^\d+\.\s+", "", line)
            html_lines.append(f"<li>{_inline_markdown(item)}</li>")
            i += 1
            continue

        # 关闭列表
        if in_list:
            html_lines.append("</ul>")
            in_list = False
        if in_ordered_list:
            html_lines.append("</ol>")
            in_ordered_list = False

        # 普通段落
        html_lines.append(f"<p>{_inline_markdown(line)}</p>")
        i += 1

    if in_list:
        html_lines.append("</ul>")
    if in_ordered_list:
        html_lines.append("</ol>")
    if in_code_block and code_buffer:
        _code_content = _escape_html("\n".join(code_buffer))
        html_lines.append(f"<pre><code>{_code_content}</code></pre>")

    return "".join(html_lines)


def _inline_markdown(text: str) -> str:
    """处理行内 Markdown 语法"""
    # 加粗 **text**
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    # 斜体 *text*
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<em>\1</em>", text)
    # 行内代码 `code`
    text = re.sub(r"`(.+?)`", r"<code>\1</code>", text)
    # 链接 [text](url) — 仅允许安全协议
    def _safe_link(m: re.Match) -> str:
        url = m.group(2)
        if re.match(r"^(https?://|mailto:)", url):
            return f'<a href="{url}" target="_blank" rel="noopener">{m.group(1)}</a>'
        # 不安全协议 → 纯文本展示
        return f"{m.group(1)} ({url})"

    text = re.sub(r"\[(.+?)\]\((.+?)\)", _safe_link, text)
    return text


def _escape_html(text: str) -> str:
    """转义 HTML 特殊字符"""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
