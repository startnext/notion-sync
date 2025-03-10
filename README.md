# Technical Documentation to Notion Sync

This project syncs Markdown (`.md`) files from a local directory to Notion, creating and updating pages accordingly.

## Features

- Recursively finds Markdown files.
- Converts Markdown syntax to Notion blocks.
- Creates or updates Notion pages based on file content.
- Maintains a directory structure as Notion pages.
- Automatically uploads images to Dropbox and replaces local paths with Dropbox links.
- Handles dynamic page links to other .md files in the same or other directories.

## Requirements

- Python 3.13+
- pip (Comes pre-installed with Python, but can be updated using `python -m ensurepip --default-pip`)
- Notion API Token

## Installation

1. **Clone the repository**
   ```sh
   git clone git@gitlab.com:startnext/sre/notion-sync.git
   cd notion-sync
   ```

2. **Create and activate a virtual environment**
   ```sh
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. **Install dependencies**
   ```sh
   pip install -r requirements.txt
   ```

## Retrieving Notion Token, Page ID, Dropbox Access Token

1. **Create a Notion Integration**
    - Go to [Notion Integrations](https://www.notion.so/my-integrations) and create a new integration.
    - Select the workspace where you want to use the integration.
    - Copy the `Internal Integration Token` provided after creation.
    - This token should be set as `NOTION_TOKEN` in your `.env` file.

2. **Obtain the Notion Page ID**
    - Open the Notion page you want to use as the root for your Markdown sync.
    - Click on `Share` and then `Copy Link`.
    - The URL will be something like: `https://www.notion.so/PageName-19632a12f848273458356deccd685c23b`
    - The `19632a12f848273458356deccd685c23b` part is your `NOTION_ROOT_PAGE_ID`.
    - Ensure your integration has access to this page by connecting it.

3. **Obtain Dropbox API Access Token**
    - Create a dropbox app [DBX Platform for Developers](https://www.dropbox.com/developers)
        - Click **Create App**.
        - Choose an API (Select `Scoped access`).
        - Choose the type of access you need (Select `Full Dropbox`).
        - Name your app (e.g., `notion-image-uploader`).
    - Generate Dropbox API Access Token
        - Go to **Permission** and select `files.content.write` , `files.content.read`, `sharing.write`
        - Go to **OAuth 2 > Generate Access Token**.
        - Copy the generated token.

4. **Create and Update the `.env` File**
    - Copy the provided `.env.example` file and rename it to `.env`.
    - Open `.env` and add your Notion, Dropbox credentials:
      ```sh
      NOTION_TOKEN=<your_notion_api_token>
      NOTION_ROOT_PAGE_ID=<your_root_page_id>
      DROPBOX_ACCESS_TOKEN=<your_dropbox_access_token>
      ```
    - Save the file. The script will automatically load these credentials when executed.

## Usage

1. **Run the script to sync Markdown files to Notion**
   ```sh
   python main.py
   ```

3. The script will:
    - Detect `.md` files in the specified directory.
    - Convert them into Notion-compatible blocks.
    - Upload them as pages under the specified Notion root page.

## File Structure

```
notion_sync/
│── docs/                 # Directory containing Markdown files
│── config.py             # Configuration settings
│── main.py               # Main script to execute syncing
│── notion_api.py         # Handles Notion API requests
│── markdown_parser.py    # Converts Markdown to Notion blocks
│── image_uploader.py     # Handles image upload to Dropbox
│── utils.py              # Utility function
│── requirements.txt      # Dependencies
│── .env                  # Environment variables (not included in repo)
```

## Notes

- Ensure your Notion integration has permission to edit pages under the specified `NOTION_ROOT_PAGE_ID`.
- Ensure all the access tokens are valid.
- The script updates existing pages to prevent duplication.
- Nested directories are preserved as Notion subpages.

## Known Issues

- Sometimes, the script detects fake changes due to API retrieval limitations when comparing local and Notion page
  content.
- In some cases, list item child values might skip converting Markdown syntax to Notion blocks and instead be
  appended as is with Markdown syntax. However, the content will still be present.