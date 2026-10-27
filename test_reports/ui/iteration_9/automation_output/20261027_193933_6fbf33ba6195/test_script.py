async def run_test(page, output_dir, page_url):
    try:
        await page.set_viewport_size({"width": 390, "height": 844})
        await page.wait_for_selector('[data-testid="auth-email-input"]', timeout=15000)
        await page.fill('[data-testid="auth-email-input"]', 'qa.manager+clerk_test@civicpro.dev')
        await page.fill('[data-testid="auth-password-input"]', 'CivicPro#Mgr2026')
        await page.click('[data-testid="sign-in-submit-button"]', force=True)
        await page.wait_for_timeout(2400)
        if await page.locator('[data-testid="auth-code-form"]').count() > 0:
            await page.fill('[data-testid="auth-code-input"]', '424242')
            await page.click('[data-testid="auth-verify-button"]', force=True)
            await page.wait_for_timeout(2200)

        await page.goto('https://project-pulse-641.preview.emergentagent.com/team')
        await page.wait_for_timeout(1300)
        await page.click('[data-testid="reset-password-user_3L9kur0VSQjT1w7CtIMJJu2w45c"]', force=True)
        await page.wait_for_selector('[data-testid="new-password-input"]', timeout=10000)
        await page.fill('[data-testid="new-password-input"]', 'CivicPro#Tmp2026!')
        await page.click('[data-testid="save-password-button"]', force=True)
        await page.wait_for_timeout(2200)
        print('H1 manager reset engineer to temporary password')

        error_text = await page.evaluate("""() => {
        const errorElements = Array.from(document.querySelectorAll('.error, [class*="error"], [id*="error"]'));
        return errorElements.map(el => el.textContent).join(", ");
        }""")
        if error_text:
            print(f"Found error message: {error_text}")
        else:
            print("No error messages found on the page")
    except Exception as e:
        print(f"H1 reset flow failed: {str(e)}")
