import os
import re
import html
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path
from xml.etree import ElementTree

from sphinx.application import Sphinx
from sphinx.util.logging import getLogger

logger = getLogger(__name__)


def _parse_index_rst(index_path: str) -> list[str]:
    """解析 index.rst 中 toctree 的文章顺序，返回 slug 列表（越靠前越新）。"""
    with open(index_path, "r", encoding="utf-8") as f:
        text = f.read()

    slugs: list[str] = []
    pattern = re.compile(r"^\s*archives/(.+)\.md\s*$", re.MULTILINE)
    for m in pattern.finditer(text):
        slugs.append(m.group(1))
    return slugs


def _parse_article(filepath: str) -> dict | None:
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    lines = content.split("\n")
    meta: dict = {}
    meta["filename"] = os.path.basename(filepath)
    meta["slug"] = os.path.splitext(meta["filename"])[0]

    # 中文标题
    title_match = re.match(r"^#\s+(.+)$", lines[0])
    if title_match:
        meta["title"] = title_match.group(1).strip()

    # 元数据字段
    # 注意：由于 `# 标题：` 与 `标题：` 容易混淆，这里跳过标题匹配
    for line in lines[1:12]:
        if not line.strip():
            continue
        for field in ("日期", "作者", "链接"):
            m = re.match(rf"^{field}：(.+)$", line)
            if m:
                key_map = {"日期": "date", "作者": "author", "链接": "link"}
                meta[key_map[field]] = m.group(1).strip()
                break

    # 提取分隔线后前三行非空内容作为摘要
    sep = next((i for i, ln in enumerate(lines) if ln.strip() == "-------"), -1)
    if sep >= 0:
        parts: list[str] = []
        for i in range(sep + 1, len(lines)):
            txt = lines[i].strip()
            if txt:
                parts.append(txt)
                if len(parts) >= 3:
                    break
        if parts:
            summary = " ".join(parts)
            meta["summary"] = summary[:500] + ("..." if len(summary) > 500 else "")

    return meta


def create_rss(app: Sphinx, exception):
    # 仅 HTML builder 生成 RSS
    if app.builder.format != "html":
        return

    site_url = (app.builder.config.html_baseurl or "").rstrip("/")
    if not site_url:
        logger.warning("html_baseurl is required for RSS feed. Feed not built.")
        return

    archives_dir = os.path.join(app.confdir, "archives")
    if not os.path.isdir(archives_dir):
        return

    suffix = app.builder.config.html_link_suffix or ".html"

    articles = []
    for fname in os.listdir(archives_dir):
        if not fname.endswith(".md"):
            continue
        try:
            meta = _parse_article(os.path.join(archives_dir, fname))
            if meta:
                articles.append(meta)
        except Exception as exc:
            logger.warning(f"Failed to parse {fname}: {exc}", type="rss")

    # 按照 index.rst toctree 顺序排列（越靠前越新）
    index_rst_path = os.path.join(app.confdir, "index.rst")
    if os.path.isfile(index_rst_path):
        order = _parse_index_rst(index_rst_path)
        order_map = {slug: i for i, slug in enumerate(order)}
        articles.sort(key=lambda a: order_map.get(a["slug"], len(order)))
    else:
        articles.sort(key=lambda a: a.get("date", ""), reverse=True)

    # 构建 RSS 2.0
    rss = ElementTree.Element("rss", version="2.0")
    rss.set("xmlns:atom", "http://www.w3.org/2005/Atom")
    channel = ElementTree.SubElement(rss, "channel")

    ElementTree.SubElement(channel, "title").text = "Caturra的中文转录小站"
    ElementTree.SubElement(channel, "link").text = site_url
    ElementTree.SubElement(channel, "description").text = (
        "一些演讲的中文转录稿"
    )
    ElementTree.SubElement(channel, "language").text = "zh-CN"
    ElementTree.SubElement(channel, "lastBuildDate").text = format_datetime(
        datetime.now(timezone.utc)
    )

    atom_link = ElementTree.SubElement(
        channel, "{http://www.w3.org/2005/Atom}link"
    )
    atom_link.set("href", f"{site_url}/rss.xml")
    atom_link.set("rel", "self")
    atom_link.set("type", "application/rss+xml")

    for a in articles:
        item = ElementTree.SubElement(channel, "item")

        title = a.get("title", a["slug"])
        ElementTree.SubElement(item, "title").text = title

        link = f"{site_url}/archives/{a['slug']}{suffix}"
        ElementTree.SubElement(item, "link").text = link
        ElementTree.SubElement(item, "guid").text = link

        summary = a.get("summary", "")
        if summary:
            ElementTree.SubElement(item, "description").text = html.escape(summary)

    out = Path(app.outdir) / "rss.xml"
    ElementTree.ElementTree(rss).write(
        out, xml_declaration=True, encoding="utf-8", method="xml"
    )
    logger.info(
        f"RSS feed generated: {out} ({len(articles)} items)",
        type="rss",
    )


def setup(app: Sphinx):
    app.connect("build-finished", create_rss)
    return {
        "parallel_read_safe": True,
        "parallel_write_safe": True,
        "version": "0.1.0",
    }
