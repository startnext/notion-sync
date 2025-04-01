import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Retrieve Notion API credentials from environment variables
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_ROOT_PAGE_ID = os.getenv("NOTION_ROOT_PAGE_ID")

# Dropbox Credentials
DROPBOX_REFRESH_TOKEN = os.getenv("DROPBOX_REFRESH_TOKEN")
DROPBOX_APP_KEY = os.getenv("DROPBOX_APP_KEY")
DROPBOX_APP_SECRET = os.getenv("DROPBOX_APP_SECRET")
DROPBOX_UPLOAD_URL = "https://content.dropboxapi.com/2/files/upload"
DROPBOX_SHARE_URL = "https://api.dropboxapi.com/2/sharing/create_shared_link_with_settings"
DROPBOX_LIST_SHARED_LINKS_URL = "https://api.dropboxapi.com/2/sharing/list_shared_links"
DROPBOX_METADATA_URL = "https://api.dropboxapi.com/2/files/get_metadata"

# Headers for Notion API requests
HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

# Directory for documentation
BASE_DIR = "docs"

# Notion API constraints
BLOCK_LIMIT = 100
MAX_BLOCK_TEXT_LENGTH = 2000

# Supported programming languages for syntax highlighting
SUPPORTED_LANGUAGES = {
    "abap", "agda", "arduino", "bash", "c", "c#", "c++", "clojure", "coffeescript", "css", "dart",
    "docker", "elixir", "elm", "erlang", "f#", "fortran", "gherkin", "go", "graphql", "haskell",
    "html", "java", "javascript", "json", "julia", "kotlin", "latex", "less", "lisp", "lua",
    "makefile", "markdown", "matlab", "mermaid", "nix", "objective-c", "ocaml", "pascal", "perl",
    "php", "plain text", "powershell", "prolog", "protobuf", "python", "r", "ruby", "rust",
    "sass", "scala", "scheme", "scss", "shell", "smalltalk", "sql", "swift", "toml", "typescript",
    "vb.net", "verilog", "vhdl", "xml", "yaml"
}

# ANSI color codes for terminal output
RED = "\033[91m"      # Red - errors
YELLOW = "\033[93m"   # Yellow - warnings
GREEN = "\033[32m"    # Green - success
BLUE = "\033[94m"     # Blue - information
RESET = "\033[0m"     # Reset to default color
