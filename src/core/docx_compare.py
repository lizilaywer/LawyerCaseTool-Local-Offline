# -*- coding: utf-8 -*-
"""Word 文档对比核心模块

支持对比两份 .docx 文档的文本差异，返回带标签的差异片段，
供界面层渲染为高亮 HTML。
"""

import html
from difflib import SequenceMatcher
from pathlib import Path
from typing import List, Tuple


def extract_docx_text(path: Path) -> str:
    """从 docx 文件中提取纯文本（段落以换行分隔）。"""
    try:
        from docx import Document
    except ImportError:
        raise RuntimeError("需要安装 python-docx: pip install python-docx")

    doc = Document(str(path))
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    return "\n".join(paragraphs)


def compare_docx(
    path_a: Path, path_b: Path
) -> Tuple[List[Tuple[str, str]], List[Tuple[str, str]]]:
    """对比两份 docx 文档，返回差异片段。

    Returns:
        (segments_a, segments_b)
        每个 segment 是 (tag, text) 元组，tag 取值：
        - "equal"   : 两边相同
        - "delete"  : 仅在 A 中存在（对 B 而言是删除）
        - "insert"  : 仅在 B 中存在（对 B 而言是新增）
        - "replace" : 两边都有但被修改
    """
    text_a = extract_docx_text(path_a)
    text_b = extract_docx_text(path_b)

    sm = SequenceMatcher(None, text_a, text_b, autojunk=False)
    segments_a: List[Tuple[str, str]] = []
    segments_b: List[Tuple[str, str]] = []

    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            segments_a.append(("equal", text_a[i1:i2]))
            segments_b.append(("equal", text_b[j1:j2]))
        elif tag == "delete":
            segments_a.append(("delete", text_a[i1:i2]))
        elif tag == "insert":
            segments_b.append(("insert", text_b[j1:j2]))
        elif tag == "replace":
            segments_a.append(("replace", text_a[i1:i2]))
            segments_b.append(("replace", text_b[j1:j2]))

    return segments_a, segments_b


def render_diff_html(segments: List[Tuple[str, str]], side: str = "left") -> str:
    """将差异片段渲染为带高亮样式的 HTML。

    Args:
        segments: (tag, text) 列表
        side: "left" 表示原文档，"right" 表示修改后文档
    """
    parts: List[str] = []
    for tag, text in segments:
        escaped = html.escape(text).replace("\n", "<br>")
        if tag == "equal":
            parts.append(f'<span style="color:#334155;">{escaped}</span>')
        elif tag == "delete":
            if side == "left":
                parts.append(
                    f'<span style="background:#fee2e2;color:#991b1b;'
                    f'text-decoration:line-through;">{escaped}</span>'
                )
            else:
                # 右侧不显示删除内容，只留空占位保持对齐
                parts.append(f'<span style="color:#cbd5e1;">⋯</span>')
        elif tag == "insert":
            if side == "right":
                parts.append(
                    f'<span style="background:#dcfce7;color:#166534;'
                    f'font-weight:600;">{escaped}</span>'
                )
            else:
                parts.append(f'<span style="color:#cbd5e1;">⋯</span>')
        elif tag == "replace":
            if side == "left":
                parts.append(
                    f'<span style="background:#fef9c3;color:#854d0e;'
                    f'text-decoration:line-through;">{escaped}</span>'
                )
            else:
                parts.append(
                    f'<span style="background:#fef9c3;color:#854d0e;'
                    f'font-weight:600;">{escaped}</span>'
                )
    return "".join(parts)
