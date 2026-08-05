import shutil
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse

from playwright.sync_api import sync_playwright


ROOT = Path("/Users/dielangli/Desktop/职场AI培训/WorkBuddyGuide_散装版")
SCREENSHOT_DIR = Path(__file__).resolve().parents[1] / "artifacts" / "local-opening-qa"
ISOLATED_ROOT = Path("/tmp/workbuddy-standalone-module-qa")


def open_local(page, path: Path) -> None:
    page.goto(path.as_uri(), wait_until="load")
    page.locator("h1").first.wait_for(state="visible")


class LocalResourceParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.resources: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "img" and values.get("src"):
            self.resources.append(values["src"])
        elif tag == "link" and values.get("rel") == "stylesheet" and values.get("href"):
            self.resources.append(values["href"])
        elif tag in {"video", "source"} and values.get("src"):
            self.resources.append(values["src"])


SCREENSHOT_DIR.mkdir(exist_ok=True)
errors: list[str] = []
failed_requests: list[str] = []

# Simulate sending exactly one visible module folder to another computer.
# Hidden .routes entries are intentionally excluded: a recipient will not have
# their symlink targets, and the local entry must not rely on them.
if ISOLATED_ROOT.exists():
    shutil.rmtree(ISOLATED_ROOT)
ISOLATED_ROOT.mkdir()
modules = sorted(path for path in ROOT.iterdir() if path.is_dir() and not path.name.startswith("."))
assert len(modules) == 17, f"模块数量错误：{len(modules)}"
for module in modules:
    shutil.copytree(module, ISOLATED_ROOT / module.name, ignore=shutil.ignore_patterns(".routes"))

local_entries = sorted(ISOLATED_ROOT.rglob("打开课件.html"))
assert local_entries, "未找到本地打开入口"
root_entries = [module / "打开课件.html" for module in sorted(ISOLATED_ROOT.iterdir())]
assert len(root_entries) == 17 and all(entry.is_file() for entry in root_entries), "模块根目录缺少打开课件.html"

for entry in local_entries:
    label = entry.relative_to(ISOLATED_ROOT)
    module_root = (ISOLATED_ROOT / label.parts[0]).resolve()
    html = entry.read_text(encoding="utf-8")
    assert "/.routes/" not in html, f"入口仍依赖隐藏路由：{label}"
    parser = LocalResourceParser()
    parser.feed(html)
    for reference in parser.resources:
        parsed = urlparse(reference)
        if parsed.scheme in {"https", "http", "data"}:
            continue
        assert not parsed.scheme, f"非本地资源引用：{label} -> {reference}"
        resource = (entry.parent / unquote(parsed.path)).resolve()
        assert resource.is_relative_to(module_root), f"资源越过模块目录：{label} -> {reference}"
        assert resource.is_file(), f"本地资源缺失：{label} -> {reference}"

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 1000}, device_scale_factor=1)
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("requestfailed", lambda request: failed_requests.append(f"{request.failure} {request.url}"))

    for entry in root_entries:
        open_local(page, entry)
        page.wait_for_timeout(100)
        label = entry.relative_to(ISOLATED_ROOT)
        assert page.locator("link[rel='stylesheet']").count() >= 2, f"样式表缺失：{label}"
        h1_size = float(page.locator("h1").evaluate("element => parseFloat(getComputedStyle(element).fontSize)"))
        assert h1_size >= 40, f"本地页面样式未加载：{label}（标题字号 {h1_size}）"

        first_image = page.locator(".VPDoc img").first
        if first_image.count():
            first_image.scroll_into_view_if_needed()
            page.wait_for_timeout(300)
            assert first_image.evaluate("item => item.complete && item.naturalWidth > 0"), f"本地图片未加载：{label}"

    example = ISOLATED_ROOT / "20_自媒体增长闭环" / "打开课件.html"
    open_local(page, example)
    assert "第 20 章 自媒体不只是靠努力" in page.locator("h1").inner_text()
    page.screenshot(path=str(SCREENSHOT_DIR / "独立案例_隔离副本直开.png"), full_page=False)

    open_local(page, ISOLATED_ROOT / "01_第一篇使用手册" / "打开课件.html")
    chapter_link = page.get_by_role("link", name="第 1 章 初识 WorkBuddy").last
    assert chapter_link.get_attribute("href") == "./chapter-01/打开课件.html"
    chapter_link.click()
    page.locator("h1", has_text="第 1 章 初识 WorkBuddy").wait_for(state="visible")
    assert page.url.endswith("chapter-01/%E6%89%93%E5%BC%80%E8%AF%BE%E4%BB%B6.html")
    page.screenshot(path=str(SCREENSHOT_DIR / "第一篇_本地章节跳转.png"), full_page=False)

    open_local(page, ISOLATED_ROOT / "26_第四篇岗位与行业落地" / "打开课件.html")
    chapter_link = page.get_by_role("link", name="第 27 章 行业路线图：从通用能力到行业工作流").last
    assert chapter_link.get_attribute("href") == "./chapter-27/打开课件.html"
    page.screenshot(path=str(SCREENSHOT_DIR / "第四篇_本地打开.png"), full_page=False)

    browser.close()

assert not errors, "本地打开页面出现脚本错误：\n" + "\n".join(errors)
meaningful_failures = [
    failure
    for failure in failed_requests
    if not ("net::ERR_ABORTED" in failure and failure.lower().endswith(".mp4"))
]
assert not meaningful_failures, "本地打开页面出现资源请求失败：\n" + "\n".join(meaningful_failures[:20])
print(f"隔离副本验收通过：17 个模块、{len(local_entries)} 个打开课件.html 均可从本地相对路径加载样式和图片，篇内章节链接正常。")
