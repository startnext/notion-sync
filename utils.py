import os

def find_md_files(base_dir):
    """Find all Markdown files recursively."""
    md_files = []
    for root, _, files in os.walk(base_dir):
        for file in files:
            if file.endswith(".md"):
                md_files.append(os.path.join(root, file))
    return md_files