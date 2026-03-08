from pathlib import Path

RAW_PATH = Path("raw/vnbadsite")
VNADS_PATH = Path("vnads.txt")

# Các hậu tố .vn nhiều cấp để xác định root domain
MULTI_VN_SUFFIXES = {
    "com.vn", "net.vn", "gov.vn", "edu.vn", "org.vn",
    "biz.vn", "name.vn", "pro.vn", "int.vn", "ac.vn",
    "health.vn", "info.vn"
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


def extract_domain_from_filter(line: str) -> str | None:
    """
    Lấy ra domain thuần từ một dòng filter dạng Adblock trong vnads.txt.
    Ví dụ:
      '||api.subiz.com.vn^' -> 'api.subiz.com.vn'
      '@@||example.com^$third-party' -> 'example.com'
    Bỏ qua dòng có wildcard (*), không có '||', v.v.
    """
    s = line.strip()
    if not s or s.startswith("#"):
        return None

    # Bỏ tiền tố allowlist '@@' nếu có
    if s.startswith("@@"):
        s = s[2:]

    if not s.startswith("||"):
        return None

    s = s[2:]  # bỏ '||'

    # Cắt tại '^' hoặc '/' (nếu có path)
    end_positions = [pos for pos in (s.find("^"), s.find("/")) if pos != -1]
    if end_positions:
        end = min(end_positions)
        host = s[:end]
    else:
        host = s

    host = host.strip()
    if not host:
        return None

    # Bỏ dấu chấm đầu nếu có (ví dụ .example.com)
    if host.startswith("."):
        host = host[1:]

    # Bỏ qua wildcard
    if "*" in host:
        return None

    # Phải có ít nhất 1 dấu chấm để coi là domain
    if "." not in host:
        return None

    return host


def load_vnads_mapping(path: Path) -> dict[str, str]:
    """
    Trả về mapping: domain -> dòng filter đầy đủ trong vnads.txt
    (Nếu trùng domain nhiều dòng, dòng sau cùng sẽ ghi đè dòng trước).
    """
    mapping: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        domain = extract_domain_from_filter(raw_line)
        if domain:
            mapping[domain] = raw_line.rstrip("\n\r")
    return mapping


def load_raw_domains(path: Path) -> list[str]:
    """
    Lấy danh sách domain từ raw/vnbadsite (bỏ qua dòng comment '#' và dòng trống),
    theo đúng thứ tự xuất hiện.
    """
    domains: list[str] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        s = raw_line.strip()
        if not s or s.startswith("#"):
            continue
        domains.append(s)
    return domains


def main() -> None:
    if not RAW_PATH.is_file():
        raise SystemExit(f"Không tìm thấy file {RAW_PATH}")
    if not VNADS_PATH.is_file():
        raise SystemExit(f"Không tìm thấy file {VNADS_PATH}")

    # 1. Tải mapping từ vnads.txt
    vnads_map = load_vnads_mapping(VNADS_PATH)

    # 2. Tải danh sách domain từ raw/vnbadsite (bỏ comment)
    raw_domains = load_raw_domains(RAW_PATH)

    matched: list[str] = []  # domain có trong vnads
    missing: list[str] = []  # domain không có trong vnads

    for d in raw_domains:
        if d in vnads_map:
            matched.append(d)
        else:
            missing.append(d)

    # 3. Xây lại nội dung file raw/vnbadsite
    out_lines: list[str] = []

    # 3a. Phần tên miền trùng (định dạng giống vnads.txt, có nhóm root)
    prev_root: str | None = None
    for d in matched:
        root = get_root(d)
        if root != prev_root:
            out_lines.append(f"# {root}")
            prev_root = root
        # Dòng filter lấy từ vnads.txt, ví dụ: ||domain.tld^
        out_lines.append(vnads_map[d])

    # 3b. Phần thiếu trong vnads (chuyển xuống cuối, thêm # vnads missing)
    if missing:
        if out_lines:
            out_lines.append("")  # ngăn cách một dòng trống
        out_lines.append("# vnads missing")
        out_lines.extend(missing)

    # 4. Ghi đè lại file raw/vnbadsite
    RAW_PATH.write_text("\n".join(out_lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()