---
name: epub-xhtml-to-markdown
description: Convert EPUB books to chapter-by-chapter Markdown by opening the EPUB archive and reading its XHTML/HTML directly, then create an Obsidian assembly note that embeds every chapter with ![[note]]. Use this skill whenever the user asks for EPUB→Markdown/MD、EPUB 分章节、直接读取 XHTML、Obsidian include/embed 总装文件、免 OCR 转电子书或保留 EPUB 阅读顺序. Prefer it over PDF/OCR conversion for normal reflowable EPUB files; do not use it for PDF, scanned books, or fixed-layout EPUBs that require visual/OCR reconstruction.
compatibility: Requires Python 3.10+; the bundled converter uses only the Python standard library.
---

# EPUB XHTML → Markdown

将标准流式 EPUB 当作 ZIP 容器打开，读取 `META-INF/container.xml`、OPF manifest/spine 和书内 XHTML，再按阅读顺序为每章生成独立 Markdown。额外生成一个总装文件，用 Obsidian `![[note]]` 嵌入全部章节。这个流程不做 OCR，也不依赖 marker、Calibre 或 Pandoc。

## 适用边界

优先用于正文已经是 XHTML/HTML 的流式 EPUB，因为直接读取文本通常比 OCR 更快、更准确。

不要用于：

- PDF、扫描图片书或只有页面截图的 EPUB；
- 依赖复杂绝对定位、SVG 页面或排版复刻的 fixed-layout EPUB；
- DRM 加密 EPUB。发现 `META-INF/encryption.xml` 且正文无法解析时，停止并说明 DRM/加密限制，不尝试绕过。

## 工作流程

1. 确认输入是 `.epub` 文件，并确定总装 `.md` 路径。用户未指定时，在 EPUB 同目录生成同名 `.md`。
2. 为避免覆盖已有笔记，总装文件、章节目录或资源目录已存在时先询问用户，除非用户明确要求覆盖。
3. 运行随 skill 附带的转换器：

   ```bash
   python3 "<skill-dir>/scripts/epub_xhtml_to_markdown.py" \
     "/path/to/book.epub" \
     "/path/to/book.md"
   ```

4. 检查命令摘要，并抽查 Markdown 的开头、一个中间章节和结尾。确认：
   - 章节顺序遵循 OPF spine；
   - `<输出文件名>_chapters/` 中每个 spine 章节对应一个编号 Markdown；
   - 总装文件按顺序使用 `![[<章节目录>/<章节文件>]]` 嵌入各章；
   - 标题、段落、列表、引用、链接和代码块可读；
   - 图片已提取到 `<输出文件名>_assets/`，章节 Markdown 使用相对路径；
   - 没有明显的导航页重复、空章节或整段粘连。
5. 报告输出 Markdown、资源目录、转换章节数及警告。不要删除源 EPUB。

## 常用选项

```bash
# 不提取图片，只保留原始 src
python3 "<skill-dir>/scripts/epub_xhtml_to_markdown.py" book.epub book.md --no-images

# 把 spine 中 linear="no" 的附录、注释页也加入正文
python3 "<skill-dir>/scripts/epub_xhtml_to_markdown.py" book.epub book.md --include-nonlinear

# 不写书名、作者等 YAML frontmatter
python3 "<skill-dir>/scripts/epub_xhtml_to_markdown.py" book.epub book.md --no-frontmatter

# 兼容旧工作流：输出一个合并的 Markdown，不生成章节目录
python3 "<skill-dir>/scripts/epub_xhtml_to_markdown.py" book.epub book.md --single-file

# 明确覆盖已有输出
python3 "<skill-dir>/scripts/epub_xhtml_to_markdown.py" book.epub book.md --force
```

## 输出规则

- 默认按章节输出，并创建一个 Obsidian 总装文件。例如：

  ```text
  book.md
  book_chapters/
  ├── 001-序章.md
  ├── 002-第一章.md
  └── 003-第二章.md
  book_assets/
  └── ...
  ```

- 总装文件包含 YAML frontmatter、章节目录和正文嵌入：

  ```markdown
  ## 目录

  1. [[book_chapters/001-序章|序章]]
  2. [[book_chapters/002-第一章|第一章]]

  ## 正文

  ![[book_chapters/001-序章]]

  ![[book_chapters/002-第一章]]
  ```

- 章节文件名使用三位 spine 序号和 XHTML 首个标题，保证排序稳定；没有标题时使用源 XHTML 文件名。
- 总装 YAML frontmatter 尽量读取 OPF 的 title、creator、language、identifier、publisher 和 date；缺失字段不编造。
- 图片写入 `<Markdown 文件名>_assets/`，保持书内相对目录，避免同名文件冲突。
- 用户明确需要一个文件时使用 `--single-file`，章节间用 `---` 分隔。
- 忽略 CSS、脚本、字体和不在 spine 中的导航资源。
- XHTML 解析失败时记录警告并继续其他章节；如果所有章节都失败，则以非零状态退出。
- 转换器面向语义内容，不承诺复刻字体、分页、浮动布局或复杂表格样式。

## 故障处理

| 症状 | 处理 |
|---|---|
| `File is not a zip file` | 文件不是有效 EPUB/ZIP；确认下载完整且扩展名未伪装 |
| 找不到 `META-INF/container.xml` | EPUB 结构损坏或不是标准 EPUB |
| 找不到 OPF/manifest/spine | 报告包结构问题，不按文件名盲目拼接正文 |
| 部分 XHTML XML 解析失败 | 报告具体章节；可先用 EPUBCheck/编辑器修复非法 XHTML 后重试 |
| 总装文件没有展开章节 | 确认总装文件和 `<书名>_chapters/` 位于同一个 Obsidian vault，并在阅读视图检查 |
| 输出几乎为空 | 检查是否为图片型或 fixed-layout EPUB；此 skill 不应改走 OCR，除非用户另行要求 |
| 图片缺失 | 检查图片是否为远程 URL、data URI、加密资源或 manifest 外文件 |
