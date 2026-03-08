#!/usr/bin/env python3
"""
Script xử lý danh sách domain:
- Tải nội dung từ list.txt -> download.txt
- Loại trùng, nhóm theo root domain (# [root domain])
- Tách IP (# [IP List]), single-root (# [1 time domain]), cut-of-slash (# [cut of /])
- New domains ở đầu (# [New Domain])
- Bỏ qua dòng bắt đầu bằng / hoặc ~
- Bỏ phần sau ^, /, ,, #, $
- Bỏ qua domain có "##" trong dòng
- Lưu kết quả vào final.txt
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import urllib.request

BASE_DIR = Path(__file__).resolve().parent
LIST_PATH = BASE_DIR / "list.txt"
DOWNLOAD_PATH = BASE_DIR / "download.txt"
FINAL_PATH = BASE_DIR / "final.txt"

MULTI_VN_SUFFIXES = {
    "com.vn", "net.vn", "gov.vn", "edu.vn", "org.vn",
    "biz.vn", "name.vn", "pro.vn", "int.vn", "ac.vn",
    "health.vn", "info.vn",
}

IPV4_RE = re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")


def is_valid_ipv4(s: str) -> bool:
    """Kiểm tra chuỗi có phải IPv4 hợp lệ không."""
    if not IPV4_RE.match(s):
        return False
    try:
        return all(0 <= int(x) <= 255 for x in s.split("."))
    except ValueError:
        return False


def get_root(domain: str) -> str:
    """Lấy root domain (tên miền cấp 1)."""
    domain = domain.strip()
    if not domain or domain.startswith("#"):
        return domain
    # Bỏ wildcard ở đầu
    s = domain.lstrip("*.")
    if not s:
        return domain
    parts = s.split(".")
    if len(parts) < 2:
        return domain
    suffix2 = parts[-2] + "." + parts[-1]
    if len(parts) >= 3 and suffix2 in MULTI_VN_SUFFIXES:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def download_all_sources(list_path: Path) -> str:
    """Tải toàn bộ nội dung từ các URL trong list.txt, ghép vào download.txt."""
    if not list_path.is_file():
        raise SystemExit(f"Không tìm thấy {list_path}")

    contents: list[str] = []
    with list_path.open(encoding="utf-8") as f:
        for line in f:
            url = line.strip()
            if not url:
                continue
            print(f"Tải: {url}")
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                raw = resp.read()
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                text = raw.decode("latin-1")
            contents.append(text.rstrip("\n\r"))

    return "\n".join(contents)


def parse_line(line: str) -> tuple[str | None, str | None]:
    """
    Parse một dòng, trả về (normalized_entry, category).
    category: "normal" | "ip" | "cut_slash" | None (bỏ qua)
    """
    # Nếu dòng có "##" thì bỏ qua domain này, không cho vào final.txt
    if "##" in line:
        return None, None

    s = line.strip()
    if not s or s.startswith("#"):
        return None, None

    # Bỏ qua dòng bắt đầu bằng / hoặc ~
    if s.startswith("/") or s.startswith("~"):
        return None, None

    # Adblock: @@, || hoặc |
    if s.startswith("@@"):
        s = s[2:]
    if s.startswith("||"):
        s = s[2:]
    elif s.startswith("|"):
        s = s[1:]

    # Bỏ phần phía sau ^, /, ,, #, $ (lấy vị trí sớm nhất)
    cut_markers = ["^", "/", ",", "#", "$"]
    min_pos = len(s)
    cut_at_slash = False
    for m in cut_markers:
        i = s.find(m)
        if i != -1 and i < min_pos:
            min_pos = i
            cut_at_slash = (m == "/")
    if min_pos < len(s):
        s = s[:min_pos]
    s = s.strip().rstrip("|")

    if not s:
        return None, None

    # Bỏ dấu chấm đầu
    if s.startswith("."):
        s = s[1:]

    # Nếu đã cắt tại / -> cut of /: ||*.servimg.com/u/f45/... -> *.servimg.com
    if cut_at_slash and "." in s:
        return s, "cut_slash"

    # Kiểm tra IP
    if is_valid_ipv4(s):
        return s, "ip"

    # Hosts format: 0.0.0.0 domain
    parts = s.split()
    if len(parts) >= 2:
        try:
            if parts[0].replace(".", "").isdigit() and is_valid_ipv4(parts[0]):
                host = parts[1].strip()
                if host and "." in host:
                    if is_valid_ipv4(host):
                        return host, "ip"
                    return host, "normal"
        except (ValueError, IndexError):
            pass

    # Domain thuần
    if "." in s and " " not in s:
        if is_valid_ipv4(s):
            return s, "ip"
        return s, "normal"

    return None, None


def load_previous_domains(path: Path) -> set[str]:
    """Đọc tất cả domain từ final.txt cũ (để so sánh new domain)."""
    if not path.is_file():
        return set()
    seen: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        seen.add(s)
    return seen


def main() -> None:
    # 1. Tải và ghi vào download.txt
    print("Đang tải các nguồn từ list.txt ...")
    merged_text = download_all_sources(LIST_PATH)
    DOWNLOAD_PATH.write_text(merged_text + "\n", encoding="utf-8")
    print(f"Đã ghi nội dung vào {DOWNLOAD_PATH}")

    # 2. Parse và phân loại (loại trùng)
    print("Đang phân tích và phân loại ...")
    normal_entries: dict[str, None] = {}
    ip_entries: dict[str, None] = {}
    cut_slash_entries: dict[str, None] = {}

    for line in merged_text.splitlines():
        entry, category = parse_line(line)
        if entry is None:
            continue
        if category == "ip":
            ip_entries[entry] = None
        elif category == "cut_slash":
            cut_slash_entries[entry] = None
        elif category == "normal":
            normal_entries[entry] = None

    normal_list = list(normal_entries.keys())
    ip_list = sorted(ip_entries.keys())
    cut_slash_list = sorted(cut_slash_entries.keys())

    # 3. So sánh với final.txt cũ -> tìm new domains
    previous = load_previous_domains(FINAL_PATH)
    new_domains = sorted(d for d in normal_list if d not in previous)

    # 4. Nhóm normal theo root (trừ new domains)
    rest_normal = [d for d in normal_list if d in previous]
    groups: dict[str, list[str]] = {}
    for d in rest_normal:
        root = get_root(d)
        groups.setdefault(root, []).append(d)

    multi_roots = sorted(r for r, ds in groups.items() if len(ds) > 1)
    single_domains: list[str] = []
    for root, ds in groups.items():
        if len(ds) == 1:
            single_domains.append(ds[0])

    # 5. Xây dựng output
    out_lines: list[str] = []

    # 5a. New domains ở đầu
    if new_domains:
        out_lines.append("# [New Domain]")
        for d in new_domains:
            out_lines.append(d)
        out_lines.append("")

    # 5b. Các root có >= 2 domain
    for root in multi_roots:
        out_lines.append(f"# [{root}]")
        for d in sorted(groups[root]):
            out_lines.append(d)

    # 5c. Cut of /
    if cut_slash_list:
        if out_lines:
            out_lines.append("")
        out_lines.append("# [cut of /]")
        for d in cut_slash_list:
            out_lines.append(d)

    # 5d. Single root (1 time domain)
    if single_domains:
        if out_lines:
            out_lines.append("")
        out_lines.append("# [1 time domain]")
        for d in sorted(single_domains):
            out_lines.append(d)

    # 5e. IP List
    if ip_list:
        if out_lines:
            out_lines.append("")
        out_lines.append("# [IP List]")
        for d in ip_list:
            out_lines.append(d)

    # 6. Ghi final.txt
    FINAL_PATH.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    print(f"Hoàn tất. Kết quả lưu tại {FINAL_PATH}")
    print(f"  - New domains: {len(new_domains)}")
    print(f"  - Root groups: {len(multi_roots)}")
    print(f"  - Cut of /: {len(cut_slash_list)}")
    print(f"  - 1 time domain: {len(single_domains)}")
    print(f"  - IP: {len(ip_list)}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(1)
