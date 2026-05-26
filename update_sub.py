#!/usr/bin/env python3
from pathlib import Path
import subprocess
import sys
import re
from datetime import datetime
from collections import deque

ROOT = Path("/home/ali/vps/programs/my_sub").resolve()

V2RAY_EXPORT_FILE = Path("/home/ali/vps/programs/v2ray_real_test/data/export.txt")

PROXY_FILES = [
    Path("/home/ali/vps/programs/proxy_scanner/working_proxies.txt"),
    Path("/home/ali/vps/programs/proxy_scannerbackup/working_proxies.txt"),
    Path("/home/ali/vps/programs/proxy_scannerbackupbackup/working_proxies.txt"),
]

OUTPUT_FILE = ROOT / "sub.txt"

LAST_LINES_FROM_V2RAY_EXPORT = 100

PROXY_URL_PATTERN = re.compile(r'(https?://\S+|socks://\S+)', re.IGNORECASE)


def run_command(command, check=True):
    return subprocess.run(
        command,
        cwd=ROOT,
        check=check,
        text=True,
        capture_output=True
    )


def get_current_branch():
    try:
        result = run_command(["git", "branch", "--show-current"])
        branch = result.stdout.strip()
        if branch:
            return branch
    except Exception:
        pass

    return "main"


def get_duplicate_key(line):
    return line.split("#", 1)[0].strip()


def read_last_lines(path, count):
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        return list(deque(f, maxlen=count))


def read_v2ray_export_last_lines(path, last_lines):
    stats = {
        "file": path,
        "exists": False,
        "used_lines": 0,
    }

    print(f"Checking V2Ray export file: {path}")

    if not path.exists():
        print(f"File not found: {path}")
        return [], stats

    lines = read_last_lines(path, last_lines)
    lines = [line.strip() for line in lines]

    stats["exists"] = True
    stats["used_lines"] = len(lines)

    print(f"Loaded {len(lines)} lines from V2Ray export file.")
    return lines, stats


def extract_proxy_configs_from_file(path):
    stats = {
        "file": path,
        "exists": False,
        "total_lines": 0,
        "matched_lines": 0,
        "extracted_configs": 0,
    }

    print(f"Checking proxy file: {path}")

    if not path.exists():
        print(f"File not found: {path}")
        return [], stats

    configs = []

    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for raw_line in f:
            stats["total_lines"] += 1

            line = raw_line.strip()
            if not line:
                continue

            match = PROXY_URL_PATTERN.search(line)
            if match:
                value = match.group(1).strip()
                configs.append(value)
                stats["matched_lines"] += 1

    stats["exists"] = True
    stats["extracted_configs"] = len(configs)

    print(
        f"Processed proxy file: {path} | "
        f"total_lines={stats['total_lines']} | "
        f"matched_lines={stats['matched_lines']} | "
        f"extracted_configs={stats['extracted_configs']}"
    )

    return configs, stats


def clean_configs(lines):
    seen = set()
    result = []

    total_lines = 0
    empty_lines = 0
    duplicate_lines = 0

    for raw_line in lines:
        total_lines += 1
        line = raw_line.strip()

        if not line:
            empty_lines += 1
            continue

        key = get_duplicate_key(line)

        if not key:
            empty_lines += 1
            continue

        if key in seen:
            duplicate_lines += 1
            continue

        seen.add(key)
        result.append(line)

    stats = {
        "total_lines": total_lines,
        "empty_lines": empty_lines,
        "duplicate_lines": duplicate_lines,
        "final_lines": len(result),
    }

    output = "\n".join(result)
    if output:
        output += "\n"

    return output, stats


def write_if_changed(path, data):
    if path.exists() and path.read_bytes() == data:
        return False

    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_bytes(data)
    temp_path.replace(path)
    return True


def git_has_staged_changes():
    result = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        cwd=ROOT
    )
    return result.returncode != 0


def git_pull_rebase(branch):
    return run_command([
        "git",
        "-c",
        "http.sslVerify=false",
        "pull",
        "--rebase",
        "origin",
        branch
    ])


def main():
    if not (ROOT / ".git").exists():
        print(f"ERROR: Git repository not found in: {ROOT}", file=sys.stderr)
        return 1

    all_configs = []

    v2ray_configs, v2ray_stats = read_v2ray_export_last_lines(
        V2RAY_EXPORT_FILE,
        LAST_LINES_FROM_V2RAY_EXPORT
    )
    all_configs.extend(v2ray_configs)

    proxy_stats_list = []
    for proxy_file in PROXY_FILES:
        proxy_configs, proxy_stats = extract_proxy_configs_from_file(proxy_file)
        all_configs.extend(proxy_configs)
        proxy_stats_list.append(proxy_stats)

    cleaned_text, stats = clean_configs(all_configs)

    print("=" * 60)
    print(f"Run time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Repository root: {ROOT}")
    print(f"Output file: {OUTPUT_FILE}")
    print("=" * 60)
    print()

    print("V2Ray export file:")
    if v2ray_stats["exists"]:
        print(f"- {v2ray_stats['file']}")
        print(f"  Last lines used: {v2ray_stats['used_lines']}")
    else:
        print(f"- {v2ray_stats['file']} | NOT FOUND")

    print()
    print("Proxy files:")

    existing_proxy_files = 0
    missing_proxy_files = 0

    for item in proxy_stats_list:
        if item["exists"]:
            existing_proxy_files += 1
            print(f"- {item['file']}")
            print(f"  Total lines: {item['total_lines']}")
            print(f"  Matched lines: {item['matched_lines']}")
            print(f"  Extracted configs: {item['extracted_configs']}")
        else:
            missing_proxy_files += 1
            print(f"- {item['file']} | NOT FOUND")

    print()
    print("Summary:")
    print(f"Existing proxy files: {existing_proxy_files}")
    print(f"Missing proxy files: {missing_proxy_files}")
    print(f"Total raw configs before cleaning: {stats['total_lines']}")
    print(f"Empty lines: {stats['empty_lines']}")
    print(f"Duplicate configs: {stats['duplicate_lines']}")
    print(f"Final configs: {stats['final_lines']}")
    print()

    if not cleaned_text.strip():
        print("ERROR: No configs found after cleaning.", file=sys.stderr)
        return 1

    output_data = cleaned_text.encode("utf-8")
    changed = write_if_changed(OUTPUT_FILE, output_data)

    if not changed:
        print("No effective changes detected in sub.txt.")
        return 0

    branch = get_current_branch()
    print(f"Current branch: {branch}")

    run_command(["git", "add", "sub.txt"])

    if not git_has_staged_changes():
        print("Nothing to commit.")
        return 0

    commit_message = f"update sub {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

    try:
        commit_result = run_command(["git", "commit", "-m", commit_message])
        if commit_result.stdout:
            print(commit_result.stdout.strip())
        if commit_result.stderr:
            print(commit_result.stderr.strip())
    except subprocess.CalledProcessError as e:
        print("ERROR: git commit failed.", file=sys.stderr)
        print(e.stdout or "", file=sys.stderr)
        print(e.stderr or "", file=sys.stderr)
        return 1

    try:
        print("Running git pull --rebase before push...")
        pull_result = git_pull_rebase(branch)
        if pull_result.stdout:
            print(pull_result.stdout.strip())
        if pull_result.stderr:
            print(pull_result.stderr.strip())
    except subprocess.CalledProcessError as e:
        print("ERROR: git pull --rebase failed.", file=sys.stderr)
        print(e.stdout or "", file=sys.stderr)
        print(e.stderr or "", file=sys.stderr)
        return 1

    try:
        push_result = run_command([
            "git",
            "-c",
            "http.sslVerify=false",
            "push",
            "origin",
            branch
        ])

        if push_result.stdout:
            print(push_result.stdout.strip())
        if push_result.stderr:
            print(push_result.stderr.strip())

    except subprocess.CalledProcessError as e:
        print("ERROR: git push failed.", file=sys.stderr)
        print(e.stdout or "", file=sys.stderr)
        print(e.stderr or "", file=sys.stderr)
        return 1

    print(f"Push completed successfully on branch: {branch}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
