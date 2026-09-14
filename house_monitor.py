"""连江县天福元润国际房源监测器。

本程序只访问用户配置的、允许自动访问的公开检索页；不绕过登录、验证码、
反爬机制或网站服务条款。将检索结果页 URL 粘贴到界面后即可开始监测。
"""
from __future__ import annotations

import html
import re
import sqlite3
import threading
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from tkinter import END, LEFT, RIGHT, BOTH, X, StringVar, Text, Tk
from tkinter import messagebox, ttk

APP_DIR = Path.home() / ".tianfu_yuanrun_monitor"
DB_PATH = APP_DIR / "monitor.db"
COMMUNITY = "天福元润国际"


@dataclass(frozen=True)
class Listing:
    title: str
    price_wan: float | None
    unit_price: int | None
    url: str
    source: str

    @property
    def key(self) -> str:
        return self.url or "%s|%s|%s" % (self.title, self.price_wan, self.unit_price)


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", value))).strip()


def number(value: str) -> float | None:
    match = re.search(r"\d+(?:\.\d+)?", value.replace(",", ""))
    return float(match.group()) if match else None


def parse_listings(page: str, source_url: str) -> list[Listing]:
    """Extract likely listings from common Chinese property-search page markup.

    This intentionally uses loose markup matching: portals differ greatly and users may
    save or point to an authorised search page. Only cards mentioning the community and
    building are retained.
    """
    cards = re.split(r"(?i)<(?:article|li|div)[^>]+(?:class|data-role)=[^>]*(?:list|house|item|card)[^>]*>", page)
    candidates = cards if len(cards) > 1 else re.split(r"(?i)</(?:article|li)>", page)
    found: dict[str, Listing] = {}
    for card in candidates:
        text = clean_text(card)
        if COMMUNITY not in text or not re.search(r"(?:4\s*(?:号|#)\s*楼|4栋)", text):
            continue
        title_match = re.search(r"(?i)<(?:h[1-6]|a)[^>]*>(.*?)</(?:h[1-6]|a)>", card, re.S)
        title = clean_text(title_match.group(1)) if title_match else text[:80]
        link_match = re.search(r'''(?i)href=["']([^"'#]+)''', card)
        link = link_match.group(1) if link_match else ""
        if link.startswith("/"):
            from urllib.parse import urljoin
            link = urljoin(source_url, link)
        total = re.search(r"(\d+(?:\.\d+)?)\s*(?:万|万元)", text)
        unit = re.search(r"(\d{3,6})\s*(?:元\s*/?\s*(?:㎡|平米)|元/㎡)", text)
        listing = Listing(title, float(total.group(1)) if total else None,
                          int(unit.group(1)) if unit else None, link, source_url)
        found[listing.key] = listing
    return list(found.values())


class Store:
    def __init__(self, path: Path = DB_PATH) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        # A fetch runs on a worker thread while the UI reads history on the main thread.
        self.connection = sqlite3.connect(path, check_same_thread=False)
        self.lock = threading.Lock()
        self.connection.execute("""CREATE TABLE IF NOT EXISTS listings (
            listing_key TEXT PRIMARY KEY, title TEXT NOT NULL, price_wan REAL,
            unit_price INTEGER, url TEXT, source TEXT, first_seen TEXT NOT NULL,
            last_seen TEXT NOT NULL)""")
        self.connection.commit()

    def save(self, listings: list[Listing]) -> tuple[int, list[Listing]]:
        now = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
        new = []
        with self.lock:
            for item in listings:
                present = self.connection.execute("SELECT 1 FROM listings WHERE listing_key=?", (item.key,)).fetchone()
                if not present:
                    new.append(item)
                self.connection.execute("""INSERT INTO listings VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(listing_key) DO UPDATE SET title=excluded.title, price_wan=excluded.price_wan,
                    unit_price=excluded.unit_price, url=excluded.url, source=excluded.source, last_seen=excluded.last_seen""",
                    (item.key, item.title, item.price_wan, item.unit_price, item.url, item.source, now, now))
            self.connection.commit()
        return len(new), new

    def recent(self) -> list[tuple]:
        with self.lock:
            return self.connection.execute("SELECT title, price_wan, unit_price, url, last_seen FROM listings ORDER BY last_seen DESC").fetchall()


def fetch(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; TianfuListingMonitor/1.0)"})
    with urllib.request.urlopen(request, timeout=20) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


class MonitorApp:
    def __init__(self, root: Tk) -> None:
        self.root, self.store, self.running = root, Store(), False
        root.title("天福元润国际 · 4号楼出售信息监测")
        root.geometry("940x590")
        self.url = StringVar()
        self.interval = StringVar(value="30")
        self.status = StringVar(value="请填写公开房源检索页 URL，然后点击立即检查。")
        form = ttk.Frame(root, padding=12); form.pack(fill=X)
        ttk.Label(form, text="检索页 URL：").pack(side=LEFT)
        ttk.Entry(form, textvariable=self.url, width=78).pack(side=LEFT, fill=X, expand=True)
        ttk.Label(form, text="  间隔(分钟)：").pack(side=LEFT)
        ttk.Spinbox(form, from_=5, to=1440, textvariable=self.interval, width=6).pack(side=LEFT)
        ttk.Button(form, text="立即检查", command=self.check_once).pack(side=RIGHT, padx=(8, 0))
        self.toggle = ttk.Button(form, text="开始监测", command=self.toggle_monitor); self.toggle.pack(side=RIGHT)
        ttk.Label(root, text="只显示同时包含“天福元润国际”和“4号楼/4栋”的房源。", padding=(12, 0)).pack(anchor="w")
        self.output = Text(root, height=9, state="disabled", wrap="word"); self.output.pack(fill=X, padx=12, pady=8)
        columns = ("title", "total", "unit", "seen", "url")
        self.table = ttk.Treeview(root, columns=columns, show="headings")
        for key, label, width in (("title", "标题", 260), ("total", "总价(万)", 85), ("unit", "单价(元/㎡)", 105), ("seen", "最后发现", 180), ("url", "链接", 280)):
            self.table.heading(key, text=label); self.table.column(key, width=width, anchor="w")
        self.table.pack(fill=BOTH, expand=True, padx=12)
        ttk.Label(root, textvariable=self.status, padding=12).pack(anchor="w")
        self.refresh_table()

    def log(self, text: str) -> None:
        self.output.configure(state="normal"); self.output.insert(END, text + "\n"); self.output.see(END); self.output.configure(state="disabled")

    def refresh_table(self) -> None:
        self.table.delete(*self.table.get_children())
        for title, total, unit, url, seen in self.store.recent():
            self.table.insert("", END, values=(title, "" if total is None else total, "" if unit is None else unit, seen, url))

    def check_once(self) -> None:
        url = self.url.get().strip()
        if not url.startswith(("http://", "https://")):
            messagebox.showwarning("需要 URL", "请输入以 http:// 或 https:// 开头、可公开访问的房源检索页 URL。")
            return
        self.status.set("正在获取房源页面…")
        threading.Thread(target=self._check, args=(url,), daemon=True).start()

    def _check(self, url: str) -> None:
        try:
            listings = parse_listings(fetch(url), url)
            count, new = self.store.save(listings)
            self.root.after(0, lambda: self._finished(len(listings), count, new))
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            self.root.after(0, lambda: self.status.set("检查失败：%s" % exc))

    def _finished(self, total: int, new_count: int, new: list[Listing]) -> None:
        self.refresh_table(); stamp = datetime.now().strftime("%F %T")
        self.status.set("%s：找到 %d 条，新增 %d 条。" % (stamp, total, new_count))
        self.log(self.status.get())
        if new_count:
            self.root.bell(); messagebox.showinfo("发现新房源", "发现 %d 条新的 4 号楼出售信息。" % new_count)

    def toggle_monitor(self) -> None:
        self.running = not self.running; self.toggle.configure(text="停止监测" if self.running else "开始监测")
        if self.running: self.schedule()

    def schedule(self) -> None:
        if not self.running: return
        self.check_once()
        try: delay = max(5, int(self.interval.get())) * 60_000
        except ValueError: delay = 30 * 60_000
        self.root.after(delay, self.schedule)


if __name__ == "__main__":
    app_root = Tk()
    MonitorApp(app_root)
    app_root.mainloop()
