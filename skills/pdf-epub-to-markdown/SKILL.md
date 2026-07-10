---
name: pdf-epub-to-markdown
description: Use when converting PDF, EPUB, DOCX, PPTX, XLSX, HTML, or image files to Markdown for an Obsidian vault. Triggers on "把 PDF 转 markdown"、"EPUB 转 md"、"导读书籍到 Obsidian"、"marker-pdf"、"批量转换文档". Detects and installs marker-pdf via uv.
---

# PDF / EPUB → Markdown (Obsidian)

## 概述

把 PDF、EPUB 等文档转换为 Markdown 并放入 Obsidian vault。底层工具是 [marker-pdf](https://github.com/datalab-to/marker)（支持 PDF / EPUB / DOCX / PPTX / XLSX / HTML / 图片，所有语言）。通过 `uv tool` 管理依赖，不污染 vault 环境。

## 何时使用

- 用户要求把 PDF / EPUB / DOCX 等转成 Markdown
- 把电子书导入 Obsidian vault 做读书笔记
- 批量转换一个目录里的文档

## 前置依赖：uv

本 skill 依赖 [uv](https://docs.astral.sh/uv/) 管理 marker-pdf。**开始任何转换前必须先检测：**

```bash
which uv && uv --version
```

- ✅ 有输出 → 继续
- ❌ 未找到 → **立即暂停，不要尝试 pip / brew 等替代方案。** 提示用户：

> 需要先安装 uv 才能使用本 skill。
> 推荐安装命令（任选其一）：
> - macOS / Linux：`curl -LsSf https://astral.sh/uv/install.sh | sh`
> - Homebrew：`brew install uv`
> - Windows：`powershell -c "irm https://astral.sh/uv/install.ps1 | iex"`
> 安装后重新打开终端，再重新触发本 skill。

## 检测与安装 marker-pdf

确认 uv 可用后，检测 marker-pdf：

```bash
marker_single --version 2>/dev/null || marker --help >/dev/null 2>&1
```

若未安装（上述命令均失败），用 `uv tool` 安装：

```bash
uv tool install "marker-pdf[full]"
```

> **为什么用 `[full]` extras**：纯 `marker-pdf` 只支持 PDF；`[full]` 才解锁 EPUB / DOCX / PPTX / XLSX / HTML 等格式。

如需升级已有版本（用户要求 `uv tool upgrade marker-pdf` 时）：

```bash
uv tool upgrade marker-pdf
```

安装完成后重新检测确认成功，再进入转换流程。

## 转换流程

### 1. 确认参数

开始前向用户确认（或从上下文推断）：

| 参数 | 说明 |
|---|---|
| 源文件 / 目录 | 单文件路径，或一个包含多个文档的目录 |
| 目标目录 | Obsidian vault 中的存放位置（如 `vault/books/`）。需确认存在，不存在则 `mkdir -p` |
| 是否提取图片 | 默认提取，图片与 `.md` 同目录存放。Vault 内通常建议提取 |
| OCR 语言 | 中文书用 `--langs "Chinese,English"`；英文用 `--langs English`。不确定时不传，让 marker 自动 |

### 2. 单文件转换

```bash
marker_single "/path/to/book.pdf" \
  --output_format markdown \
  --output_dir "/path/to/vault/books/" \
  --langs "Chinese,English"
```

EPUB 同理（需 `[full]` extras）：

```bash
marker_single "/path/to/book.epub" \
  --output_format markdown \
  --output_dir "/path/to/vault/books/" \
  --langs "Chinese,English"
```

### 3. 批量转换一整个目录

```bash
marker "/input/dir/" "/path/to/vault/books/" \
  --workers 4 \
  --output_format markdown
```

- `--workers N`：并行进程数，每个约用 5GB 显存峰值 / 3.5GB 平均。CPU 环境保持默认或设为 1-2。

### 4. 常用 CLI 选项

| 选项 | 作用 |
|---|---|
| `--output_format markdown\|json\|html\|chunks` | 输出格式，本 skill 固定 `markdown` |
| `--output_dir PATH` | 输出目录，默认 `settings.OUTPUT_DIR` |
| `--workers N` | 批量转换的并行度（`marker` 子命令）|
| `--force_ocr` | 强制对所有页面 OCR（扫描书 / 乱码时用）|
| `--strip_existing_ocr` | 移除已有 OCR 文本层并重新 OCR |
| `--langs "Chinese,English"` | OCR 语言，逗号分隔 |
| `--page_range "0,5-10,20"` | 只处理指定页 |
| `--disable_image_extraction` | 不提取图片（纯文本 / 节省空间时用）|
| `--use_llm` | 用 LLM 提升准确率（需另行配置 LLM 后端，非本 skill 默认）|

完整列表：`marker_single --help`。

### 5. 整理输出到 Obsidian

转换完成后，marker 在 `--output_dir` 下为每个源文件生成：

```
<output_dir>/
├── book_name/
│   ├── book_name.md          # ⭐ 主 Markdown 文件，Obsidian 打开这个
│   └── (图片资源)            # 嵌入的图片，路径已相对引用
```

推荐做法：

1. **归集 `.md`**：主笔记就是每个子目录里的 `.md` 文件。
2. **重命名**（可选）：按 Obsidian 命名习惯 rename，例如 `<书名> - <作者>.md`。
3. **加 frontmatter**（可选）：给 `.md` 顶部加 YAML 属性，便于 Bases / Dataview 检索：

   ```yaml
   ---
   source_type: epub
   author: <作者>
   converted: 2026-07-10
   ---
   ```

4. 同步图片路径：marker 的 `.md` 用相对路径引用同目录图片，迁移时保持目录完整即可。若只搬 `.md` 不搬图片，加上 `--disable_image_extraction` 重跑。

## 故障排查

| 症状 | 处理 |
|---|---|
| `uv: command not found` | 见上方"前置依赖"流程，**暂停并提示用户安装 uv** |
| `marker_single: command not found` | `uv tool install "marker-pdf[full]"` |
| 中文乱码 | 加 `--force_ocr --langs "Chinese,English"` |
| EPUB 报错 `No module named marker.converters.epub` | 重装 `[full]`：`uv tool install "marker-pdf[full]" --force` |
| 显存不足 / OOM | `--workers 1`；或设环境变量 `TORCH_DEVICE=cpu` 走 CPU |
| 输出里图片丢失 | 把 `<output_dir>/<book_name>/` 整个目录搬进 vault，或 `--disable_image_extraction` 只要文字 |
| 第一行报 `usage: marker_single ...` 参数错误 | 确认 marker-pdf 版本 ≥ 1.0，老版本参数格式不同。`uv tool upgrade marker-pdf` |

## 约束

- **不要**在没有 uv 时绕路用 `pip install`、`brew install marker` 等——会让依赖散落，违背本 skill 设计。
- **不要**删除或移动 marker 原始输出目录里的图片，否则 `.md` 引用会全部断裂。
- 大书（>500 页）转换很慢且占内存，先用 `--page_range` 试跑几页确认质量。
- 不擅自调用 `--use_llm`——会触发额外 API 费用，需用户显式同意。
