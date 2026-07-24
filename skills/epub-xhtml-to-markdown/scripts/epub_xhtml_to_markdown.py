#!/usr/bin/env python3
"""Convert a reflowable EPUB to Markdown by reading its XHTML spine."""

from __future__ import annotations

import argparse
import posixpath
import re
import shutil
import sys
import urllib.parse
import zipfile
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET


CONTAINER_NS = {"c": "urn:oasis:names:tc:opendocument:xmlns:container"}
BLOCK_TAGS = {
    "address", "article", "aside", "blockquote", "body", "dd", "div", "dl",
    "dt", "figcaption", "figure", "footer", "header", "main", "nav", "p",
    "section",
}
SKIP_TAGS = {"script", "style", "svg"}


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def normalize_zip_path(base: str, href: str) -> str:
    decoded = urllib.parse.unquote(href.split("#", 1)[0])
    normalized = posixpath.normpath(posixpath.join(posixpath.dirname(base), decoded))
    if normalized == ".." or normalized.startswith("../") or normalized.startswith("/"):
        raise ValueError(f"unsafe EPUB archive path: {href}")
    return normalized


def yaml_string(value: str) -> str:
    value = re.sub(r"\s+", " ", value).strip()
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def collapse_inline(text: str) -> str:
    return re.sub(r"[ \t\r\f\v]+", " ", text)


def tidy_markdown(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


@dataclass
class ManifestItem:
    item_id: str
    path: str
    media_type: str
    properties: set[str]


@dataclass
class Chapter:
    number: int
    title: str
    filename: str
    markdown: str


def chapter_title(root: ET.Element, item_path: str, number: int) -> str:
    for wanted in ("h1", "h2", "h3", "h4", "h5", "h6", "title"):
        for element in root.iter():
            if local_name(element.tag) != wanted:
                continue
            value = " ".join("".join(element.itertext()).split())
            if value:
                return value
    fallback = Path(item_path).stem.replace("_", " ").replace("-", " ").strip()
    return fallback or f"Chapter {number}"


def safe_chapter_filename(title: str, number: int) -> str:
    # Exclude filesystem-reserved and wikilink-special characters.
    name = re.sub(r'[\\/:*?"<>|#^\\[\\]]+', "-", title)
    name = re.sub(r"\s+", " ", name).strip(" .-")
    if not name:
        name = f"chapter-{number}"
    return f"{number:03d}-{name[:80].rstrip(' .-')}.md"


def obsidian_label(title: str) -> str:
    return title.replace("|", "｜").replace("]", "］").replace("\n", " ").strip()


class XHTMLRenderer:
    def __init__(
        self,
        archive: zipfile.ZipFile,
        document_path: str,
        assets_dir: Path,
        link_from_dir: Path,
        extract_images: bool,
        warnings: list[str],
    ) -> None:
        self.archive = archive
        self.document_path = document_path
        self.assets_dir = assets_dir
        self.link_from_dir = link_from_dir
        self.extract_images = extract_images
        self.warnings = warnings
        self.list_depth = 0

    def render(self, root: ET.Element) -> str:
        body = next((el for el in root.iter() if local_name(el.tag) == "body"), root)
        return tidy_markdown(self._node(body))

    def _children(self, node: ET.Element) -> str:
        parts = [collapse_inline(node.text or "")]
        for child in node:
            parts.append(self._node(child))
            parts.append(collapse_inline(child.tail or ""))
        return "".join(parts)

    def _node(self, node: ET.Element) -> str:
        tag = local_name(node.tag)
        if tag in SKIP_TAGS:
            return ""
        if tag in {"ul", "ol"}:
            self.list_depth += 1
            rendered = "".join(self._node(child) + collapse_inline(child.tail or "") for child in node)
            self.list_depth -= 1
            return f"\n{rendered.strip()}\n"
        if tag == "table":
            return self._table(node)
        if tag == "pre":
            code = "".join(node.itertext()).strip("\n")
            return f"\n\n```\n{code}\n```\n\n" if code else ""

        inner = self._children(node)
        clean = inner.strip()

        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            level = int(tag[1])
            return f"\n\n{'#' * level} {clean}\n\n" if clean else ""
        if tag in BLOCK_TAGS:
            if tag == "blockquote":
                quoted = "\n".join(f"> {line}" if line else ">" for line in tidy_markdown(inner).splitlines())
                return f"\n\n{quoted}\n\n" if quoted else ""
            return f"\n\n{clean}\n\n" if clean else ""
        if tag == "br":
            return "  \n"
        if tag == "hr":
            return "\n\n---\n\n"
        if tag in {"strong", "b"}:
            return f"**{clean}**" if clean else ""
        if tag in {"em", "i"}:
            return f"*{clean}*" if clean else ""
        if tag == "del":
            return f"~~{clean}~~" if clean else ""
        if tag == "sup":
            return f"<sup>{clean}</sup>" if clean else ""
        if tag == "sub":
            return f"<sub>{clean}</sub>" if clean else ""
        if tag == "code":
            return f"`{clean.replace('`', '``')}`" if clean else ""
        if tag == "a":
            href = node.attrib.get("href", "").strip()
            if not href:
                return clean
            return f"[{clean or href}]({href.replace(' ', '%20')})"
        if tag == "img":
            src = node.attrib.get("src", "").strip()
            alt = node.attrib.get("alt", "").strip()
            return self._image(src, alt)
        if tag == "li":
            marker = node.attrib.pop("_md_marker", "-")
            lines = tidy_markdown(inner).splitlines() or [""]
            indent = "  " * max(self.list_depth - 1, 0)
            continuation = "\n".join(f"{indent}  {line}" for line in lines[1:])
            return f"{indent}{marker} {lines[0]}{f'{chr(10)}{continuation}' if continuation else ''}\n"
        return inner

    def _image(self, src: str, alt: str) -> str:
        if not src:
            return ""
        if not self.extract_images or re.match(r"^(?:data:|https?://)", src, re.I):
            return f"![{alt}]({src.replace(' ', '%20')})"

        archive_path = normalize_zip_path(self.document_path, src)
        if archive_path not in self.archive.namelist():
            self.warnings.append(f"image not found: {archive_path}")
            return f"![{alt}]({src.replace(' ', '%20')})"

        relative = Path(*archive_path.split("/"))
        target = self.assets_dir / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        with self.archive.open(archive_path) as source, target.open("wb") as destination:
            shutil.copyfileobj(source, destination)
        markdown_path = Path(
            posixpath.relpath(target.as_posix(), self.link_from_dir.as_posix())
        ).as_posix()
        return f"![{alt}]({urllib.parse.quote(markdown_path, safe='/')})"

    def _table(self, table: ET.Element) -> str:
        rows: list[list[str]] = []
        for row in table.iter():
            if local_name(row.tag) != "tr":
                continue
            cells = [
                tidy_markdown("".join(cell.itertext())).replace("|", "\\|").replace("\n", " ")
                for cell in row
                if local_name(cell.tag) in {"th", "td"}
            ]
            if cells:
                rows.append(cells)
        if not rows:
            return ""
        width = max(len(row) for row in rows)
        rows = [row + [""] * (width - len(row)) for row in rows]
        header = rows[0]
        lines = [
            "| " + " | ".join(header) + " |",
            "| " + " | ".join(["---"] * width) + " |",
        ]
        lines.extend("| " + " | ".join(row) + " |" for row in rows[1:])
        return "\n\n" + "\n".join(lines) + "\n\n"


def assign_list_markers(root: ET.Element) -> None:
    for parent in root.iter():
        tag = local_name(parent.tag)
        if tag not in {"ul", "ol"}:
            continue
        marker = "1." if tag == "ol" else "-"
        for child in parent:
            if local_name(child.tag) == "li":
                child.attrib["_md_marker"] = marker


def read_package(archive: zipfile.ZipFile) -> tuple[str, ET.Element]:
    try:
        container = ET.fromstring(archive.read("META-INF/container.xml"))
    except KeyError as exc:
        raise ValueError("missing META-INF/container.xml") from exc
    rootfile = container.find(".//c:rootfile", CONTAINER_NS)
    if rootfile is None:
        rootfile = next((el for el in container.iter() if local_name(el.tag) == "rootfile"), None)
    if rootfile is None or not rootfile.attrib.get("full-path"):
        raise ValueError("container.xml does not identify an OPF package")
    package_path = urllib.parse.unquote(rootfile.attrib["full-path"])
    try:
        package = ET.fromstring(archive.read(package_path))
    except KeyError as exc:
        raise ValueError(f"OPF package not found: {package_path}") from exc
    except ET.ParseError as exc:
        raise ValueError(f"invalid OPF package XML: {exc}") from exc
    return package_path, package


def package_metadata(package: ET.Element) -> dict[str, str]:
    wanted = {"title", "creator", "language", "identifier", "publisher", "date"}
    result: dict[str, str] = {}
    for element in package.iter():
        name = local_name(element.tag)
        value = " ".join("".join(element.itertext()).split())
        if name in wanted and value and name not in result:
            result[name] = value
    return result


def package_items(package_path: str, package: ET.Element) -> tuple[dict[str, ManifestItem], list[tuple[str, bool]]]:
    manifest: dict[str, ManifestItem] = {}
    spine: list[tuple[str, bool]] = []
    for element in package.iter():
        tag = local_name(element.tag)
        if tag == "item" and element.attrib.get("id") and element.attrib.get("href"):
            item_id = element.attrib["id"]
            manifest[item_id] = ManifestItem(
                item_id=item_id,
                path=normalize_zip_path(package_path, element.attrib["href"]),
                media_type=element.attrib.get("media-type", ""),
                properties=set(element.attrib.get("properties", "").split()),
            )
        elif tag == "itemref" and element.attrib.get("idref"):
            spine.append((element.attrib["idref"], element.attrib.get("linear", "yes").lower() != "no"))
    if not manifest:
        raise ValueError("OPF manifest is empty")
    if not spine:
        raise ValueError("OPF spine is empty")
    return manifest, spine


def frontmatter(metadata: dict[str, str]) -> str:
    lines = ["---", "source_type: epub"]
    for key in ("title", "creator", "language", "identifier", "publisher", "date"):
        if key in metadata:
            lines.append(f"{key}: {yaml_string(metadata[key])}")
    lines.extend(["---", ""])
    return "\n".join(lines)


def assembly_markdown(
    metadata: dict[str, str],
    chapters: list[Chapter],
    chapters_dir: Path,
    include_frontmatter: bool,
    fallback_title: str,
) -> str:
    parts: list[str] = []
    if include_frontmatter:
        parts.append(frontmatter(metadata).rstrip())
    book_title = metadata.get("title", fallback_title)
    parts.extend([f"# {book_title}", "", "## 目录", ""])
    for chapter in chapters:
        target = f"{chapters_dir.name}/{Path(chapter.filename).stem}"
        parts.append(f"{chapter.number}. [[{target}|{obsidian_label(chapter.title)}]]")
    parts.extend(["", "## 正文", ""])
    for chapter in chapters:
        target = f"{chapters_dir.name}/{Path(chapter.filename).stem}"
        parts.extend([f"![[{target}]]", ""])
    return "\n".join(parts).rstrip() + "\n"


def convert(args: argparse.Namespace) -> tuple[int, list[str]]:
    source = Path(args.input).expanduser().resolve()
    output = Path(args.output).expanduser().resolve()
    chapters_dir = output.with_name(f"{output.stem}_chapters")
    assets_dir = output.with_name(f"{output.stem}_assets")
    if not source.is_file():
        raise ValueError(f"input file not found: {source}")
    if output.exists() and not args.force:
        raise ValueError(f"output already exists (use --force to overwrite): {output}")
    if not args.single_file and chapters_dir.exists() and not args.force:
        raise ValueError(
            f"chapter directory already exists (use --force to overwrite files): {chapters_dir}"
        )
    if assets_dir.exists() and not args.force:
        raise ValueError(
            f"asset directory already exists (use --force to overwrite files): {assets_dir}"
        )
    output.parent.mkdir(parents=True, exist_ok=True)

    warnings: list[str] = []
    chapters: list[Chapter] = []
    with zipfile.ZipFile(source) as archive:
        package_path, package = read_package(archive)
        metadata = package_metadata(package)
        manifest, spine = package_items(package_path, package)
        if "META-INF/encryption.xml" in archive.namelist():
            warnings.append(
                "META-INF/encryption.xml is present; encrypted resources may not convert"
            )
        for item_id, is_linear in spine:
            if not is_linear and not args.include_nonlinear:
                continue
            item = manifest.get(item_id)
            if item is None:
                warnings.append(f"spine item missing from manifest: {item_id}")
                continue
            if item.media_type not in {"application/xhtml+xml", "text/html"}:
                warnings.append(f"skipped non-XHTML spine item: {item.path} ({item.media_type})")
                continue
            try:
                root = ET.fromstring(archive.read(item.path))
                assign_list_markers(root)
                number = len(chapters) + 1
                title = chapter_title(root, item.path, number)
                filename = safe_chapter_filename(title, number)
                link_from_dir = output.parent if args.single_file else chapters_dir
                renderer = XHTMLRenderer(
                    archive,
                    item.path,
                    assets_dir,
                    link_from_dir,
                    not args.no_images,
                    warnings,
                )
                rendered = renderer.render(root)
            except KeyError:
                warnings.append(f"chapter not found: {item.path}")
                continue
            except ET.ParseError as exc:
                warnings.append(f"invalid XHTML skipped: {item.path}: {exc}")
                continue
            if rendered:
                chapters.append(
                    Chapter(
                        number=number,
                        title=title,
                        filename=filename,
                        markdown=rendered,
                    )
                )
            else:
                warnings.append(f"empty XHTML skipped: {item.path}")

    if not chapters:
        raise ValueError("no readable XHTML chapters were found in the EPUB spine")
    if args.single_file:
        content = ""
        if not args.no_frontmatter:
            content += frontmatter(metadata)
        content += "\n\n---\n\n".join(chapter.markdown for chapter in chapters).strip() + "\n"
        output.write_text(content, encoding="utf-8")
    else:
        chapters_dir.mkdir(parents=True, exist_ok=True)
        for chapter in chapters:
            chapter_path = chapters_dir / chapter.filename
            if chapter_path.exists() and not args.force:
                raise ValueError(
                    f"chapter file already exists (use --force to overwrite): {chapter_path}"
                )
            chapter_path.write_text(chapter.markdown.rstrip() + "\n", encoding="utf-8")
        output.write_text(
            assembly_markdown(
                metadata,
                chapters,
                chapters_dir,
                not args.no_frontmatter,
                source.stem,
            ),
            encoding="utf-8",
        )
    return len(chapters), warnings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Convert EPUB spine XHTML to chapter Markdown files and an Obsidian assembly note."
        )
    )
    parser.add_argument("input", help="source .epub file")
    parser.add_argument("output", help="destination .md file")
    parser.add_argument("--no-images", action="store_true", help="do not extract embedded images")
    parser.add_argument(
        "--include-nonlinear",
        action="store_true",
        help='include spine entries marked linear="no"',
    )
    parser.add_argument("--no-frontmatter", action="store_true", help="omit YAML frontmatter")
    parser.add_argument(
        "--single-file",
        action="store_true",
        help="write one combined Markdown file instead of Obsidian chapter embeds",
    )
    parser.add_argument("--force", action="store_true", help="overwrite an existing Markdown file")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        count, warnings = convert(args)
    except (ValueError, OSError, zipfile.BadZipFile) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    output = Path(args.output).expanduser().resolve()
    print(f"converted {count} XHTML chapter(s) -> {output}")
    if not args.single_file:
        print(f"chapters: {output.with_name(f'{output.stem}_chapters')}")
    assets_dir = output.with_name(f"{output.stem}_assets")
    if assets_dir.exists():
        print(f"assets: {assets_dir}")
    for warning in warnings:
        print(f"warning: {warning}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
