import os
import re
from config import MAX_BLOCK_TEXT_LENGTH, SUPPORTED_LANGUAGES, RED, GREEN, YELLOW, RESET
from image_uploader import upload_image_to_dropbox
from urllib.parse import urlparse

# Module-level constants
MAX_NESTING_DEPTH = 3

# Cached regex for inline formatting using named groups.
INLINE_PATTERN = re.compile(
    r"(?P<code_block>```(?P<code_block_content>.*?)```)|"
    r"(?P<quad_inline_code>````(?P<quad_inline_code_content>.*?)````)|"
    r"(?P<double_inline_code>``(?P<double_inline_code_content>.*?)``)|"
    r"(?P<inline_code>`(?P<inline_code_content>.*?)`)|"
    r"(?P<strong_emph>\*\*\*(?P<strong_emph_content>.*?)\*\*\*)|"
    r"(?P<strong>\*\*(?P<strong_content>.*?)\*\*)|"
    r"(?P<emph>\*(?P<emph_content>.*?)\*)|"
    r"(?P<strike>~~(?P<strike_content>.*?)~~)|"
    r"(?P<link>\[(?P<link_text>.*?)\]\((?P<link_url>.*?)\))|"
    r"(?P<url>https?://\S+)",
    re.DOTALL
)

# Cached regex for markdown links in replace_md_links.
MD_LINK_PATTERN = re.compile(r'\[(.*?)\]\(([^)#]+)(?:#[^)]+)?\)')

def split_text_into_chunks(text, max_length=MAX_BLOCK_TEXT_LENGTH):
    """Splits text into chunks that fit within Notion's character limit."""
    return [text[i:i + max_length] for i in range(0, len(text), max_length)]

def check_for_image(text, base_path="."):
    """Check for an image in the text and upload if necessary."""
    image_match = re.search(r"!\[(.*?)\]\((.*?)\)", text)
    if not image_match:
        return text, None  # No image found, return unchanged text

    alt_text, image_path = image_match.groups()

    # Replace '%2F' with '/' if present.
    if '%2F' in image_path:
        image_path = image_path.replace('%2F', '/')

    # Only process local files (skip URLs)
    if image_path.startswith("http"):
        return text, None

    image_full_path = os.path.abspath(os.path.join(base_path, image_path))

    if not os.path.exists(image_full_path):
        print(f"{YELLOW}Warning: Image not found - {image_full_path}{RESET}")
        return text, None

    try:
        image_url = upload_image_to_dropbox(image_full_path)
        if not image_url:
            print(f"{RED}Error: Failed to upload image - {image_full_path}{RESET}")
            return text, None
    except Exception as e:
        print(f"{YELLOW}Exception during image upload: {e}{RESET}")
        return text, None

    # Remove the Markdown image syntax from the text
    text = text.replace(f"![{alt_text}]({image_path})", "").strip()

    # Return updated text and Notion image block
    image_block = {
        "object": "block",
        "type": "image",
        "image": {
            "type": "external",
            "external": {"url": image_url}
        }
    }
    return text, image_block

def is_valid_url(url):
    try:
        parsed = urlparse(url)
        return parsed.scheme in ['http', 'https'] and bool(parsed.netloc)
    except ValueError:
        return False

def format_rich_text(text):
    """
    Convert inline markdown formatting to Notion rich_text objects.
    Uses a cached regex with named groups for improved robustness.
    """
    rich_text = []
    pos = 0
    for match in INLINE_PATTERN.finditer(text):
        start, end = match.span()

        if start > pos:
            # Append plain text in between matches.
            rich_text.append({
                "type": "text",
                "text": {"content": text[pos:start]},
                "annotations": {"bold": False, "italic": False, "strikethrough": False, "underline": False, "code": False, "color": "default"}
            })

        if match.group("code_block"):
            content = match.group("code_block_content").strip()
            rich_text.append({
                "type": "text",
                "text": {"content": content},
                "annotations": {"code": True, "bold": False, "italic": False, "strikethrough": False, "underline": False, "color": "default"}
            })

        elif match.group("quad_inline_code"):
            content = match.group("quad_inline_code_content").strip()
            rich_text.append({
                "type": "text",
                "text": {"content": content},
                "annotations": {"code": True, "bold": False, "italic": False, "strikethrough": False, "underline": False, "color": "default"}
            })

        elif match.group("double_inline_code"):
            content = match.group("double_inline_code_content").strip()
            rich_text.append({
                "type": "text",
                "text": {"content": content},
                "annotations": {"code": True, "bold": False, "italic": False, "strikethrough": False, "underline": False, "color": "default"}
            })

        elif match.group("inline_code"):
            content = match.group("inline_code_content").strip()
            rich_text.append({
                "type": "text",
                "text": {"content": content},
                "annotations": {"code": True, "bold": False, "italic": False, "strikethrough": False, "underline": False, "color": "default"}
            })

        elif match.group("strong_emph"):
            content = match.group("strong_emph_content")
            rich_text.append({
                "type": "text",
                "text": {"content": content},
                "annotations": {"italic": True, "bold": True, "strikethrough": False, "underline": False, "code": False, "color": "default"}
            })

        elif match.group("strong"):
            content = match.group("strong_content")
            rich_text.append({
                "type": "text",
                "text": {"content": content},
                "annotations": {"bold": True, "italic": False, "strikethrough": False, "underline": False, "code": False, "color": "default"}
            })

        elif match.group("emph"):
            content = match.group("emph_content")
            rich_text.append({
                "type": "text",
                "text": {"content": content},
                "annotations": {"italic": True, "bold": False, "strikethrough": False, "underline": False, "code": False, "color": "default"}
            })

        elif match.group("strike"):
            content = match.group("strike_content")
            rich_text.append({
                "type": "text",
                "text": {"content": content},
                "annotations": {"strikethrough": True, "bold": False, "italic": False, "underline": False, "code": False, "color": "default"}
            })

        elif match.group("link"):
            link_text = match.group("link_text")
            link_url = match.group("link_url").strip()

            # If URL ends with .php or .json and isn't fully qualified, output as plain text.
            link_url_lower = link_url.lower()
            if (link_url_lower.endswith(('.php', '.json', '.drawio', '.pem', '.mind')) or link_url.startswith("#")) and not link_url_lower.startswith(('http://', 'https://')):
                rich_text.append({
                    "type": "text",
                    "text": {"content": link_text},
                    "annotations": {"bold": False, "italic": False, "strikethrough": False, "underline": False, "code": False, "color": "default"}
                })
            else:
                rich_text.append({
                    "type": "text",
                    "text": {"content": link_text, "link": {"url": link_url}},
                    "annotations": {"bold": False, "italic": False, "strikethrough": False, "underline": False, "code": False, "color": "default"}
                })

        elif match.group("url"):
            url = match.group("url")
            pre_char = text[match.start()-1] if match.start() > 0 else ""
            if pre_char in ['"', "'"] or not is_valid_url(url):
                rich_text.append({
                    "type": "text",
                    "text": {"content": url},
                    "annotations": {"bold": False, "italic": False, "strikethrough": False, "underline": False, "code": False, "color": "default"}
                })
            else:
                rich_text.append({
                    "type": "text",
                    "text": {"content": url, "link": {"url": url}},
                    "annotations": {"bold": False, "italic": False, "strikethrough": False, "underline": False, "code": False, "color": "default"}
                })

        pos = end
    if pos < len(text):
        rich_text.append({
            "type": "text",
            "text": {"content": text[pos:]},
            "annotations": {"bold": False, "italic": False, "strikethrough": False, "underline": False, "code": False, "color": "default"}
        })

    return rich_text if rich_text else [{"type": "text", "text": {"content": text}, "annotations": {"bold": False, "italic": False, "strikethrough": False, "underline": False, "code": False, "color": "default"}}]

def enforce_rich_text_limits(block):
    """
    Recursively ensure that every rich_text token in a block is within MAX_BLOCK_TEXT_LENGTH.
    If a token's content exceeds that limit, split it into multiple tokens.
    This function modifies the block in place.
    """
    # Determine where the rich_text tokens for different block types.
    token_list = None
    block_type = block.get("type")
    if block_type == "paragraph":
        token_list = block.get("paragraph", {}).get("rich_text", [])
    elif block_type in ["heading_1", "heading_2", "heading_3", "quote"]:
        token_list = block.get(block_type, {}).get("rich_text", [])
    elif block_type in ["bulleted_list_item", "numbered_list_item", "to_do"]:
        token_list = block.get(block_type, {}).get("rich_text", [])

    if token_list is not None:
        new_tokens = []
        for token in token_list:
            content = token["text"]["content"]
            if len(content) > MAX_BLOCK_TEXT_LENGTH:
                # Split the content into chunks.
                chunks = split_text_into_chunks(content, MAX_BLOCK_TEXT_LENGTH)
                for chunk in chunks:
                    new_token = {
                        "type": token["type"],
                        "text": {"content": chunk, "link": token["text"].get("link")},
                        "annotations": token.get("annotations", {"bold": False, "italic": False, "strikethrough": False, "underline": False, "code": False, "color": "default"})
                    }
                    new_tokens.append(new_token)
            else:
                new_tokens.append(token)
        # Update the token list in the block.
        if block_type == "paragraph":
            block["paragraph"]["rich_text"] = new_tokens
        elif block_type in ["heading_1", "heading_2", "heading_3", "quote"]:
            block[block_type]["rich_text"] = new_tokens
        elif block_type in ["bulleted_list_item", "numbered_list_item", "to_do"]:
            block[block_type]["rich_text"] = new_tokens

    # Recurse into children attached under the top-level "children" key.
    if "children" in block:
        for child in block["children"]:
            enforce_rich_text_limits(child)

    # Also, for list items, sometimes children are attached within their own property.
    if block_type in ["bulleted_list_item", "numbered_list_item", "to_do"]:
        children = block.get(block_type, {}).get("children", [])
        for child in children:
            enforce_rich_text_limits(child)

def md_to_notion_blocks(md_content, base_path="."):
    """Convert Markdown content into Notion API blocks."""
    blocks = []
    lines = md_content.split("\n")
    in_code_block = False
    code_language = "plain text"
    code_lines = []
    list_stack = []
    table_rows = []
    current_list_item = None
    current_item_indent = 0

    def process_cell(cell, base_path):
        """Process a table cell."""
        cell = cell.strip()
        processed_text, image_block = check_for_image(cell, base_path)
        if image_block:
            image_url = image_block["image"]["external"]["url"]
            # Return a token that displays a placeholder and links to the image.
            return [{
                "type": "text",
                "text": {"content": "[Image]", "link": {"url": image_url}},
                "annotations": {"bold": False, "italic": False, "strikethrough": False,
                                "underline": False, "code": False, "color": "default"}
            }]
        else:
            return format_rich_text(processed_text)

    def process_table():
        """Convert collected table rows to Notion table format, ensuring max 100 rows per table."""
        if not table_rows:
            return
        headers = table_rows[0]
        num_cols = len(headers)
        rows = table_rows[1:]
        chunk_size = 99  # Notion limit: 1 header + 99 rows

        for start in range(0, len(rows), chunk_size):
            table_chunk = [headers] + rows[start : start + chunk_size]
            notion_table = {
                "object": "block",
                "type": "table",
                "table": {
                    "table_width": num_cols,
                    "has_column_header": True,
                    "has_row_header": False,
                    "children": []
                }
            }

            for row in table_chunk:
                if len(row) < num_cols:
                    adjusted_row = row + [""] * (num_cols - len(row))
                else:
                    adjusted_row = row[:num_cols]

                row_block = {
                    "object": "block",
                    "type": "table_row",
                    "table_row": {
                        "cells": [process_cell(cell, base_path) if cell else [{"type": "text", "text": {"content": ""}}] for cell in adjusted_row]
                    }
                }
                notion_table["table"]["children"].append(row_block)
            blocks.append(notion_table)
        table_rows.clear()

    for line in lines:
        line = line.rstrip()

        # Code block handling
        if line.startswith("```"):
            # Count the leading backticks dynamically.
            num_backticks = 0
            for ch in line:
                if ch == '`':
                    num_backticks += 1
                else:
                    break
            fence = "`" * num_backticks

            # Check if the line contains both the opening and closing fence.
            if line.rstrip().endswith(fence) and len(line.strip()) > 2 * num_backticks:
                # Extract the inner content.
                inner = line[num_backticks:].strip()
                if inner.endswith(fence):
                    inner = inner[:-num_backticks].strip()
                # Try to detect a language specifier.
                parts = inner.split(None, 1)
                if len(parts) == 2 and parts[0].lower() in SUPPORTED_LANGUAGES:
                    code_language = parts[0].lower()
                    content = parts[1]
                else:
                    code_language = "plain text"
                    content = inner
                for chunk in split_text_into_chunks(content):
                    blocks.append({
                        "object": "block",
                        "type": "code",
                        "code": {
                            "rich_text": [{"type": "text", "text": {"content": chunk}}],
                            "language": "plain text"
                        }
                    })
                continue  # Process next line.
            else:
                if in_code_block:
                    if line.strip() == fence:
                        code_text = "\n".join(code_lines)
                        if code_language.lower() not in SUPPORTED_LANGUAGES:
                            code_language = "plain text"
                        for chunk in split_text_into_chunks(code_text):
                            blocks.append({
                                "object": "block",
                                "type": "code",
                                "code": {
                                    "rich_text": [{"type": "text", "text": {"content": chunk}}],
                                    "language": code_language
                                }
                            })
                        in_code_block = False
                        code_lines = []
                        fence = None  # Reset the fence
                    else:
                        code_lines.append(line)
                    continue  # Skip further processing of this line.
                else:
                    in_code_block = True
                    detected_language = line[num_backticks:].strip().lower() # The language specifier is any text after the fence.
                    code_language = detected_language if detected_language in SUPPORTED_LANGUAGES else "plain text"
                    code_lines = []  # Reset code_lines to start collecting code.
                    fence = fence  # Save the current fence.
                    continue  # Skip further processing of this line.

        elif in_code_block:
            code_lines.append(line)

        # Table handling
        elif re.match(r"^\|(.+)\|$", line):
            table_row = [cell.strip() for cell in line.split("|")[1:-1]]
            if not all(re.match(r"^-+$", cell) for cell in table_row):
                table_rows.append(table_row)
        elif table_rows and (line.strip() == "" or not line.startswith("|")):
            process_table()

        # Headings
        elif line.startswith("#"):
            heading_level = min(line.count("#"), 3)
            text = line.lstrip("#").strip()
            blocks.append({
                "object": "block",
                "type": f"heading_{heading_level}",
                f"heading_{heading_level}": {"rich_text": [{"type": "text", "text": {"content": text}}]}
            })

        # To-Do lists
        elif re.match(r"^\s*(-|\*)\s\[(x|X| )\]", line):
            indent_level = len(line) - len(line.lstrip())
            is_checked = "[x]" in line.lower()
            text = re.sub(r"^\s*(-|\*)\s\[(x|X| )\]\s*", "", line)
            list_item = {
                "object": "block",
                "type": "to_do",
                "to_do": {
                    "rich_text": format_rich_text(text),
                    "checked": is_checked,
                    "children": []
                }
            }
            while list_stack and list_stack[-1][0] >= indent_level:
                list_stack.pop()
            if list_stack:
                list_stack[-1][1]["to_do"].setdefault("children", []).append(list_item)
            else:
                blocks.append(list_item)
            list_stack.append((indent_level, list_item))

        # Bullet lists
        elif re.match(r"^\s*(-|\*)\s", line):
            indent_level = len(line) - len(line.lstrip())
            text = line.lstrip().lstrip("-*").strip()
            text, image_block = check_for_image(text, base_path)
            if image_block:
                blocks.append(image_block)
            list_item = {
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": format_rich_text(text)}
            }
            while list_stack and list_stack[-1][0] >= indent_level:
                list_stack.pop()
            if len(list_stack) >= MAX_NESTING_DEPTH:
                list_item = {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {"rich_text": format_rich_text("    " * (len(list_stack) - 1) + text)}
                }
                blocks.append(list_item)
                current_list_item = None
                current_item_indent = 0
            else:
                if list_stack:
                    parent_item = list_stack[-1][1]
                    parent_type = parent_item["type"]
                    if "children" not in parent_item[parent_type]:
                        parent_item[parent_type]["children"] = []
                    parent_item[parent_type]["children"].append(list_item)
                else:
                    blocks.append(list_item)
                current_list_item = list_item
                current_item_indent = indent_level
            list_stack.append((indent_level, list_item))

        # Numbered lists
        elif re.match(r"^\s*\d+\.\s", line):
            indent_level = len(line) - len(line.lstrip())
            text = line.lstrip().split(". ", 1)[1] if ". " in line else line
            text, image_block = check_for_image(text, base_path)
            if image_block:
                blocks.append(image_block)
            list_item = {
                "object": "block",
                "type": "numbered_list_item",
                "numbered_list_item": {"rich_text": format_rich_text(text)}
            }
            while list_stack and list_stack[-1][0] >= indent_level:
                list_stack.pop()
            if len(list_stack) >= MAX_NESTING_DEPTH:
                list_item = {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {"rich_text": format_rich_text("    " * (len(list_stack) - 1) + text)}
                }
                blocks.append(list_item)
                current_list_item = None
                current_item_indent = 0
            else:
                if list_stack:
                    parent_item = list_stack[-1][1]
                    parent_type = parent_item["type"]
                    if "children" not in parent_item[parent_type]:
                        parent_item[parent_type]["children"] = []
                    parent_item[parent_type]["children"].append(list_item)
                else:
                    blocks.append(list_item)
                current_list_item = list_item
                current_item_indent = indent_level
            list_stack.append((indent_level, list_item))

        # Blockquotes
        elif line.startswith(">"):
            text = line.lstrip(">").strip()
            blocks.append({
                "object": "block",
                "type": "quote",
                "quote": {"rich_text": format_rich_text(text)}
            })

        # Horizontal rule
        elif line.strip() == "---":
            blocks.append({
                "object": "block",
                "type": "divider",
                "divider": {}
            })

        # Image handling (if line contains a standalone image)
        elif re.match(r"!\[.*?\]\(.*?\)", line.lstrip()):
            line, image_block = check_for_image(line, base_path)
            if image_block:
                blocks.append(image_block)

        # If there's an empty line, treat it as a separate paragraph
        elif line.strip() == "":
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": [{"type": "text", "text": {"content": ""}}]}
            })
            current_list_item = None
            current_item_indent = 0

        # Regular paragraph with inline formatting
        elif line:
            text = line.strip()
            indent = len(line) - len(line.lstrip())
            if (current_list_item is not None and indent > current_item_indent and
                not re.match(r"^#{1,6}\s", text) and not text.startswith("**") and not text[0].isdigit()):
                key = current_list_item["type"]
                current_list_item[key]["rich_text"][-1]["text"]["content"] += " " + text

            elif (blocks and blocks[-1]["type"] == "paragraph" and
                  text and  # Ensure it's not an empty line
                  not text.startswith(("#", "**", "-", "*", ">", "`", "~~")) and
                  not text[0].isdigit() and
                  not re.match(r"^\s", text) and
                  not re.search(r"`.*?`", text) and
                  not re.search(r"\[.*?\]\(.*?\)", text)):
                # Append the text to the last paragraph
                blocks[-1]["paragraph"]["rich_text"][-1]["text"]["content"] += " " + text

            else:
                blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {"rich_text": format_rich_text(text)}
                })
                current_list_item = None
                current_item_indent = 0

    process_table()

    # Enforce rich_text limits for every block.
    for block in blocks:
        enforce_rich_text_limits(block)

    return blocks if blocks else []

def replace_md_links(markdown_content, mapping):
    """
    Replace markdown inline links that reference a local .md file with the corresponding Notion page URL.
    The mapping should be a dictionary where the keys are markdown filenames (e.g. "New.md")
    and the values are the corresponding Notion page URLs.
    """
    def repl(match):
        text = match.group(1)
        base_url = match.group(2).strip()
        if base_url.lower().endswith('.md'):
            filename = os.path.basename(base_url)
            if filename in mapping:
                return f"[{text}]({mapping[filename]})"
        return match.group(0)
    return MD_LINK_PATTERN.sub(repl, markdown_content)
