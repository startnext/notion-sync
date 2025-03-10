import os
import requests
import json
from config import (
    DROPBOX_ACCESS_TOKEN,
    DROPBOX_UPLOAD_URL,
    DROPBOX_SHARE_URL,
    DROPBOX_LIST_SHARED_LINKS_URL,
    DROPBOX_METADATA_URL,
    RED,
    GREEN,
    YELLOW,
    RESET,
)

def check_if_file_exists(dropbox_path):
    """Checks if a file already exists in Dropbox."""
    headers = {
        "Authorization": f"Bearer {DROPBOX_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    data = json.dumps({"path": dropbox_path})

    response = requests.post(DROPBOX_METADATA_URL, headers=headers, data=data)

    return response.status_code == 200


def upload_image_to_dropbox(image_path):
    """Uploads an image to Dropbox and returns a direct raw link."""
    if not os.path.exists(image_path):
        print(f"{YELLOW}Image not found: {image_path}{RESET}")
        return None

    image_filename = os.path.basename(image_path)
    dropbox_path = f"/notion-images/{image_filename}"

    headers = {
        "Authorization": f"Bearer {DROPBOX_ACCESS_TOKEN}",
        "Dropbox-API-Arg": json.dumps({"path": dropbox_path, "mode": "overwrite"}),
        "Content-Type": "application/octet-stream"
    }

    if check_if_file_exists(dropbox_path):
        print(f"{YELLOW}Image already exists in Dropbox. Fetching existing link...{RESET}")
        return get_existing_or_new_dropbox_link(dropbox_path)

    with open(image_path, "rb") as image_file:
        response = requests.post(DROPBOX_UPLOAD_URL, headers=headers, data=image_file)

    if response.status_code == 200:
        print(f"{GREEN}Uploaded {image_filename} to Dropbox{RESET}")
        return get_existing_or_new_dropbox_link(dropbox_path)
    else:
        print(f"{RED}Failed to upload {image_filename}: Status Code {response.status_code}{RESET}")
        print(f"Response Content: {response.text}")
        return None

def get_existing_or_new_dropbox_link(file_path):
    """Retrieves an existing Dropbox shared link or creates a new one."""
    headers = {"Authorization": f"Bearer {DROPBOX_ACCESS_TOKEN}", "Content-Type": "application/json"}
    data = json.dumps({"path": file_path})

    #Check if a shared link already exists
    response = requests.post(DROPBOX_LIST_SHARED_LINKS_URL, headers=headers, data=data)

    if response.status_code == 200:
        links = response.json().get("links", [])
        if links:
            raw_link = convert_to_direct_link(links[0]["url"])
            print(f"{YELLOW}Found existing Dropbox link: {raw_link}{RESET}")
            return raw_link

    # If no link exists, create a new one
    return create_dropbox_shared_link(file_path)

def create_dropbox_shared_link(file_path):
    """Creates a new Dropbox shared link and converts it to a direct raw link."""
    headers = {"Authorization": f"Bearer {DROPBOX_ACCESS_TOKEN}", "Content-Type": "application/json"}
    data = json.dumps({"path": file_path, "settings": {"requested_visibility": "public"}})

    response = requests.post(DROPBOX_SHARE_URL, headers=headers, data=data)

    if response.status_code == 200:
        shared_url = response.json()["url"]
        raw_link = convert_to_direct_link(shared_url)
        print(f"{GREEN}Created new Dropbox link: {raw_link}{RESET}")
        return raw_link
    else:
        print(f"{RED}Failed to create shareable link: Status Code {response.status_code}{RESET}")
        print(f"Response Content: {response.text}")
        return None

def convert_to_direct_link(dropbox_link):
    """Converts Dropbox shareable link to a direct raw image link."""
    return dropbox_link.replace("www.dropbox.com", "dl.dropboxusercontent.com").replace("?dl=0", "")
