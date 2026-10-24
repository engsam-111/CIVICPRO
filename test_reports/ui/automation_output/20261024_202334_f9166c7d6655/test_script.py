async def run_test(page, output_dir, page_url):
    try:
        await page.set_viewport_size({"width": 390, "height": 844})
        await page.wait_for_selector('input[placeholder="Enter your email address"]', timeout=8000)
        print("Clerk email field rendered")
        assert await page.get_by_role("button", name="Continue").count() > 0
        print("Clerk Continue control rendered")
        await page.goto("https://project-pulse-641.preview.emergentagent.com/")
        await page.wait_for_timeout(1800)
        print(f"Root URL after signed-out navigation: {page.url}")
        assert "/sign-in" in page.url
        await page.goto("https://project-pulse-641.preview.emergentagent.com/projects")
        await page.wait_for_timeout(1200)
        print(f"Projects URL after signed-out navigation: {page.url}")
        assert "/sign-in" in page.url
        overflow = await page.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth")
        print(f"Mobile horizontal overflow: {overflow}")
        assert not overflow
        error_text = await page.evaluate("""() => { const errorElements = Array.from(document.querySelectorAll('.error, [class*="error"], [id*="error"]')); return errorElements.map(el => el.textContent).join(", "); }""")
        print(f"Errors: {error_text or 'none'}")
        print("SIGNED-OUT UI checks passed")
    except AssertionError as exc:
        print(f"FINDING: assertion failed: {exc}")
    except Exception as exc:
        print(f"FINDING: UI test error: {exc}")
