from __future__ import annotations

import sys
from pathlib import Path

import urllib.request

BASE_DIR = Path(__file__).resolve().parent
LIST_PATH = BASE_DIR / "list.txt"
DOWNLOAD_PATH = BASE_DIR / "download.txt"
FINAL_PATH = BASE_DIR / "final.txt"

# Các hậu tố .vn nhiều cấp để xác định root domain
MULTI_VN_SUFFIXES = {
    "com.vn", "net.vn", "gov.vn", "edu.vn", "org.vn",
    "biz.vn", "name.vn", "pro.vn", "int.vn", "ac.vn",
    "health.vn", "info.vn",
}


def get_root(domain: str) -> str:
    domain = domain.strip()
    if not domain or domain.startswith("#"):
        return domain
    parts = domain.split(".")
    if len(parts) < 2:
        return domain
    suffix2 = parts[-2] + "." + parts[-1]
    if len(parts) >= 3 and suffix2 in MULTI_VN_SUFFIXES:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def download_all_sources(list_path: Path) -> str:
    """
    Đọc list.txt, tải toàn bộ nội dung các URL text,
    ghép lại thành một chuỗi lớn (ngăn cách bằng '\n').
    """
    if not list_path.is_file():
        raise SystemExit(f"Không tìm thấy {list_path}")

    contents: list[str] = []
    with list_path.open(encoding="utf-8") as f:
        for line in f:
            url = line.strip()
            if not url:
                continue
            print(f"Tải: {url}")
            with urllib.request.urlopen(url) as resp:
                raw = resp.read()
            # cố gắng decode utf-8, fallback latin-1 nếu lỗi
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                text = raw.decode("latin-1")
            contents.append(text.rstrip("\n\r"))

    return "\n".join(contents)


def normalize_line(line: str) -> str | None:
    """
    Chuẩn hóa mỗi dòng về dạng 'domain' (không protocol, không path),
    hoặc trả về None nếu không phải dòng domain hợp lệ.
    Hỗ trợ:
      - Dòng kiểu hosts: '0.0.0.0 example.com'
      - Dòng kiểu Adblock: '||example.com^'
      - Dòng chỉ có domain: 'example.com'
    """
    s = line.strip()
    if not s or s.startswith("#"):
        return None

    # Adblock '||domain^'
    if s.startswith("@@"):
        s = s[2:]
    if s.startswith("||"):
        s = s[2:]
        # cắt tại '^' hoặc '/'
        for sep in ("^", "/"):
            if sep in s:
                s = s.split(sep, 1)[0]
        s = s.strip()
        if s.startswith("."):
            s = s[1:]
        if not s or "*" in s or "." not in s:
            return None
        return s

    # hosts: '0.0.0.0 domain' hoặc '127.0.0.1 domain'
    parts = s.split()
    if len(parts) >= 2 and (
        parts[0].replace(".", "").isdigit()
        or parts[0] in {"0.0.0.0", "127.0.0.1"}
    ):
        host = parts[1].strip()
        if host and "." in host and "*" not in host:
            return host

    # Thuần domain trên một dòng
    if " " not in s and "." in s and "*" not in s:
        return s

    return None


def main() -> None:
    # 1. Tải và ghép nội dung theo list.txt -> download.txt
    print("Đang tải tất cả nguồn trong list.txt ...")
    merged_text = download_all_sources(LIST_PATH)
    DOWNLOAD_PATH.write_text(merged_text + "\n", encoding="utf-8")
    print(f"Đã ghi toàn bộ nội dung vào {DOWNLOAD_PATH}")

    # 2. Lọc ra domain, loại trùng lặp
    print("Đang phân tích domain và loại trùng ...")
    unique_domains: dict[str, None] = {}
    for line in merged_text.splitlines():
        d = normalize_line(line)
        if d:
            unique_domains.setdefault(d, None)

    domains = list(unique_domains.keys())

    # 3. Nhóm theo root domain
    print("Đang nhóm theo root domain ...")
    groups: dict[str, list[str]] = {}
    for d in domains:
        root = get_root(d)
        groups.setdefault(root, []).append(d)

    # Tách root xuất hiện nhiều lần và root xuất hiện 1 lần
    multi_roots = sorted(r for r, ds in groups.items() if len(ds) > 1)
    single_domains: list[str] = []
    for root, ds in groups.items():
        if len(ds) == 1:
            single_domains.extend(ds)

    out_lines: list[str] = []

    # 3a. Các root có từ 2 domain trở lên
    for root in multi_roots:
        out_lines.append(f"# [{root}]")
        for d in sorted(groups[root]):
            out_lines.append(d)

    # 3b. Các root chỉ xuất hiện 1 lần -> đưa xuống cuối
    if single_domains:
        if out_lines:
            out_lines.append("")  # ngăn cách một dòng trống
        out_lines.append("# [1 time domain]")
        for d in sorted(single_domains):
            out_lines.append(d)

    FINAL_PATH.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    print(f"Hoàn tất. Kết quả lưu tại {FINAL_PATH}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(1)