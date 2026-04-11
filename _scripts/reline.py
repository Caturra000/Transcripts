#!/usr/bin/env python3
"""
Markdown 换行标准化工具

将 Markdown 文件中的单个换行符(\\n)转换为双换行符(\\n\\n)以符合 Markdown 段落标准，
同时保持列表、代码块、表格、引用等特殊结构的完整性。

用法:
    python md_fix_newlines.py <目录路径> [--ext .md] [--dry-run]

规则:
    - 单个 \\n 分隔的普通文本段落 → 转换为 \\n\\n
    - 列表项之间 / 列表续行 → 保持不变
    - 围栏代码块内部 → 保持不变
    - 行尾两个空格的硬换行 → 保持不变
    - 表格行之间 → 保持不变
    - 引用行之间 → 保持不变
    - 引用式链接定义 / 脚注定义之间 → 保持不变
    - setext 标题下划线(===/---)前 → 保持不变
    - YAML front matter → 保持不变
"""

import os
import re
import sys
import argparse


# ─── 行类型判断 ───────────────────────────────────────────────

def is_list_item(line):
    """判断是否为列表项（有序或无序，含 task list）"""
    stripped = line.strip()
    if re.match(r'^[-*+]\s', stripped):
        return True
    if re.match(r'^\d+[.)]\s', stripped):
        return True
    return False


def is_blockquote(line):
    """判断是否为引用行"""
    return line.strip().startswith('>')


def is_table_row(line):
    """判断是否为表格行"""
    stripped = line.strip()
    return stripped.startswith('|') and stripped.count('|') >= 2


def is_reference_link(line):
    """判断是否为引用式链接定义  [label]: url"""
    return bool(re.match(r'^\[.+?\]:\s', line.strip()))


def is_footnote_def(line):
    """判断是否为脚注定义  [^id]: text"""
    return bool(re.match(r'^\[\^.+?\]:\s', line.strip()))


def has_hard_break(line):
    """判断行尾是否有硬换行标记（两个或更多空格）"""
    return line.endswith('  ')


def is_setext_underline(line):
    """判断是否为 setext 标题的下划线（=== 或 ---）"""
    stripped = line.strip()
    return bool(re.match(r'^=+\s*$', stripped)) or bool(re.match(r'^-+\s*$', stripped))


# ─── 区域识别 ─────────────────────────────────────────────────

def identify_code_content(lines):
    """返回围栏代码块「内容」行号集合（围栏标记行本身不计入）"""
    code_lines = set()
    in_code = False
    fence_char = None

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not in_code:
            if stripped.startswith('```') or stripped.startswith('~~~'):
                ch = stripped[0]
                n = 0
                for c in stripped:
                    if c == ch:
                        n += 1
                    else:
                        break
                if n >= 3:
                    in_code = True
                    fence_char = ch
        else:
            # 检查闭合围栏
            if stripped.startswith(fence_char):
                n = 0
                for c in stripped:
                    if c == fence_char:
                        n += 1
                    else:
                        break
                if n >= 3:
                    in_code = False
                    fence_char = None
                    continue          # 闭合围栏行本身不保护
            code_lines.add(i)

    return code_lines


def identify_front_matter(lines):
    """返回 YAML front matter 行号集合（含首尾 ---）"""
    fm_lines = set()
    if len(lines) > 0 and lines[0].strip() == '---':
        fm_lines.add(0)
        found = False
        for i in range(1, len(lines)):
            fm_lines.add(i)
            if lines[i].strip() == '---':
                found = True
                break
        if not found:                 # 没找到闭合 ---，不算 front matter
            fm_lines.clear()
    return fm_lines


# ─── 核心处理 ─────────────────────────────────────────────────

def process_markdown(text):
    """将 Markdown 文本中的单换行标准化为双换行（段落分隔）"""
    if not text:
        return text

    # 统一换行符为 LF
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    lines = text.split('\n')

    # 标记受保护区域
    code_lines = identify_code_content(lines)
    fm_lines   = identify_front_matter(lines)
    protected  = code_lines | fm_lines

    result = []
    in_list = False                   # 跟踪列表上下文

    for i in range(len(lines)):
        line = lines[i]

        # ── 受保护行：原样写入 ──
        if i in protected:
            result.append(line)
            in_list = False
            continue

        result.append(line)

        # ── 空行 ──
        if line.strip() == '':
            in_list = False
            continue

        # ── 更新列表上下文 ──
        if is_list_item(line):
            in_list = True
        elif in_list and (line.startswith('  ') or line.startswith('\t')):
            pass                      # 缩进续行，保持 in_list
        else:
            in_list = False

        # ── 判断是否在下一行前插入空行 ──
        if i + 1 >= len(lines):
            continue
        if (i + 1) in protected:
            continue

        next_line = lines[i + 1]

        # 下一行已为空 → 已有段落分隔
        if next_line.strip() == '':
            continue

        # 当前行尾有硬换行标记（两空格）
        if has_hard_break(line):
            continue

        ls = line.strip()
        ns = next_line.strip()

        # setext 标题下划线前不插入（"Title\\n---" 不应被拆开）
        if is_setext_underline(ns):
            continue

        # ── 同类块元素保持单换行 ──

        # 列表项 ↔ 列表项
        if is_list_item(ls) and is_list_item(ns):
            continue

        # 列表项 → 缩进续行
        if is_list_item(ls) and (next_line.startswith('  ') or next_line.startswith('\t')):
            continue

        # 缩进续行 → 列表项（列表上下文中）
        if in_list and (line.startswith('  ') or line.startswith('\t')) and is_list_item(ns):
            continue

        # 缩进续行 → 缩进续行（列表上下文中）
        if in_list and (line.startswith('  ') or line.startswith('\t')) \
                and (next_line.startswith('  ') or next_line.startswith('\t')):
            continue

        # 引用行 ↔ 引用行
        if is_blockquote(ls) and is_blockquote(ns):
            continue

        # 表格行 ↔ 表格行
        if is_table_row(ls) and is_table_row(ns):
            continue

        # 引用式链接定义 ↔ 引用式链接定义
        if is_reference_link(ls) and is_reference_link(ns):
            continue

        # 脚注定义 ↔ 脚注定义
        if is_footnote_def(ls) and is_footnote_def(ns):
            continue

        # ── 其余情况：插入空行形成段落分隔 ──
        result.append('')

    return '\n'.join(result)


# ─── 文件处理 ─────────────────────────────────────────────────

def process_file(filepath, dry_run=False):
    """处理单个 Markdown 文件，返回 (是否修改, 新内容|None)"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except (IOError, UnicodeDecodeError) as e:
        print(f"  跳过 {filepath}: {e}")
        return False, None

    processed = process_markdown(content)

    if processed != content:
        if not dry_run:
            with open(filepath, 'w', encoding='utf-8', newline='') as f:
                f.write(processed)
        return True, processed
    return False, None


# ─── 入口 ─────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Markdown 换行标准化工具 — 将单换行转换为双换行以符合段落标准'
    )
    parser.add_argument('directory', help='要处理的目录路径')
    parser.add_argument('--ext', default='.md', help='Markdown 文件扩展名（默认: .md）')
    parser.add_argument('--dry-run', action='store_true', help='仅预览，不实际修改文件')
    args = parser.parse_args()

    directory = args.directory
    if not os.path.isdir(directory):
        print(f"错误: 「{directory}」不是有效目录")
        sys.exit(1)

    print(f"扫描目录: {directory}  (扩展名: {args.ext})")
    if args.dry_run:
        print("⚠  干跑模式 — 不会修改文件\n")

    count = 0
    modified = 0

    for root, dirs, files in os.walk(directory):
        # 跳过隐藏目录和常见依赖目录
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('node_modules', '__pycache__', 'vendor')]

        for filename in sorted(files):
            if filename.endswith(args.ext):
                filepath = os.path.join(root, filename)
                count += 1
                changed, _ = process_file(filepath, dry_run=args.dry_run)
                if changed:
                    modified += 1
                    tag = "将修改" if args.dry_run else "已处理"
                    print(f"  ✓ {tag}: {filepath}")
                else:
                    print(f"  - 无变化: {filepath}")

    label = "将修改" if args.dry_run else "已修改"
    print(f"\n完成! 共扫描 {count} 个文件，{label} {modified} 个文件")


if __name__ == '__main__':
    main()