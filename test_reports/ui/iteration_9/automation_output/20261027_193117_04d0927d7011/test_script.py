async def run_test(page, output_dir, page_url):
    try:
        await page.set_viewport_size({"width": 1920, "height": 1080})
        print("Viewport set")
        await page.wait_for_timeout(500)
        await page.wait_for_selector('[data-testid="auth-brand"]', timeout=15000)
        print("Sign-in page loaded")
        await page.screenshot(path="/app/test_reports/ui/iteration_9/automation_output/20261027_193117_04d0927d7011/signin_desktop_smoke.jpeg", type="jpeg", quality=40, full_page=False)
        print("Smoke screenshot captured")

        error_text = await page.evaluate("""() => {
        const errorElements = Array.from(document.querySelectorAll('.error, [class*="error"], [id*="error"]'));
        return errorElements.map(el => el.textContent).join(", ");
        }""")
        if error_text:
            print(f"Found error message: {error_text}")
        else:
            print("No error messages found on the page")
    except Exception as e:
        print(f"Smoke load failed: {str(e)}")
