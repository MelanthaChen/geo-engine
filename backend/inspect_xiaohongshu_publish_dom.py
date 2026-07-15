import json
import subprocess
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

from app.services.session_resolver import SessionResolver


PUBLISH_URL = "https://creator.xiaohongshu.com/publish/publish?source=official"
OUTPUT_DIR = Path("publishing_previews/xiaohongshu_dom_inspection")
HTML_PATH = OUTPUT_DIR / "publish_dom.html"
JSON_PATH = OUTPUT_DIR / "publish_elements.json"
FULL_SCREENSHOT_PATH = OUTPUT_DIR / "publish_screenshot_full_raw.png"
VIEWPORT_SCREENSHOT_PATH = OUTPUT_DIR / "publish_screenshot_viewport_raw.png"
HIGHLIGHTED_FULL_PATH = OUTPUT_DIR / "publish_screenshot.png"
HIGHLIGHTED_VIEWPORT_PATH = OUTPUT_DIR / "publish_screenshot_viewport.png"
GRAPHIC_HTML_PATH = OUTPUT_DIR / "publish_graphic_dom.html"
GRAPHIC_JSON_PATH = OUTPUT_DIR / "publish_graphic_elements.json"
GRAPHIC_FULL_SCREENSHOT_PATH = OUTPUT_DIR / "publish_graphic_full_raw.png"
GRAPHIC_VIEWPORT_SCREENSHOT_PATH = OUTPUT_DIR / "publish_graphic_viewport_raw.png"
GRAPHIC_HIGHLIGHTED_FULL_PATH = OUTPUT_DIR / "publish_graphic.png"
GRAPHIC_HIGHLIGHTED_VIEWPORT_PATH = OUTPUT_DIR / "publish_graphic_viewport.png"
TEST_IMAGE_PATH = OUTPUT_DIR / "test_upload_image.png"
EDITOR_HTML_PATH = OUTPUT_DIR / "editor_dom.html"
EDITOR_JSON_PATH = OUTPUT_DIR / "editor_elements.json"
AFTER_UPLOAD_RAW_PATH = OUTPUT_DIR / "after_upload_raw.png"
AFTER_UPLOAD_VIEWPORT_RAW_PATH = OUTPUT_DIR / "after_upload_viewport_raw.png"
AFTER_UPLOAD_PATH = OUTPUT_DIR / "after_upload.png"
AFTER_UPLOAD_VIEWPORT_PATH = OUTPUT_DIR / "after_upload_viewport.png"


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    profile_path = SessionResolver().resolve_profile(
        platform="xiaohongshu",
        purpose="creator",
    )

    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(profile_path),
            channel="chrome",
            headless=False,
            viewport={"width": 1440, "height": 1100},
        )
        page = context.pages[0] if context.pages else context.new_page()

        print(f"Opening publish page with creator profile: {profile_path}")
        page.goto(PUBLISH_URL, wait_until="domcontentloaded")
        page.wait_for_load_state("networkidle", timeout=45000)
        page.wait_for_timeout(3000)

        inspection = collect_and_save(
            page=page,
            html_path=HTML_PATH,
            json_path=JSON_PATH,
            full_screenshot_path=FULL_SCREENSHOT_PATH,
            viewport_screenshot_path=VIEWPORT_SCREENSHOT_PATH,
            highlighted_full_path=HIGHLIGHTED_FULL_PATH,
            highlighted_viewport_path=HIGHLIGHTED_VIEWPORT_PATH,
        )
        print_report(inspection)
        print(f"Saved HTML: {HTML_PATH}")
        print(f"Saved JSON: {JSON_PATH}")
        print(f"Saved highlighted full-page screenshot: {HIGHLIGHTED_FULL_PATH}")
        print(f"Saved highlighted viewport screenshot: {HIGHLIGHTED_VIEWPORT_PATH}")
        print("EDITOR_DISCOVERY_COMPLETE")

        switch_to_graphic_tab(page)
        graphic_inspection = collect_and_save(
            page=page,
            html_path=GRAPHIC_HTML_PATH,
            json_path=GRAPHIC_JSON_PATH,
            full_screenshot_path=GRAPHIC_FULL_SCREENSHOT_PATH,
            viewport_screenshot_path=GRAPHIC_VIEWPORT_SCREENSHOT_PATH,
            highlighted_full_path=GRAPHIC_HIGHLIGHTED_FULL_PATH,
            highlighted_viewport_path=GRAPHIC_HIGHLIGHTED_VIEWPORT_PATH,
        )
        graphic_summary = summarize_graphic_tab(graphic_inspection)
        print_report(graphic_inspection)
        print(f"Saved graphic HTML: {GRAPHIC_HTML_PATH}")
        print(f"Saved graphic JSON: {GRAPHIC_JSON_PATH}")
        print(f"Saved highlighted graphic screenshot: {GRAPHIC_HIGHLIGHTED_FULL_PATH}")
        print(f"Saved highlighted graphic viewport screenshot: {GRAPHIC_HIGHLIGHTED_VIEWPORT_PATH}")
        print("GRAPHIC_TAB_READY")
        print(f"current_url={graphic_inspection['current_url']}")
        print(f"active_tab_name={graphic_summary['active_tab_name']}")
        print(f"editable_field_count={graphic_summary['editable_field_count']}")
        print(f"discovered_title_selector={graphic_summary['title_selector']}")
        print(f"discovered_body_selector={graphic_summary['body_selector']}")

        upload_info = inspect_upload_component(page)
        print("UPLOAD_COMPONENT")
        print(json.dumps(upload_info, ensure_ascii=False, indent=2))

        create_test_image(TEST_IMAGE_PATH)
        print(f"Generated temporary test image: {TEST_IMAGE_PATH}")
        upload_test_image(page, TEST_IMAGE_PATH)
        wait_for_editor_after_upload(page)

        editor_inspection = collect_and_save(
            page=page,
            html_path=EDITOR_HTML_PATH,
            json_path=EDITOR_JSON_PATH,
            full_screenshot_path=AFTER_UPLOAD_RAW_PATH,
            viewport_screenshot_path=AFTER_UPLOAD_VIEWPORT_RAW_PATH,
            highlighted_full_path=AFTER_UPLOAD_PATH,
            highlighted_viewport_path=AFTER_UPLOAD_VIEWPORT_PATH,
        )
        editor_summary = summarize_editor(editor_inspection)
        print_report(editor_inspection)
        print(f"Saved editor HTML: {EDITOR_HTML_PATH}")
        print(f"Saved editor JSON: {EDITOR_JSON_PATH}")
        print(f"Saved after-upload screenshot: {AFTER_UPLOAD_PATH}")
        print("EDITOR_READY_AFTER_UPLOAD")
        print(f"title_selector={editor_summary['title_selector']}")
        print(f"body_selector={editor_summary['body_selector']}")
        print(f"publish_selector={editor_summary['publish_selector']}")

        try:
            input("Press ENTER to close the inspector browser...")
        except EOFError:
            pass
        context.close()


def collect_and_save(
    page,
    html_path: Path,
    json_path: Path,
    full_screenshot_path: Path,
    viewport_screenshot_path: Path,
    highlighted_full_path: Path,
    highlighted_viewport_path: Path,
) -> dict:
    inspection = collect_dom_inspection(page)

    html_path.write_text(page.content(), encoding="utf-8")
    json_path.write_text(
        json.dumps(inspection, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    page.screenshot(path=str(viewport_screenshot_path), full_page=False)
    page.screenshot(path=str(full_screenshot_path), full_page=True)

    draw_highlights(
        source=viewport_screenshot_path,
        target=highlighted_viewport_path,
        elements=inspection["editable_elements"],
        viewport=True,
    )
    draw_highlights(
        source=full_screenshot_path,
        target=highlighted_full_path,
        elements=inspection["editable_elements"],
        viewport=False,
    )

    return inspection


def collect_dom_inspection(page) -> dict:
    return page.evaluate(
        """() => {
            const selectors = [
                'input',
                'textarea',
                '[contenteditable]',
                '[role="textbox"]',
                '[role="combobox"]',
                'button',
                'xhs-publish-btn',
                '[class*="editor"]',
                '[class*="input"]',
                '[class*="title"]',
                '[class*="publish"]',
                '[class*="ProseMirror"]',
                '[class*="DraftEditor"]',
                '[class*="slate"]',
            ];

            const unique = (nodes) => Array.from(new Set(nodes));
            const visible = (element) => {
                const style = window.getComputedStyle(element);
                const rect = element.getBoundingClientRect();
                return (
                    style &&
                    style.visibility !== 'hidden' &&
                    style.display !== 'none' &&
                    rect.width > 0 &&
                    rect.height > 0
                );
            };
            const attrs = (element) => {
                const result = {};
                for (const attr of element.attributes || []) {
                    if (
                        attr.name === 'aria-label' ||
                        attr.name.startsWith('aria-') ||
                        attr.name === 'role' ||
                        attr.name === 'placeholder' ||
                        attr.name === 'type' ||
                        attr.name === 'id' ||
                        attr.name === 'class' ||
                        attr.name === 'data-testid'
                    ) {
                        result[attr.name] = attr.value;
                    }
                }
                return result;
            };
            const box = (element) => {
                const rect = element.getBoundingClientRect();
                return {
                    x: rect.x,
                    y: rect.y,
                    width: rect.width,
                    height: rect.height,
                    page_x: rect.x + window.scrollX,
                    page_y: rect.y + window.scrollY,
                };
            };
            const describe = (element, index) => ({
                index,
                tag: element.tagName.toLowerCase(),
                type: element.getAttribute('type'),
                placeholder: element.getAttribute('placeholder'),
                aria_label: element.getAttribute('aria-label'),
                id: element.id || null,
                class: element.className ? String(element.className) : null,
                role: element.getAttribute('role'),
                contenteditable: element.getAttribute('contenteditable'),
                aria: attrs(element),
                text_length: (element.innerText || element.textContent || element.value || '').length,
                outerHTML: element.outerHTML,
                bounding_box: box(element),
                visible: visible(element),
            });

            const inputs = Array.from(document.querySelectorAll('input'))
                .filter(visible)
                .map(describe);
            const textareas = Array.from(document.querySelectorAll('textarea'))
                .filter(visible)
                .map(describe);
            const contenteditables = Array.from(document.querySelectorAll('[contenteditable]'))
                .filter(visible)
                .map(describe);
            const editableElements = unique(
                selectors.flatMap((selector) => Array.from(document.querySelectorAll(selector)))
            )
                .filter(visible)
                .map(describe);

            return {
                current_url: window.location.href,
                page_title: document.title,
                active_tab_name: detectActiveTabName(),
                viewport: {
                    width: window.innerWidth,
                    height: window.innerHeight,
                    scroll_x: window.scrollX,
                    scroll_y: window.scrollY,
                    document_width: document.documentElement.scrollWidth,
                    document_height: document.documentElement.scrollHeight,
                },
                inputs,
                textareas,
                contenteditables,
                editable_elements: editableElements,
            };

            function detectActiveTabName() {
                const isVisible = (element) => {
                    const style = window.getComputedStyle(element);
                    const rect = element.getBoundingClientRect();
                    return style.display !== 'none' &&
                        style.visibility !== 'hidden' &&
                        rect.width > 0 &&
                        rect.height > 0 &&
                        Number(style.opacity || 1) > 0.01;
                };
                const candidates = Array.from(document.querySelectorAll(
                    '#creator-publish-dom .header-tabs .creator-tab, [class*="tab"], [role="tab"], [role="button"], button, span.title'
                )).filter(isVisible);
                const active = candidates.find((element) => {
                    const text = (element.innerText || element.textContent || '').trim();
                    const className = String(element.className || '');
                    const ariaSelected = element.getAttribute('aria-selected');
                    return (
                        text &&
                        (className.includes('active') || ariaSelected === 'true')
                    );
                });
                if (active) {
                    return (active.innerText || active.textContent || '').trim();
                }

                const bodyText = document.body.innerText || '';
                if (bodyText.includes('上传图片，或写文字生成图片')) {
                    return '上传图文';
                }
                if (bodyText.includes('拖拽视频到此或点击上传')) {
                    return '上传视频';
                }
                return null;
            }
        }"""
    )


def switch_to_graphic_tab(page):
    print("Switching to 上传图文 tab...")
    page.wait_for_load_state("domcontentloaded")
    page.wait_for_load_state("networkidle", timeout=45000)
    click_graphic_tab(page)
    wait_for_graphic_tab_active(page)
    page.wait_for_load_state("networkidle", timeout=45000)
    page.wait_for_timeout(3000)


def click_graphic_tab(page):
    strategies = [
        ("publish header tab coordinates", lambda: click_publish_header_graphic_tab(page)),
        ("publish header tab locator", lambda: page.locator('#creator-publish-dom .header-tabs .creator-tab:has-text("上传图文")').last.click(timeout=8000)),
        ("dom visible creator tab", lambda: click_visible_graphic_tab_with_dom(page)),
        ("visible text", lambda: page.get_by_text("上传图文", exact=True).last.click(timeout=8000)),
        ("role tab", lambda: page.get_by_role("tab", name="上传图文").click(timeout=8000)),
        ("role button", lambda: page.get_by_role("button", name="上传图文").click(timeout=8000)),
        ("aria-label", lambda: page.locator('[aria-label*="上传图文"]').last.click(timeout=8000)),
        ("data-testid", lambda: page.locator('[data-testid*="image"], [data-testid*="graphic"], [data-testid*="note"]').last.click(timeout=8000)),
        ("xpath text", lambda: page.locator('xpath=//*[normalize-space(text())="上传图文"]').last.click(timeout=8000)),
        ("class tab text", lambda: page.locator('.creator-tab:has-text("上传图文"), [class*="tab"]:has-text("上传图文")').last.click(timeout=8000)),
    ]

    errors = []
    for name, strategy in strategies:
        try:
            strategy()
            print(f"Clicked 上传图文 using strategy: {name}")
            return
        except Exception as error:
            errors.append(f"{name}: {error}")

    raise RuntimeError(
        "Unable to click 上传图文 tab. Tried strategies:\n" +
        "\n".join(errors)
    )


def click_publish_header_graphic_tab(page):
    box = page.evaluate(
        """() => {
            const visible = (element) => {
                const style = window.getComputedStyle(element);
                const rect = element.getBoundingClientRect();
                return style.display !== 'none' &&
                    style.visibility !== 'hidden' &&
                    rect.width > 0 &&
                    rect.height > 0 &&
                    Number(style.opacity || 1) > 0.01;
            };
            const tabs = Array.from(document.querySelectorAll(
                '#creator-publish-dom .header-tabs .creator-tab'
            )).filter((element) =>
                visible(element) &&
                (element.innerText || element.textContent || '').includes('上传图文')
            );
            const target = tabs.at(-1);
            if (!target) {
                return null;
            }
            const rect = target.getBoundingClientRect();
            return {
                x: rect.x + rect.width / 2,
                y: rect.y + rect.height / 2,
                text: (target.innerText || target.textContent || '').trim(),
                className: String(target.className || ''),
            };
        }"""
    )

    if not box:
        raise RuntimeError("No visible #creator-publish-dom header 上传图文 tab found")

    print(f"Click target: {json.dumps(box, ensure_ascii=False)}")
    page.mouse.click(box["x"], box["y"])


def click_visible_graphic_tab_with_dom(page):
    clicked = page.evaluate(
        """() => {
            const visible = (element) => {
                const style = window.getComputedStyle(element);
                const rect = element.getBoundingClientRect();
                return style.display !== 'none' &&
                    style.visibility !== 'hidden' &&
                    rect.width > 0 &&
                    rect.height > 0 &&
                    Number(style.opacity || 1) > 0.01;
            };
            const candidates = Array.from(document.querySelectorAll(
                '.creator-tab, [class*="tab"], [role="tab"], [role="button"], button, span.title'
            )).filter((element) =>
                visible(element) &&
                (element.innerText || element.textContent || '').includes('上传图文')
            );
            const target = candidates
                .map((element) => element.closest('.creator-tab') || element)
                .find(visible);

            if (!target) {
                return false;
            }

            target.dispatchEvent(new MouseEvent('mousedown', {bubbles: true, cancelable: true, view: window}));
            target.dispatchEvent(new MouseEvent('mouseup', {bubbles: true, cancelable: true, view: window}));
            target.click();
            return true;
        }"""
    )

    if not clicked:
        raise RuntimeError("No visible 上传图文 tab found by DOM strategy")


def wait_for_graphic_tab_active(page):
    try:
        page.wait_for_function(
            """() => {
                const state = window.__geoGraphicTabState = getGraphicTabState();
                return state.graphic_active && state.video_inactive;

                function getGraphicTabState() {
                    const visible = (element) => {
                        const style = window.getComputedStyle(element);
                        const rect = element.getBoundingClientRect();
                        return style.display !== 'none' &&
                            style.visibility !== 'hidden' &&
                            rect.width > 0 &&
                            rect.height > 0 &&
                            Number(style.opacity || 1) > 0.01;
                    };
                    const tabs = Array.from(document.querySelectorAll(
                        '.creator-tab, [class*="tab"], [role="tab"], [role="button"], button'
                    )).filter(visible);
                    const graphic = tabs.find((element) =>
                        (element.innerText || element.textContent || '').includes('上传图文')
                    );
                    const video = tabs.find((element) =>
                        (element.innerText || element.textContent || '').includes('上传视频')
                    );
                    const graphicClass = graphic ? String(graphic.className || '') : '';
                    const videoClass = video ? String(video.className || '') : '';
                    return {
                        graphic_found: Boolean(graphic),
                        video_found: Boolean(video),
                        graphic_active: Boolean(graphic) && (
                            graphicClass.includes('active') ||
                            graphic.getAttribute('aria-selected') === 'true'
                        ),
                        video_inactive: !video || (
                            !videoClass.includes('active') &&
                            video.getAttribute('aria-selected') !== 'true'
                        ),
                    };
                }
            }""",
            timeout=12000,
        )
        print("上传图文 tab is active; 上传视频 tab is inactive.")
        return
    except Exception:
        state = page.evaluate(
            """() => {
                const text = document.body.innerText || '';
                const visible = (selector) => Array.from(document.querySelectorAll(selector)).some((element) => {
                    const style = window.getComputedStyle(element);
                    const rect = element.getBoundingClientRect();
                    return style.display !== 'none' &&
                        style.visibility !== 'hidden' &&
                        rect.width > 0 &&
                        rect.height > 0;
                });
                return {
                    body_has_graphic_tab: text.includes('上传图文'),
                    body_has_video_tab: text.includes('上传视频'),
                    body_has_image_upload: text.includes('上传图片') || text.includes('上传图文') || text.includes('图片'),
                    body_has_video_upload: text.includes('上传视频'),
                    visible_file_input: visible('input[type="file"]'),
                    active_state: window.__geoGraphicTabState || null,
                };
            }"""
        )
        print(
            "上传图文 active-state class verification timed out; "
            f"continuing inspection with state={json.dumps(state, ensure_ascii=False)}"
        )

    page.wait_for_timeout(3000)


def inspect_upload_component(page) -> dict:
    return page.evaluate(
        """() => {
            const box = (element) => {
                const rect = element.getBoundingClientRect();
                return {
                    x: rect.x,
                    y: rect.y,
                    width: rect.width,
                    height: rect.height,
                    page_x: rect.x + window.scrollX,
                    page_y: rect.y + window.scrollY,
                };
            };
            const visible = (element) => {
                const style = window.getComputedStyle(element);
                const rect = element.getBoundingClientRect();
                return style.display !== 'none' &&
                    style.visibility !== 'hidden' &&
                    rect.width > 0 &&
                    rect.height > 0 &&
                    Number(style.opacity || 1) > 0.01;
            };
            const describe = (element, index) => ({
                index,
                tag: element.tagName.toLowerCase(),
                type: element.getAttribute('type'),
                accept: element.getAttribute('accept'),
                multiple: element.hasAttribute('multiple'),
                text: (element.innerText || element.textContent || '').trim().slice(0, 200),
                class: String(element.className || ''),
                id: element.id || null,
                visible: visible(element),
                bounding_box: box(element),
                outerHTML: element.outerHTML.slice(0, 800),
            });

            return {
                file_inputs: Array.from(document.querySelectorAll('input[type="file"]')).map(describe),
                upload_buttons: Array.from(document.querySelectorAll('button, [role="button"], .upload-button, [class*="upload"]'))
                    .filter((element) => {
                        const text = (element.innerText || element.textContent || '').trim();
                        const className = String(element.className || '');
                        return visible(element) && (
                            text.includes('上传') ||
                            text.includes('图片') ||
                            className.includes('upload')
                        );
                    })
                    .map(describe),
                drag_drop_areas: Array.from(document.querySelectorAll(
                    '.drag-over, [class*="drag"], [class*="upload-wrapper"], [class*="upload-container"], [class*="upload-content"]'
                ))
                    .filter(visible)
                    .map(describe),
                body_text_sample: (document.body.innerText || '').slice(0, 500),
            };
        }"""
    )


def create_test_image(path: Path):
    script = f"""
from PIL import Image, ImageDraw, ImageFont

path = {str(path)!r}
image = Image.new("RGB", (1200, 1600), "white")
draw = ImageDraw.Draw(image)
text = "TEST"
try:
    font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 180)
except Exception:
    font = ImageFont.load_default()
box = draw.textbbox((0, 0), text, font=font)
x = (1200 - (box[2] - box[0])) / 2
y = (1600 - (box[3] - box[1])) / 2
draw.text((x, y), text, fill="black", font=font)
image.save(path)
"""
    subprocess.run(["python3", "-c", script], check=True)


def upload_test_image(page, image_path: Path):
    print("Uploading temporary image through 图文 upload input...")
    file_input = page.locator('input[type="file"][accept*="png"], input[type="file"]').first
    file_input.set_input_files(str(image_path))
    print("Temporary image selected.")


def wait_for_editor_after_upload(page):
    print("Waiting for upload to finish and editor to mount...")
    page.wait_for_function(
        """() => {
            const text = document.body.innerText || '';
            const titleLike = Array.from(document.querySelectorAll('input, textarea, [contenteditable], [role="textbox"]'))
                .some((element) => {
                    const marker = [
                        element.getAttribute('placeholder'),
                        element.getAttribute('aria-label'),
                        element.getAttribute('class'),
                        element.id,
                        element.outerHTML.slice(0, 300),
                    ].join(' ');
                    return marker.includes('标题') || marker.toLowerCase().includes('title');
                });
            const bodyLike = Array.from(document.querySelectorAll('textarea, [contenteditable], [role="textbox"], [class*="editor"], [class*="ProseMirror"], [class*="slate"]'))
                .some((element) => {
                    const marker = [
                        element.getAttribute('placeholder'),
                        element.getAttribute('aria-label'),
                        element.getAttribute('class'),
                        element.id,
                        element.outerHTML.slice(0, 300),
                    ].join(' ');
                    return marker.includes('正文') ||
                        marker.includes('描述') ||
                        marker.includes('内容') ||
                        marker.includes('分享') ||
                        marker.toLowerCase().includes('editor') ||
                        marker.includes('ProseMirror') ||
                        marker.includes('slate');
                });
            const publishLike = Array.from(document.querySelectorAll('xhs-publish-btn, button, [role="button"], [class*="publish"]'))
                .some((element) => (element.innerText || element.textContent || '').includes('发布'));
            const publishComponent = Boolean(document.querySelector('xhs-publish-btn[submit-text*="发布"]'));
            const uploadStillVisible = text.includes('上传图片，或写文字生成图片');
            const progressVisible = text.includes('上传中') || text.includes('处理中') || text.includes('%');
            window.__geoAfterUploadState = {
                titleLike,
                bodyLike,
                publishLike: publishLike || publishComponent,
                uploadStillVisible,
                progressVisible,
                textSample: text.slice(0, 300),
            };
            return (titleLike || bodyLike) && (publishLike || publishComponent) && !progressVisible;
        }""",
        timeout=90000,
    )
    state = page.evaluate("() => window.__geoAfterUploadState || null")
    print(f"Editor mount state: {json.dumps(state, ensure_ascii=False)}")
    page.wait_for_timeout(3000)


def summarize_graphic_tab(inspection: dict) -> dict:
    title_selector = discover_title_selector(inspection)
    body_selector = discover_body_selector(inspection)

    return {
        "active_tab_name": inspection.get("active_tab_name") or "unknown",
        "editable_field_count": len(inspection.get("editable_elements", [])),
        "title_selector": title_selector,
        "body_selector": body_selector,
    }


def summarize_editor(inspection: dict) -> dict:
    return {
        "title_selector": discover_title_selector(inspection),
        "body_selector": discover_body_selector(inspection),
        "publish_selector": discover_publish_selector(inspection),
    }


def discover_title_selector(inspection: dict) -> str | None:
    for element in inspection.get("inputs", []) + inspection.get("textareas", []):
        text = " ".join(
            str(value or "")
            for value in [
                element.get("placeholder"),
                element.get("aria_label"),
                element.get("class"),
                element.get("id"),
            ]
        )
        if "标题" in text or "title" in text.lower():
            return selector_for_element(element)

    for element in inspection.get("editable_elements", []):
        if not (
            element.get("contenteditable") == "true" or
            element.get("role") == "textbox" or
            element.get("tag") in {"input", "textarea"}
        ):
            continue
        text = " ".join(
            str(value or "")
            for value in [
                element.get("placeholder"),
                element.get("aria_label"),
                element.get("class"),
                element.get("id"),
                element.get("outerHTML", "")[:300],
            ]
        )
        if "标题" in text or "title" in text.lower():
            return selector_for_element(element)

    return None


def discover_publish_selector(inspection: dict) -> str | None:
    for element in inspection.get("editable_elements", []):
        if element.get("tag") == "xhs-publish-btn":
            return 'xhs-publish-btn[submit-text*="发布"]'

    candidates = []
    for element in inspection.get("editable_elements", []):
        text = " ".join(
            str(value or "")
            for value in [
                element.get("class"),
                element.get("id"),
                element.get("role"),
                element.get("outerHTML", "")[:500],
            ]
        )
        if "发布" in text or "publish" in text.lower():
            candidates.append(element)

    for element in candidates:
        selector = selector_for_element(element)
        if selector:
            return selector

    return None


def discover_body_selector(inspection: dict) -> str | None:
    body_markers = ["正文", "描述", "内容", "分享", "editor", "ProseMirror", "slate", "DraftEditor"]

    for element in (
        inspection.get("contenteditables", []) +
        inspection.get("textareas", []) +
        inspection.get("editable_elements", [])
    ):
        if not (
            element.get("contenteditable") == "true" or
            element.get("role") == "textbox" or
            element.get("tag") == "textarea"
        ):
            continue
        text = " ".join(
            str(value or "")
            for value in [
                element.get("placeholder"),
                element.get("aria_label"),
                element.get("class"),
                element.get("id"),
                element.get("role"),
                element.get("outerHTML", "")[:300],
            ]
        )
        if any(marker.lower() in text.lower() for marker in body_markers):
            return selector_for_element(element)

    return None


def selector_for_element(element: dict) -> str:
    if element.get("id"):
        return f"#{element['id']}"

    tag = element.get("tag") or "*"
    placeholder = element.get("placeholder")
    aria_label = element.get("aria_label")
    role = element.get("role")
    class_name = element.get("class")

    if placeholder:
        return f'{tag}[placeholder*="{placeholder[:12]}"]'

    if aria_label:
        return f'{tag}[aria-label*="{aria_label[:12]}"]'

    if role:
        return f'{tag}[role="{role}"]'

    if class_name:
        first_class = str(class_name).split()[0]
        return f"{tag}.{first_class}"

    return tag


def draw_highlights(source: Path, target: Path, elements: list[dict], viewport: bool):
    elements_path = target.with_suffix(".elements.json")
    elements_path.write_text(
        json.dumps(elements, ensure_ascii=False),
        encoding="utf-8",
    )
    script = f"""
import json
from PIL import Image, ImageDraw

source = {str(source)!r}
target = {str(target)!r}
elements_path = {str(elements_path)!r}
viewport = {viewport!r}

image = Image.open(source).convert("RGBA")
draw = ImageDraw.Draw(image)
elements = json.loads(open(elements_path, encoding="utf-8").read())

for element in elements:
    box = element.get("bounding_box") or {{}}
    if viewport:
        x = box.get("x", 0)
        y = box.get("y", 0)
    else:
        x = box.get("page_x", 0)
        y = box.get("page_y", 0)
    width = box.get("width", 0)
    height = box.get("height", 0)
    if width <= 0 or height <= 0:
        continue
    draw.rectangle(
        [x, y, x + width, y + height],
        outline=(255, 0, 0, 255),
        width=4,
    )

image.save(target)
"""
    subprocess.run(
        ["python3", "-c", script],
        check=True,
    )


def compact_element(element: dict) -> dict:
    return {
        "index": element.get("index"),
        "tag": element.get("tag"),
        "type": element.get("type"),
        "placeholder": element.get("placeholder"),
        "aria_label": element.get("aria_label"),
        "id": element.get("id"),
        "class": element.get("class"),
        "role": element.get("role"),
        "contenteditable": element.get("contenteditable"),
        "text_length": element.get("text_length"),
        "bounding_box": element.get("bounding_box"),
    }


def print_report(inspection: dict):
    print("Current URL:", inspection["current_url"])
    print("Page title:", inspection["page_title"])

    print("\nVISIBLE_INPUTS")
    for element in inspection["inputs"]:
        print(json.dumps(compact_element(element), ensure_ascii=False))

    print("\nVISIBLE_TEXTAREAS")
    for element in inspection["textareas"]:
        print(json.dumps(compact_element(element), ensure_ascii=False))

    print("\nCONTENTEDITABLE_ELEMENTS")
    for element in inspection["contenteditables"]:
        compact = compact_element(element)
        compact["outerHTML"] = (element.get("outerHTML") or "")[:1000]
        compact["aria"] = element.get("aria")
        print(json.dumps(compact, ensure_ascii=False))

    print("\nALL_EDITABLE_ELEMENTS")
    for element in inspection["editable_elements"]:
        print(json.dumps(compact_element(element), ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
