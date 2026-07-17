import json
from pathlib import Path

from playwright.sync_api import sync_playwright


STATE_DIR = Path("tmp_reddit_migration")
STORAGE_STATE_PATH = STATE_DIR / "storage_state.json"
PERSISTENT_PROFILE_DIR = STATE_DIR / "persistent_profile"
HOME_URL = "https://www.reddit.com/"
LOGIN_URL = "https://www.reddit.com/login/"
ORIGIN = "https://www.reddit.com"


def collect_browser_state(page, context, label):
    state = page.evaluate(
        """
        async () => {
            const indexedDBNames = [];
            try {
                if (indexedDB.databases) {
                    const databases = await indexedDB.databases();
                    for (const database of databases) {
                        indexedDBNames.push(database.name || "");
                    }
                }
            } catch (error) {
                indexedDBNames.push(`[indexedDB error: ${error.name}]`);
            }

            const permissionStates = {};
            for (const permissionName of ["geolocation", "notifications", "camera", "microphone"]) {
                try {
                    const result = await navigator.permissions.query({name: permissionName});
                    permissionStates[permissionName] = result.state;
                } catch (error) {
                    permissionStates[permissionName] = `error:${error.name}`;
                }
            }

            return {
                url: location.href,
                title: document.title,
                readyState: document.readyState,
                documentCookieNames: document.cookie
                    .split(";")
                    .map((item) => item.split("=")[0].trim())
                    .filter(Boolean)
                    .sort(),
                localStorageKeys: Object.keys(localStorage).sort(),
                sessionStorageKeys: Object.keys(sessionStorage).sort(),
                indexedDBNames: indexedDBNames.filter(Boolean).sort(),
                navigator: {
                    webdriver: navigator.webdriver,
                    userAgent: navigator.userAgent,
                    platform: navigator.platform,
                    language: navigator.language,
                    languages: Array.from(navigator.languages || []),
                    pluginsLength: navigator.plugins ? navigator.plugins.length : null,
                    mimeTypesLength: navigator.mimeTypes ? navigator.mimeTypes.length : null,
                    hardwareConcurrency: navigator.hardwareConcurrency,
                    deviceMemory: navigator.deviceMemory || null,
                    maxTouchPoints: navigator.maxTouchPoints,
                    cookieEnabled: navigator.cookieEnabled,
                    doNotTrack: navigator.doNotTrack,
                    pdfViewerEnabled: navigator.pdfViewerEnabled,
                    userAgentData: navigator.userAgentData
                        ? {
                            brands: navigator.userAgentData.brands,
                            mobile: navigator.userAgentData.mobile,
                            platform: navigator.userAgentData.platform,
                        }
                        : null,
                },
                screen: {
                    width: screen.width,
                    height: screen.height,
                    availWidth: screen.availWidth,
                    availHeight: screen.availHeight,
                    colorDepth: screen.colorDepth,
                    pixelDepth: screen.pixelDepth,
                },
                window: {
                    outerWidth,
                    outerHeight,
                    innerWidth,
                    innerHeight,
                    devicePixelRatio,
                    chromeRuntimeExists: Boolean(window.chrome && window.chrome.runtime),
                },
                permissions: permissionStates,
                bodyTextStart: (document.body && document.body.innerText || "").slice(0, 200),
            };
        }
        """
    )
    cookies = context.cookies([ORIGIN])
    state["contextCookieNames"] = sorted(
        {
            f"{cookie.get('domain')}::{cookie.get('name')}::{cookie.get('path')}"
            for cookie in cookies
        }
    )
    print(f"\n=== {label} STATE ===")
    print(json.dumps(state, ensure_ascii=False, indent=2))
    return state


def extract_origin_storage(storage_state):
    local_storage = []
    for origin_state in storage_state.get("origins", []):
        if origin_state.get("origin") == ORIGIN:
            local_storage = origin_state.get("localStorage", [])
            break
    return {
        "cookies": storage_state.get("cookies", []),
        "localStorage": local_storage,
    }


def apply_local_storage(page, local_storage):
    page.goto(ORIGIN, wait_until="domcontentloaded")
    page.evaluate(
        """
        (items) => {
            for (const item of items) {
                localStorage.setItem(item.name, item.value);
            }
        }
        """,
        local_storage,
    )


def compare_values(path, first, second, differences):
    if isinstance(first, dict) and isinstance(second, dict):
        for key in sorted(set(first) | set(second)):
            compare_values(
                f"{path}.{key}" if path else key,
                first.get(key),
                second.get(key),
                differences,
            )
        return

    if first != second:
        differences.append(
            {
                "property": path,
                "launch": first,
                "persistent": second,
            }
        )


def is_challenged(url):
    return "js_challenge=1" in url or "challenge" in url.lower()


def main():
    STATE_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        print("=== PHASE 1: chromium.launch() ===")
        browser = playwright.chromium.launch(
            channel="chrome",
            headless=False,
        )
        context = browser.new_context()
        page = context.new_page()

        page.goto(LOGIN_URL, wait_until="domcontentloaded")
        page.wait_for_timeout(5000)
        print("LAUNCH LOGIN URL:", page.url)
        print("LAUNCH LOGIN TITLE:", page.title())
        page.screenshot(path=str(STATE_DIR / "launch_login.png"), full_page=True)

        input("Log in in the launch() browser, then press ENTER here...")

        page.goto(HOME_URL, wait_until="domcontentloaded")
        page.wait_for_timeout(5000)
        launch_state = collect_browser_state(page, context, "launch")
        page.screenshot(path=str(STATE_DIR / "launch_after_login.png"), full_page=True)

        context.storage_state(path=str(STORAGE_STATE_PATH))
        storage_state = json.loads(STORAGE_STATE_PATH.read_text(encoding="utf-8"))
        exported = extract_origin_storage(storage_state)
        print("\n=== EXPORTED STATE SUMMARY ===")
        print("storage_state:", STORAGE_STATE_PATH)
        print("cookie_count:", len(exported["cookies"]))
        print(
            "cookie_names:",
            sorted({f"{cookie.get('domain')}::{cookie.get('name')}" for cookie in exported["cookies"]}),
        )
        print(
            "localStorage_keys:",
            sorted({item.get("name") for item in exported["localStorage"]}),
        )
        print("sessionStorage_migration: not supported by Playwright storage_state")
        print("indexedDB_migration: not supported by Playwright storage_state")
        browser.close()

        print("\n=== PHASE 2: launch_persistent_context() + migrated state ===")
        persistent_context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(PERSISTENT_PROFILE_DIR),
            channel="chrome",
            headless=False,
        )
        persistent_page = (
            persistent_context.pages[0]
            if persistent_context.pages
            else persistent_context.new_page()
        )

        persistent_context.add_cookies(exported["cookies"])
        apply_local_storage(persistent_page, exported["localStorage"])

        persistent_page.goto(HOME_URL, wait_until="domcontentloaded")
        persistent_page.wait_for_timeout(5000)
        persistent_state = collect_browser_state(
            persistent_page,
            persistent_context,
            "persistent",
        )
        persistent_page.screenshot(
            path=str(STATE_DIR / "persistent_after_migration.png"),
            full_page=True,
        )

        differences = []
        compare_values(
            "",
            {
                "navigator": launch_state["navigator"],
                "screen": launch_state["screen"],
                "window": launch_state["window"],
                "permissions": launch_state["permissions"],
                "localStorageKeys": launch_state["localStorageKeys"],
                "sessionStorageKeys": launch_state["sessionStorageKeys"],
                "indexedDBNames": launch_state["indexedDBNames"],
                "documentCookieNames": launch_state["documentCookieNames"],
                "contextCookieNames": launch_state["contextCookieNames"],
            },
            {
                "navigator": persistent_state["navigator"],
                "screen": persistent_state["screen"],
                "window": persistent_state["window"],
                "permissions": persistent_state["permissions"],
                "localStorageKeys": persistent_state["localStorageKeys"],
                "sessionStorageKeys": persistent_state["sessionStorageKeys"],
                "indexedDBNames": persistent_state["indexedDBNames"],
                "documentCookieNames": persistent_state["documentCookieNames"],
                "contextCookieNames": persistent_state["contextCookieNames"],
            },
            differences,
        )

        print("\n=== RESULT ===")
        print("launch_url:", launch_state["url"])
        print("persistent_url:", persistent_state["url"])
        print("launch_js_challenge:", is_challenged(launch_state["url"]))
        print("persistent_js_challenge:", is_challenged(persistent_state["url"]))
        print("differences:")
        print(json.dumps(differences, ensure_ascii=False, indent=2))

        input("Press ENTER to close persistent browser...")
        persistent_context.close()


if __name__ == "__main__":
    main()
