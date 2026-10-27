async def run_test(page, output_dir, page_url):
    try:
        await page.set_viewport_size({"width": 1920, "height": 1080})
        page.on("console", lambda msg: print(f"CONSOLE: {msg.type}: {msg.text}"))
        await page.wait_for_timeout(1500)
        await page.screenshot(path="/app/test_reports/ui/iteration_10/automation_output/20261027_201523_7f1b6f83de27/initial_load.jpeg", type="jpeg", quality=40, full_page=False)
        print("Initial load screenshot captured")
        title = await page.title()
        print(f"Page title: {title}")
    except Exception as e:
        print(f"Initial load check failed: {str(e)}")
