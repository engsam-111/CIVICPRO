async def run_test(page, output_dir, page_url):
    import re
    try:
        await page.set_viewport_size({"width": 390, "height": 844})
        await page.goto('https://project-pulse-641.preview.emergentagent.com/', wait_until='domcontentloaded')
        await page.wait_for_timeout(2500)
        print('URL after root:', page.url)
        assert '/sign-in' in page.url
        print('PASS: root redirects signed-out user to sign-in')
        await page.wait_for_selector('[data-testid="auth-loading"], .cl-card, [data-testid="auth-unavailable"]', timeout=10000)
        if await page.locator('.cl-card').count():
            print('PASS: Clerk sign-in card rendered')
        elif await page.locator('[data-testid="auth-unavailable"]').count():
            print('FINDING: auth unavailable message rendered')
        else:
            print('FINDING: Clerk card did not render')
        overflow = await page.evaluate('document.documentElement.scrollWidth > document.documentElement.clientWidth')
        print('Mobile overflow:', overflow)
        assert not overflow
        print('PASS: signed-out mobile layout has no horizontal overflow')
        await page.goto('https://project-pulse-641.preview.emergentagent.com/projects', wait_until='domcontentloaded')
        await page.wait_for_timeout(2000)
        print('Projects URL:', page.url)
        assert '/sign-in' in page.url
        print('PASS: protected projects route redirects signed-out user')
        error_text = await page.evaluate("""() => { const errorElements = Array.from(document.querySelectorAll('.error, [class*="error"], [id*="error"]')); return errorElements.map(el => el.textContent).join(', '); }""")
        if error_text:
            print('Found error message:', error_text)
        else:
            print('No error messages found on the page')
    except AssertionError as exc:
        print('FINDING:', exc)
    except Exception as exc:
        print('SCRIPT ERROR:', exc)
        raise
