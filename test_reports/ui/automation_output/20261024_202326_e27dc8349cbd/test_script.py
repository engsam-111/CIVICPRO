async def run_test(page, output_dir, page_url):
    import re

    try:
        await page.set_viewport_size({"width": 390, "height": 844})
        await page.wait_for_timeout(2500)
        assert await page.locator('[data-testid="auth-loading"]').count() == 0
        print("Auth loading completed")
        sign_in_text = await page.get_by_text("Sign in", exact=False).count()
        print(f"Sign-in content matches: {sign_in_text}")
        assert sign_in_text > 0
        await page.goto("https://project-pulse-641.preview.emergentagent.com/")
        await page.wait_for_timeout(1800)
        print(f"Redirected URL: {page.url}")
        assert "/sign-in" in page.url
        await page.goto("https://project-pulse-641.preview.emergentagent.com/projects")
        await page.wait_for_timeout(1200)
        print(f"Protected projects URL: {page.url}")
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
