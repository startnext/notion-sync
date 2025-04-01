import os
import requests
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from config import HEADERS, NOTION_ROOT_PAGE_ID, BLOCK_LIMIT, BASE_DIR, RED, YELLOW, GREEN, RESET
from markdown_parser import md_to_notion_blocks

# Global session with retries
session = requests.Session()
retries = Retry(
    total=5,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["HEAD", "GET", "OPTIONS", "POST", "PATCH", "DELETE"]
)
adapter = HTTPAdapter(max_retries=retries)
session.mount("https://", adapter)
session.mount("http://", adapter)

folder_cache = {} # Cache for storing folder page IDs

def get_all_notion_pages(parent_id, parent_path=""):
    """Recursively fetch all Notion pages under a given parent page and store full paths."""
    print("Fetching All Notion Pages to compare with local...")

    def fetch_pages(parent, current_path):
        """Fetch all child pages for a given parent page."""
        url = f"https://api.notion.com/v1/blocks/{parent}/children"
        notion_pages = {}  # Store pages with full relative paths
        next_cursor = None

        while True:
            params = {"page_size": 100}
            if next_cursor:
                params["start_cursor"] = next_cursor

            response = session.get(url, headers=HEADERS, params=params)
            if response.status_code != 200:
                print(f"{RED}Error fetching pages: {response.status_code}, {response.text}{RESET}")
                return notion_pages

            data = response.json()
            results = data.get("results", [])
            next_cursor = data.get("next_cursor")

            for page in results:
                if page["object"] == "block" and page["type"] == "child_page":
                    sub_page_id = page["id"]
                    page_title = page["child_page"]["title"].strip()

                    # Construct full relative path
                    full_path = os.path.join(current_path, page_title)

                    # Store in dictionary
                    notion_pages[full_path] = sub_page_id

                    # Recursively fetch subpages
                    notion_pages.update(fetch_pages(sub_page_id, full_path))

            if not next_cursor:
                break

        return notion_pages

    return fetch_pages(parent_id, parent_path)

def get_existing_child_pages(parent_id):
    """Fetch all child pages under a parent to check for existing pages."""
    url = f"https://api.notion.com/v1/blocks/{parent_id}/children"
    response = session.get(url, headers=HEADERS)

    if response.status_code == 200:
        return response.json().get("results", [])
    else:
        print(f"{RED}Error fetching existing pages: {response.status_code}, {response.text}{RESET}")
        return []

def search_existing_page(title, parent_id):
    """Search recursively for an existing Notion page matching the title."""
    child_pages = get_existing_child_pages(parent_id)

    for page in child_pages:
        if page["object"] == "block" and page["type"] == "child_page":
            page_title = page["child_page"]["title"]
            if page_title == title:
                return page["id"]  # Return existing page ID

            # Recursively check inside this child page
            sub_page_id = page["id"]
            found_page_id = search_existing_page(title, sub_page_id)
            if found_page_id:
                return found_page_id

    return None  # No existing page found

def get_existing_page_content(page_id):
    """Fetch the current content of a Notion page."""
    url = f"https://api.notion.com/v1/blocks/{page_id}/children"
    response = session.get(url, headers=HEADERS)

    if response.status_code == 200:
        return response.json().get("results", [])
    else:
        print(f"{RED}Error fetching page content: {response.status_code}, {response.text}{RESET}")
        return []

def archive_page_in_notion(page_id):
    """Archives a Notion page instead of deleting it."""

    url = f"https://api.notion.com/v1/pages/{page_id}"
    data = {"archived": True}

    response = session.patch(url, headers=HEADERS, json=data)

    if response.status_code == 200:
        print(f"{GREEN}Successfully archived Notion page (ID: {page_id}){RESET}")
        return "deleted"
    else:
        print(f"{RED}Failed to archive Notion page (ID: {page_id}) | Status Code: {response.status_code}{RESET}")
        print(f"Response: {response.text}")

def delete_notion_page_if_missing(local_md_files):
    """Archives Notion pages that correspond to missing local Markdown files."""
    notion_pages = get_all_notion_pages(NOTION_ROOT_PAGE_ID)  # Get all Notion pages with full paths

    # Ensure local filenames **store full relative paths WITH `.md`**
    local_file_names = {os.path.relpath(f, BASE_DIR) for f in local_md_files}

    # Extract **folder structure** to track subdirectories
    local_folders = set()
    for f in local_md_files:
        folder_path = os.path.dirname(f)
        while folder_path and folder_path != BASE_DIR:
            local_folders.add(os.path.relpath(folder_path, BASE_DIR))  # Keep relative paths
            folder_path = os.path.dirname(folder_path)

    remaining_folders = {}  # Store folder pages to process later
    deleted_pages = 0  # Track deleted pages

    for notion_path, page_id in notion_pages.items():
        # Check if this Notion page represents a Markdown file
        if notion_path.endswith(".md"):
            if notion_path not in local_file_names:
                print(f"{RED}Detected missing file: {notion_path} | Archiving Notion page...{RESET}")
                status = archive_page_in_notion(page_id)
                if status == "deleted":
                    deleted_pages += 1

        # Check if this Notion page represents a folder
        else:
            remaining_folders[notion_path] = page_id

    # Process folder deletions
    for folder_path, folder_page_id in remaining_folders.items():
        if folder_path not in local_folders:
            child_pages = get_existing_child_pages(folder_page_id)  # Get Notion folder children

            if not child_pages:  # Only delete if it's empty
                print(f"{RED}Folder {folder_path} is now empty. Archiving Notion folder page...{RESET}")
                archive_page_in_notion(folder_page_id)

    return deleted_pages

def extract_full_text(blocks):
    """Extracts all Notion block content into a single formatted text string for comparison."""
    text_list = []

    for block in blocks:
        # Handle checkboxes (to-do items)
        if "to_do" in block and "rich_text" in block["to_do"]:
            checkbox_state = "[x]" if block["to_do"]["checked"] else "[ ]"
            text_content = " ".join(rt["text"]["content"] for rt in block["to_do"]["rich_text"])
            text_list.append(f"{checkbox_state} {text_content}")

        # Handle text-based content
        for key in ["paragraph", "heading_1", "heading_2", "heading_3", "bulleted_list_item", "numbered_list_item", "quote"]:
            if key in block and "rich_text" in block[key]:
                text_list.append(" ".join(rt["text"]["content"] for rt in block[key]["rich_text"]))

        # Handle dividers
        if "divider" in block:
            text_list.append("---")

        # Handle images
        if "image" in block and "external" in block["image"]:
            text_list.append(f"![Image]({block['image']['external']['url']})")

        # Handle code blocks
        if "code" in block and "rich_text" in block["code"]:
            code_text = "\n".join(rt["text"]["content"] for rt in block["code"]["rich_text"])
            text_list.append(f"```{block['code'].get('language', 'plain text')}\n{code_text}\n```")

        # Handle tables
        if "table" in block and "children" in block["table"]:
            table_data = []
            for row in block["table"]["children"]:
                if "table_row" in row and "cells" in row["table_row"]:
                    row_data = " | ".join(
                        " ".join(cell["text"]["content"] for cell in cell_list if "text" in cell)
                        for cell_list in row["table_row"]["cells"]
                    )
                    table_data.append(row_data)
            text_list.append("\n".join(table_data))

    return "\n".join(text_list).strip()

def content_has_changed(existing_blocks, new_blocks):
    """Compares full Notion page content with new Markdown content as a single formatted string."""
    return extract_full_text(existing_blocks) != extract_full_text(new_blocks)

def delete_existing_content(page_id):
    """Delete all content blocks from an existing Notion page before updating."""
    url = f"https://api.notion.com/v1/blocks/{page_id}/children"
    params = {"page_size": 100}

    while True:
        response = session.get(url, headers=HEADERS, params=params)
        if response.status_code != 200:
            print(f"{RED}Error fetching content for deletion: {response.status_code}, {response.text}{RESET}")
            break

        data = response.json()
        blocks = data.get("results", [])

        # Delete each block in the current batch.
        for block in blocks:
            if block["object"] == "block" and block.get("id"):
                block_id = block.get("id")
                del_response = session.delete(f"https://api.notion.com/v1/blocks/{block_id}", headers=HEADERS)
                if del_response.status_code != 200:
                    print(f"{RED}Failed to delete block {block_id}: {del_response.status_code} - {del_response.text}{RESET}")

        # Check if there are more blocks.
        if data.get("has_more"):
            params["start_cursor"] = data.get("next_cursor")
        else:
            break

    print(f"{YELLOW}Cleared old content from page (ID: {page_id}){RESET}")

def create_or_update_notion_page(title, parent_id, blocks, is_folder=False):
    """Create a new Notion page or update an existing one if found."""
    existing_page_id = search_existing_page(title, parent_id)

    if existing_page_id:
        existing_blocks = get_existing_page_content(existing_page_id)

        if not content_has_changed(existing_blocks, blocks):
            print(f"Page '{title}' is already up to date. Skipping update.")
            return existing_page_id  # No need to update if content hasn't changed

        print(f"{YELLOW}Page '{title}' content has changed. Updating...{RESET}")
        delete_existing_content(existing_page_id)
        upload_blocks_to_notion(existing_page_id, blocks)
        return existing_page_id

    payload = {
        "parent": {"page_id": parent_id},
        "properties": {"title": {"title": [{"text": {"content": title}}]}},
    }
    if is_folder:
        payload["icon"] = {"emoji": "🗂️"}

    print(f"{GREEN}Creating new Notion page: {title}{RESET}")
    response = session.post("https://api.notion.com/v1/pages", json=payload, headers=HEADERS)
    if response.status_code == 200:
        page_id = response.json().get("id")
        upload_blocks_to_notion(page_id, blocks)  # Upload content immediately
        return page_id
    else:
        print(f"{RED}Failed to create Notion page: {title} | Error: {response.status_code} - {response.text}{RESET}")
        return None

def get_or_create_folder_page(folder_path):
    """Ensure Notion folder pages match directory structure recursively."""
    parent_id = NOTION_ROOT_PAGE_ID
    folders = folder_path.split(os.sep)

    for folder in folders:
        if folder in folder_cache:
            parent_id = folder_cache[folder]
        else:
            folder_id = search_existing_page(folder, parent_id)
            if not folder_id:
                folder_id = create_or_update_notion_page(folder, parent_id, [], is_folder=True)
            if folder_id:
                folder_cache[folder] = folder_id
                parent_id = folder_id
    return parent_id

def upload_blocks_to_notion(page_id, blocks):
    """Upload content blocks to Notion in chunks, ensuring no empty pages."""
    if not blocks:
        print(f"Skipping empty block upload for page (ID: {page_id})")
        return

    for i in range(0, len(blocks), BLOCK_LIMIT):
        response = session.patch(
            f"https://api.notion.com/v1/blocks/{page_id}/children",
            json={"children": blocks[i:i + BLOCK_LIMIT]},
            headers=HEADERS
        )
        if response.status_code == 200:
            print(f"{GREEN}Successfully updated Notion page (ID: {page_id}){RESET}")
        else:
            print(f"{RED}Error updating blocks: {response.status_code}, {response.text}{RESET}")
            return "failed"

    return "updated"

def upload_markdown_file_to_notion(file_path, update_content=False, new_content=None):
    """Upload a Markdown file as a Notion page inside its folder structure.

    If update_content is False, a minimal content is uploaded (or the page is created if missing).
    If update_content is True, then the file’s content is used, converted to Notion blocks, and the page is updated if
    changes are detected.
    """
    file_name = os.path.basename(file_path)
    base_path = os.path.dirname(file_path)
    relative_path = os.path.relpath(os.path.dirname(file_path), BASE_DIR)

    parent_id = get_or_create_folder_page(relative_path) if relative_path != "." else NOTION_ROOT_PAGE_ID

    # Read markdown content.
    try:
        if update_content:
            # For updates, use new_content if provided, else read file.
            if new_content is not None:
                md_content = new_content
            else:
                with open(file_path, "r", encoding="utf-8") as f:
                    md_content = f.read()
        else:
            # For phase 1 (creation), we can use the file content but upload minimal blocks.
            with open(file_path, "r", encoding="utf-8") as f:
                md_content = f.read()
    except Exception as e:
        print(f"{RED}Error reading {file_path}: {e}{RESET}")
        return ("failed", None)

    # Generate blocks.
    if update_content:
        blocks = md_to_notion_blocks(md_content, base_path=base_path)
    else:
        # Minimal content (an empty paragraph) for initial creation.
        blocks = [{
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": ""}}]
            }
        }]

    if not blocks:
        print(f"{YELLOW}Warning: No content to upload for {file_name}{RESET}")
        return ("skipped", None)

    # Check if the page already exists.
    existing_page_id = search_existing_page(file_name, parent_id)

    if existing_page_id:
        if update_content:
            existing_blocks = get_existing_page_content(existing_page_id)

            if not content_has_changed(existing_blocks, blocks):
                print(f"Page '{file_name}' is already up to date. Skipping update.")
                return ("skipped", existing_page_id)
            print(f"{YELLOW}Page '{file_name}' content has changed. Updating...{RESET}")
            delete_existing_content(existing_page_id)
            status = upload_blocks_to_notion(existing_page_id, blocks)

            if status == "failed":
                return ("failed", existing_page_id)
            return ("updated", existing_page_id)
        else:
            # If not updating content (phase 1), do nothing if the page exists.
            return ("skipped", existing_page_id)
    else:
        # Create a new page.
        print(f"{GREEN}Creating new Notion page: {file_name}{RESET}")
        response = session.post(
            "https://api.notion.com/v1/pages",
            json={
                "parent": {"page_id": parent_id},
                "properties": {"title": {"title": [{"text": {"content": file_name}}]}},
            },
            headers=HEADERS,
        )

        if response.status_code == 200:
            new_page_id = response.json().get("id")
            upload_blocks_to_notion(new_page_id, blocks)
            return ("created", new_page_id)
        else:
            print(f"{RED}Failed to create Notion page: {file_name} | Error: {response.status_code} - {response.text}{RESET}")
            return ("failed", None)