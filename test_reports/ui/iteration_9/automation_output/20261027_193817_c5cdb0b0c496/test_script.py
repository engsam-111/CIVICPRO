async def run_test(page, output_dir, page_url):
    try:
        await page.set_viewport_size({"width": 390, "height": 844})
        on1 = await page.evaluate("navigator.onLine")
        await page.context.set_offline(True)
        await page.wait_for_timeout(500)
        on2 = await page.evaluate("navigator.onLine")
        await page.context.set_offline(False)
        await page.wait_for_timeout(500)
        on3 = await page.evaluate("navigator.onLine")
        print(f"E1 navigator online states before/offline/after = {on1}/{on2}/{on3}")

        error_text = await page.evaluate("""() => {
        const errorElements = Array.from(document.querySelectorAll('.error, [class*="error"], [id*="error"]'));
        return errorElements.map(el => el.textContent).join(", ");
        }""")
        if error_text:
            print(f"Found error message: {error_text}")
        else:
            print("No error messages found on the page")
    except Exception as e:
        print(f"online toggle check failed: {str(e)}")
