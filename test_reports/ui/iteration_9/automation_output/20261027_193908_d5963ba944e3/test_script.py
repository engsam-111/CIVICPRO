async def run_test(page, output_dir, page_url):
    try:
        await page.set_viewport_size({"width": 390, "height": 844})
        await page.wait_for_selector('[data-testid="auth-email-input"]', timeout=15000)
        await page.fill('[data-testid="auth-email-input"]', 'qa.manager+clerk_test@civicpro.dev')
        await page.fill('[data-testid="auth-password-input"]', 'CivicPro#Mgr2026')
        await page.click('[data-testid="sign-in-submit-button"]', force=True)
        await page.wait_for_timeout(2500)

        if await page.locator('[data-testid="auth-code-form"]').count() > 0:
            await page.fill('[data-testid="auth-code-input"]', '424242')
            await page.click('[data-testid="auth-verify-button"]', force=True)
            await page.wait_for_timeout(2500)

        if await page.locator('[data-testid="mobile-navigation"]').count() == 0:
            print('G1 login did not reach app shell')
        else:
            print('G1 manager login reached app shell')

        await page.context.set_offline(True)
        await page.wait_for_timeout(1000)
        banner = await page.locator('[data-testid="offline-banner"]').count() > 0
        print(f"G2 offline banner visible={banner}")

        await page.goto('https://project-pulse-641.preview.emergentagent.com/projects')
        await page.wait_for_timeout(1200)
        if await page.locator('[data-testid="new-project-button"]').count() > 0:
            await page.click('[data-testid="new-project-button"]', force=True)
            await page.wait_for_selector('[data-testid="form-modal"]', timeout=10000)
            await page.fill('[data-testid="name-input"]', 'TEST_OFFLINE_SAVE')
            await page.fill('[data-testid="code-input"]', 'OFFSAVE')
            await page.click('[data-testid="save-project-button"]', force=True)
            await page.wait_for_timeout(1200)
            still_open = await page.locator('[data-testid="form-modal"]').count() > 0
            print(f"G3 offline save blocked={still_open}")
        else:
            print('G3 project page unavailable offline')

        await page.goto('https://project-pulse-641.preview.emergentagent.com/nonexistent-offline-route')
        await page.wait_for_timeout(1200)
        offline_page = await page.locator('[data-testid="offline-page"]').count() > 0
        print(f"G4 offline fallback page visible={offline_page}")

        await page.context.set_offline(False)
        await page.wait_for_timeout(700)
        banner_after = await page.locator('[data-testid="offline-banner"]').count() > 0
        print(f"G5 offline banner after reconnect={banner_after}")

        error_text = await page.evaluate("""() => {
        const errorElements = Array.from(document.querySelectorAll('.error, [class*="error"], [id*="error"]'));
        return errorElements.map(el => el.textContent).join(", ");
        }""")
        if error_text:
            print(f"Found error message: {error_text}")
        else:
            print("No error messages found on the page")
    except Exception as e:
        print(f"offline check retry failed: {str(e)}")
