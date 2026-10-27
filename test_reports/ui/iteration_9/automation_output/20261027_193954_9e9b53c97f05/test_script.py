async def run_test(page, output_dir, page_url):
    try:
        await page.set_viewport_size({"width": 390, "height": 844})
        await page.wait_for_selector('[data-testid="auth-email-input"]', timeout=15000)
        await page.fill('[data-testid="auth-email-input"]', 'qa.engineer+clerk_test@civicpro.dev')
        await page.fill('[data-testid="auth-password-input"]', 'CivicPro#Test2026')
        await page.click('[data-testid="sign-in-submit-button"]', force=True)
        await page.wait_for_timeout(1800)
        old_fail = await page.locator('[data-testid="auth-error"]').count() > 0
        print(f"H2 engineer old password rejected={old_fail}")

        error_text = await page.evaluate("""() => {
        const errorElements = Array.from(document.querySelectorAll('.error, [class*="error"], [id*="error"]'));
        return errorElements.map(el => el.textContent).join(", ");
        }""")
        if error_text:
            print(f"Found error message: {error_text}")
        else:
            print("No error messages found on the page")
    except Exception as e:
        print(f"H2 old password check failed: {str(e)}")
