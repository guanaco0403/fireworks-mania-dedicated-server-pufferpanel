import argparse
import requests
import os
import zipfile
from github import Github

# ANSI Color Codes
CLR_RESET = "\033[0m"
CLR_GREEN = "\033[32m"
CLR_CYAN = "\033[36m"
CLR_YELLOW = "\033[33m"
CLR_RED = "\033[31m"
CLR_BOLD = "\033[1m"

def print_info(msg):
    print(f"{CLR_CYAN}[INFO]{CLR_RESET} {msg}")

def print_success(msg):
    print(f"{CLR_GREEN}[SUCCESS]{CLR_RESET} {msg}")

def print_warn(msg):
    print(f"{CLR_YELLOW}[WARNING]{CLR_RESET} {msg}")

def print_error(msg):
    print(f"{CLR_RED}[ERROR]{CLR_RESET} {msg}")

print(".")
print(f"{CLR_GREEN}=========================================={CLR_RESET}")
print(f"  {CLR_CYAN}{CLR_BOLD}Fireworks Mania Auto Server Updater V2.0{CLR_RESET}")
print(f"               {CLR_CYAN}By Guanaco0403{CLR_RESET}")
print(f"{CLR_GREEN}=========================================={CLR_RESET}")

def download_asset(asset, asset_name, github_token=None):
    print_info(f"Downloading asset: {asset_name}...")
    headers = {
        'Accept': 'application/octet-stream'
    }
    if github_token and github_token.strip() and github_token.strip().lower() != "none":
        headers['Authorization'] = f'token {github_token.strip()}'

    try:
        response = requests.get(asset.url, headers=headers, stream=True)

        if response.status_code == 200:
            with open(asset_name, 'wb') as file:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        file.write(chunk)
            print_success(f"Successfully downloaded {asset_name}")
        else:
            print_error(f"Failed to download asset (HTTP {response.status_code}): {response.text}")
    except Exception as e:
        print_error(f"Download exception: {e}")

def extract_zip(file_path):
    print_info("Extracting archive...")
    try:
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            extract_path = os.path.dirname(os.path.abspath(__file__))
            zip_ref.extractall(extract_path)
            print_success(f"Extracted files to: {extract_path}")
    except Exception as e:
        print_error(f"Failed to extract archive: {e}")

def main(github_token=None):
    token = github_token.strip() if github_token and github_token.strip() and github_token.strip().lower() != "none" else None
    if token:
        print_info(f"Using GitHub Token: {token[:4]}...{token[-4:]}")
        g = Github(token)
    else:
        print_warn("No GitHub token provided. Using unauthenticated API access...")
        g = Github()

    repo_owner = 'Laumania'
    repo_name = 'FireworksMania.DedicatedServer'
    print_info(f"Target Repository: {repo_owner}/{repo_name}")

    try:
        repo = g.get_repo(f"{repo_owner}/{repo_name}")
        print_success(f"Accessed repository: {repo.full_name}")
    except Exception as e:
        print_error(f"Error accessing repository: {e}")
        return

    try:
        releases = repo.get_releases()
        print_info(f"Found {releases.totalCount} release(s)")
    except Exception as e:
        print_error(f"Error fetching releases: {e}")
        return

    if releases:
        for release in releases:
            for asset in release.get_assets():
                if 'Linux' in asset.name and asset.name.endswith('.zip'):
                    print_info(f"Found target release asset: {asset.name}")
                    download_asset(asset, asset.name, token)
                    extract_zip(asset.name)
                    print(f"{CLR_GREEN}================================================={CLR_RESET}")
                    print(f"  {CLR_CYAN}{CLR_BOLD}Fireworks Mania Server Successfully Installed{CLR_RESET}")
                    print(f"{CLR_GREEN}================================================={CLR_RESET}")
                    return
        print_error("No matching Linux server asset (.zip) found in releases.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Download and update Dedicated Server from GitHub')
    parser.add_argument('github_token', type=str, nargs='?', default='', help='Your GitHub access token')
    args = parser.parse_args()

    main(args.github_token)
