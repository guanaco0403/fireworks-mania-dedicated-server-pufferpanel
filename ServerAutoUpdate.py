import argparse
import os
import sys
import zipfile

try:
    import requests
except ImportError:
    os.system(f"{sys.executable} -m pip install requests PyGithub")
    import requests

try:
    from github import Github, Auth, BadCredentialsException, UnknownObjectException
except ImportError:
    os.system(f"{sys.executable} -m pip install PyGithub")
    from github import Github, Auth, BadCredentialsException, UnknownObjectException

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

def download_asset(asset, target_path, github_token=None):
    asset_name = os.path.basename(target_path)
    print_info(f"Downloading asset: {asset_name}...")
    headers = {
        'Accept': 'application/octet-stream'
    }
    if github_token and github_token.strip() and github_token.strip().lower() != "none":
        headers['Authorization'] = f'token {github_token.strip()}'

    part_path = f"{target_path}.part"

    def _stream_download(url, req_headers):
        try:
            with requests.get(url, headers=req_headers, stream=True, timeout=60) as resp:
                if resp.status_code == 200:
                    total_size = int(resp.headers.get('content-length', 0))
                    downloaded = 0
                    last_pct = -1
                    with open(part_path, 'wb') as file:
                        for chunk in resp.iter_content(chunk_size=1024 * 1024):
                            if chunk:
                                file.write(chunk)
                                downloaded += len(chunk)
                                if total_size > 0:
                                    pct = int((downloaded / total_size) * 100)
                                    if pct % 10 == 0 and pct != last_pct:
                                        last_pct = pct
                                        mb_dl = downloaded // (1024 * 1024)
                                        mb_tot = total_size // (1024 * 1024)
                                        print_info(f"Download progress: {pct}% ({mb_dl}MB / {mb_tot}MB)")
                    return True
                return resp
        except Exception as e:
            return e

    try:
        # Try authenticated / asset.url first
        res = _stream_download(asset.url, headers)
        if res is True:
            if os.path.exists(target_path):
                os.remove(target_path)
            os.rename(part_path, target_path)
            print_success(f"Successfully downloaded {asset_name}")
            return True

        status_code = getattr(res, 'status_code', None)
        if status_code in (401, 403, 404):
            # Try fallback URL without token
            fallback_url = getattr(asset, 'browser_download_url', None) or asset.url
            print_warn(f"Download returned HTTP {status_code}. Retrying via fallback URL without token...")
            res_retry = _stream_download(fallback_url, {'Accept': 'application/octet-stream'})
            if res_retry is True:
                if os.path.exists(target_path):
                    os.remove(target_path)
                os.rename(part_path, target_path)
                print_success(f"Successfully downloaded {asset_name} (fallback)")
                return True

        if os.path.exists(part_path):
            os.remove(part_path)

        if hasattr(res, 'status_code'):
            print_error(f"Failed to download asset (HTTP {res.status_code}): {getattr(res, 'text', '')}")
        else:
            print_error(f"Download failed: {res}")

        if not github_token and status_code in (401, 403, 404):
            print_warn("Notice: If this repository asset is private or rate-limited, please specify a valid GitHub Token in PufferPanel settings.")
        return False
    except Exception as e:
        if os.path.exists(part_path):
            os.remove(part_path)
        print_error(f"Download exception: {e}")
        return False

def extract_zip(file_path, extract_path):
    print_info(f"Extracting archive '{os.path.basename(file_path)}'...")
    try:
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            zip_ref.extractall(extract_path)
            print_success(f"Extracted files to: {extract_path}")

        # Ensure server binary has execute permissions
        binary_path = os.path.join(extract_path, "FireworksManiaDedicatedLinux.x86_64")
        if os.path.exists(binary_path):
            try:
                os.chmod(binary_path, 0o755)
            except Exception:
                pass
        return True
    except Exception as e:
        print_error(f"Failed to extract archive: {e}")
        return False

def main(github_token=None, github_repo=None, server_version=None, force=False):
    token = github_token.strip() if github_token and github_token.strip() and github_token.strip().lower() != "none" else None
    repo_target = github_repo.strip() if github_repo and github_repo.strip() else 'Laumania/FireworksMania.DedicatedServer'
    version_target = server_version.strip() if server_version and server_version.strip() else 'latest'

    print_info(f"Target Repository: {repo_target}")
    print_info(f"Target Version: {version_target}")
    if force:
        print_info("Install/Force mode enabled: bypassing .installed_version check and forcing download & overwrite.")

    g = None
    repo = None

    if token:
        print_info(f"Using GitHub Token: {token[:4]}...{token[-4:]}")
        try:
            g = Github(auth=Auth.Token(token))
            repo = g.get_repo(repo_target)
            print_success(f"Accessed repository: {repo.full_name} (Authenticated)")
        except BadCredentialsException:
            print_warn("Provided GitHub Token is invalid or expired. Retrying unauthenticated...")
            token = None
            g = Github()
        except Exception as e:
            print_warn(f"Authenticated access failed ({e}). Retrying unauthenticated...")
            g = Github()

    if not repo:
        if not token:
            print_info("No GitHub token provided. Using unauthenticated API access...")
            g = Github()
        try:
            repo = g.get_repo(repo_target)
            print_success(f"Accessed repository: {repo.full_name}")
        except UnknownObjectException:
            print_error(f"Repository '{repo_target}' not found (404).")
            if not token:
                print_warn("If this repository is private, a valid GitHub Personal Access Token is required in PufferPanel settings.")
            return False
        except Exception as e:
            print_error(f"Error accessing repository '{repo_target}': {e}")
            if not token:
                print_warn("If this repository is private or rate-limited, please provide a valid GitHub Personal Access Token in PufferPanel settings.")
            return False

    # Fetch targeted release
    target_release = None
    if version_target.lower() == 'latest':
        try:
            target_release = repo.get_latest_release()
            print_info(f"Fetched latest release: {target_release.tag_name}")
        except Exception as e:
            print_warn(f"Could not fetch latest release directly ({e}). Iterating releases...")
            try:
                releases = repo.get_releases()
                if releases.totalCount > 0:
                    target_release = releases[0]
            except Exception as e_rel:
                print_error(f"Error fetching releases: {e_rel}")
                return False
    else:
        print_info(f"Searching for release tag/version '{version_target}'...")
        try:
            target_release = repo.get_release(version_target)
            print_info(f"Found release for tag '{version_target}': {target_release.title or target_release.tag_name}")
        except Exception:
            # Fallback search by tag_name or title in all releases
            try:
                releases = repo.get_releases()
                for r in releases:
                    if r.tag_name == version_target or r.title == version_target or r.tag_name == f"v{version_target}":
                        target_release = r
                        print_info(f"Matched release: {r.tag_name}")
                        break
            except Exception as e_rel:
                print_error(f"Error searching releases: {e_rel}")
                return False

    if not target_release:
        print_error(f"Could not find release matching version '{version_target}' in {repo_target}.")
        if not token:
            print_warn("Notice: If this version or repository requires authentication, please specify a GitHub Token in PufferPanel settings.")
        return False

    base_dir = os.path.dirname(os.path.abspath(__file__))
    version_file = os.path.join(base_dir, ".installed_version")
    binary_path = os.path.join(base_dir, "FireworksManiaDedicatedLinux.x86_64")

    # Find Linux asset in release
    for asset in target_release.get_assets():
        if 'Linux' in asset.name and asset.name.endswith('.zip'):
            print_info(f"Found target release asset: {asset.name}")

            version_marker = f"{repo_target}:{target_release.tag_name}:{asset.name}"

            # Check if this version is already installed locally (only if not forcing)
            if not force and os.path.exists(version_file) and os.path.exists(binary_path):
                try:
                    with open(version_file, "r") as f:
                        installed_marker = f.read().strip()
                    if installed_marker == version_marker:
                        print_success(f"Server is already up-to-date ({target_release.tag_name}). Skipping download.")
                        return True
                except Exception:
                    pass

            if force:
                print_info(f"Install/Force mode: downloading and overwriting server release '{target_release.tag_name}'...")
            else:
                print_info(f"Downloading and installing server release '{target_release.tag_name}'...")

            archive_path = os.path.join(base_dir, asset.name)
            if download_asset(asset, archive_path, token):
                if extract_zip(archive_path, base_dir):
                    # Clean up downloaded zip archive to save disk space
                    try:
                        if os.path.exists(archive_path):
                            os.remove(archive_path)
                    except Exception:
                        pass

                    # Save version marker
                    try:
                        with open(version_file, "w") as f:
                            f.write(version_marker)
                    except Exception as e:
                        print_warn(f"Notice: Failed to write {version_file}: {e}")

                    print(f"{CLR_GREEN}================================================={CLR_RESET}")
                    print(f"  {CLR_CYAN}{CLR_BOLD}Fireworks Mania Server Successfully Installed / Updated{CLR_RESET}")
                    print(f"{CLR_GREEN}================================================={CLR_RESET}")
                    return True
                return False
            return False

    print_error(f"No matching Linux server asset (.zip) found in release '{target_release.tag_name}'.")
    return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Download and update Dedicated Server from GitHub')
    parser.add_argument('positional_token', type=str, nargs='?', default='', help='GitHub token (optional positional argument)')
    parser.add_argument('--token', type=str, default='', help='Your GitHub access token')
    parser.add_argument('--repo', type=str, default='Laumania/FireworksMania.DedicatedServer', help='GitHub repository (owner/repo)')
    parser.add_argument('--version', type=str, default='latest', help='Server release version or tag name (e.g. latest or v1.2.0)')
    parser.add_argument('--force', '--install', action='store_true', dest='force', help='Force download and overwrite existing files, ignoring .installed_version')

    args = parser.parse_args()

    token = args.token if args.token else args.positional_token
    if token and (token.startswith("${") and token.endswith("}")):
        token = ""

    repo = args.repo
    if repo and (repo.startswith("${") and repo.endswith("}")):
        repo = "Laumania/FireworksMania.DedicatedServer"

    version = args.version
    if version and (version.startswith("${") and version.endswith("}")):
        version = "latest"

    success = main(github_token=token, github_repo=repo, server_version=version, force=args.force)
    sys.exit(0 if success else 1)
