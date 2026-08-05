import json
from pathlib import Path
from urllib.parse import quote, unquote, urlparse

from playwright.sync_api import sync_playwright


ROOT = Path("/Users/dielangli/Desktop/职场AI培训/WorkBuddyGuide_散装版")
BASE_URL = "http://127.0.0.1:8899"
SCREENSHOT_DIR = Path(__file__).resolve().parents[1] / "artifacts" / "modular-courseware-qa"


def module_url(module: dict, suffix: str = "") -> str:
    route = module["route"]
    encoded_suffix = "/".join(quote(segment, safe="") for segment in suffix.split("/") if segment)
    tail = f"/{encoded_suffix}/" if encoded_suffix else "/"
    return f"{BASE_URL}/.routes/{route}{tail}"


def visible_count(page, selector: str) -> int:
    return sum(1 for item in page.locator(selector).all() if item.is_visible())


def assert_rendered(page, title_text: str, sidebar: bool) -> None:
    page.locator("h1").first.wait_for(state="visible", timeout=30_000)
    page.wait_for_timeout(300)
    assert title_text in page.locator("body").inner_text(), f"标题缺失：{title_text}"
    assert visible_count(page, ".VPNav") == 0, f"仍显示顶部导航：{page.url}"
    assert visible_count(page, ".VPSidebar") == (1 if sidebar else 0), f"左侧目录状态错误：{page.url}"
    assert visible_count(page, ".VPDocFooter .edit-link-button") == 0, f"仍显示编辑链接：{page.url}"

    image_sources = page.locator(".VPDoc img").evaluate_all("imgs => imgs.map(img => img.src)")
    broken_images = []
    for source in image_sources:
        path_parts = [part for part in unquote(urlparse(source).path).split("/") if part]
        if len(path_parts) >= 3 and path_parts[0] == ".routes":
            module = next(item for item in manifest["modules"] if item["route"] == path_parts[1])
            resource_path = ROOT / module["folder"] / Path(*path_parts[2:])
        else:
            resource_path = ROOT / Path(*path_parts)
        if not resource_path.is_file() or resource_path.stat().st_size == 0:
            broken_images.append(str(resource_path))
    assert not broken_images, f"图片资源缺失：{broken_images[:3]}"


def assert_page(page, url: str, title_text: str, sidebar: bool) -> None:
    response = page.goto(url, wait_until="commit", timeout=60_000)
    assert response is not None and response.ok, f"页面无法打开：{url}"
    assert_rendered(page, title_text, sidebar)


manifest = json.loads((ROOT / "modules.json").read_text(encoding="utf-8"))
assert manifest["moduleCount"] == 17
assert len(manifest["modules"]) == 17
for module in manifest["modules"]:
    local_entry = ROOT / module["folder"] / "打开课件.html"
    assert local_entry.is_file(), f"缺少本地打开入口：{module['folder']}"
    assert "/.routes/" not in local_entry.read_text(encoding="utf-8"), f"本地入口仍依赖服务器路径：{module['folder']}"

SCREENSHOT_DIR.mkdir(exist_ok=True)
failed_responses: list[str] = []
console_errors: list[str] = []

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 1000}, device_scale_factor=1)
    page.on(
        "response",
        lambda response: failed_responses.append(f"{response.status} {response.url}")
        if response.status >= 400
        else None,
    )
    page.on(
        "console",
        lambda message: console_errors.append(message.text) if message.type == "error" else None,
    )

    response = page.goto(BASE_URL, wait_until="domcontentloaded")
    assert response is not None and response.ok
    assert page.locator(".module").count() == 17
    page.screenshot(path=str(SCREENSHOT_DIR / "00_模块总览.png"), full_page=True)

    # 先验证第四篇的实际篇内目录跳转，避免长时间遍历后的浏览器资源干扰。
    fourth = manifest["modules"][-1]
    fourth_chapter = "第 27 章 行业路线图：从通用能力到行业工作流"
    assert_page(page, module_url(fourth), fourth["title"], sidebar=True)
    page.get_by_role("link", name=fourth_chapter).first.click()
    page.locator("h1", has_text=fourth_chapter).wait_for(state="visible", timeout=30_000)
    assert_rendered(page, fourth_chapter, sidebar=True)
    page.screenshot(path=str(SCREENSHOT_DIR / "26_第四篇_篇内目录.png"), full_page=False)

    for module in manifest["modules"]:
        assert_page(
            page,
            module_url(module),
            module["title"],
            sidebar=module["kind"] == "collection",
        )

    first = manifest["modules"][0]
    page.goto(module_url(first), wait_until="domcontentloaded")
    page.screenshot(path=str(SCREENSHOT_DIR / "01_第一篇_篇内目录.png"), full_page=False)

    case = manifest["modules"][10]
    page.goto(module_url(case), wait_until="domcontentloaded")
    page.screenshot(path=str(SCREENSHOT_DIR / "20_第二篇_独立案例无侧栏.png"), full_page=False)

    video_case = next(item for item in manifest["modules"] if item["folder"].startswith("23_"))
    page.goto(module_url(video_case), wait_until="domcontentloaded")
    video = page.locator("video")
    assert video.count() == 1, "第 23 章视频标签缺失"
    video_src = video.get_attribute("src")
    assert video_src and "003_asset_HE1Nb74Hfo" in video_src, "第 23 章视频地址错误"
    page.screenshot(path=str(SCREENSHOT_DIR / "23_第三篇_视频案例.png"), full_page=False)
    page.close()

    browser.close()

assert not failed_responses, "存在失败的网络资源：\n" + "\n".join(failed_responses[:20])
assert not console_errors, "浏览器控制台报错：\n" + "\n".join(console_errors[:20])

print("验收通过：17 个模块均可打开，导航状态与代表性资源加载正常。")
