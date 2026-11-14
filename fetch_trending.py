#!/usr/bin/env python3
"""抓取 GitHub Trending(无官方 API,解析 HTML),零第三方依赖。

用法:
    python fetch_trending.py                # 今日趋势
    python fetch_trending.py weekly         # 每周趋势
    python fetch_trending.py monthly python # 按语言过滤
输出 JSON 到 stdout;--out 可写入文件。
"""
import json
import re
import ssl
import sys
import urllib.request
from argparse import ArgumentParser

BASE = "https://github.com/trending"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}


def get_ssl_context() -> ssl.SSLContext:
    # Windows 商店版 Python 常缺根证书:依次尝试 certifi、系统默认、跳过验证
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        pass
    try:
        ctx = ssl.create_default_context()
        import urllib.request as _u
        _u.urlopen("https://github.com", context=ctx, timeout=5).close()
        return ctx
    except Exception:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx


def fetch(period: str, language: str) -> str:
    url = BASE
    if language:
        url += "/" + language
    if period and period != "daily":
        url += "?since=" + period
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30, context=get_ssl_context()) as resp:
        return resp.read().decode("utf-8")


def parse(html: str) -> list:
    repos = []
    tag_re = re.compile(r'<a\s[^>]*href="(/[^"]+/stargazers)"', re.S)
    for row in html.split('<article class="Box-row">')[1:]:
        # 仓库全名:stargazers 链接所在条目的 h2 中第一个仓库链接
        m = re.search(r'<h2[^>]*>.*?<a\s[^>]*href="/([^"]+)"', row, re.S)
        if not m:
            continue
        full_name = m.group(1).rstrip("/")
        item = {"repo": full_name, "url": "https://github.com/" + full_name}
        d = re.search(r'<p class="col-9 color-fg-muted[^"]*">\s*(.*?)\s*</p>', row, re.S)
        if d:
            item["description"] = re.sub(r"<[^>]+>", "", d.group(1)).strip()
        s = tag_re.search(row)
        if s:
            # 星数数字跟在 stargazers 链接的 svg 之后
            m2 = re.search(re.escape(s.group(0)) + r'.*?</svg>\s*([\d,]+)', row, re.S)
            if m2:
                item["stars"] = int(m2.group(1).replace(",", ""))
        repos.append(item)
    return repos


def main() -> None:
    ap = ArgumentParser(description="抓取 GitHub Trending")
    ap.add_argument("period", nargs="?", choices=["daily", "weekly", "monthly"], default="daily")
    ap.add_argument("language", nargs="?", default="")
    ap.add_argument("--out", help="写入 JSON 文件而非 stdout")
    args = ap.parse_args()

    html = fetch(args.period, args.language)
    data = {"period": args.period, "language": args.language or "all", "repos": parse(html)}
    text = json.dumps(data, ensure_ascii=False, indent=2)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"已写入 {args.out}({len(data['repos'])} 个仓库)")
    else:
        print(text)


if __name__ == "__main__":
    main()
