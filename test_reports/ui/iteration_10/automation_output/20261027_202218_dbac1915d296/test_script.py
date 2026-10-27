async def run_test(page, output_dir, page_url):
    import asyncio
    import re
    from pathlib import Path

    EMAIL = "qa.manager+clerk_test@civicpro.dev"
    PASSWORD = "CivicPro#Mgr2026"
    OTP = "424242"
    ASSET_DIR = Path('/app/tests/assets/iteration10')
    FILE_B = ASSET_DIR / 'valid-b.txt'
    FILE_C = ASSET_DIR / 'valid-c.txt'
    FILE_PDF = ASSET_DIR / 'valid-doc.pdf'
    FILE_BAD_PDF = ASSET_DIR / 'invalid-content.pdf'

    created_project_ids = []
    page.on("console", lambda msg: print(f"CONSOLE: {msg.type}: {msg.text}"))

    async def goto_projects_root():
        await page.goto('https://project-pulse-641.preview.emergentagent.com/projects')
        await page.wait_for_selector('[data-testid="new-project-button"]', timeout=20000)

    async def ensure_signed_in():
        if await page.locator('[data-testid="auth-email-input"]').count() > 0:
            await page.fill('[data-testid="auth-email-input"]', EMAIL)
            await page.fill('[data-testid="auth-password-input"]', PASSWORD)
            await page.click('[data-testid="sign-in-submit-button"]', force=True)
        for _ in range(30):
            if await page.locator('[data-testid="page-title"]').count() > 0:
                return True
            if await page.locator('[data-testid="auth-code-form"]').count() > 0:
                await page.fill('[data-testid="auth-code-input"]', OTP)
                await page.click('[data-testid="auth-verify-button"]', force=True)
            await page.wait_for_timeout(1000)
        return False

    try:
        await page.set_viewport_size({"width": 1440, "height": 1080})
        ok = await ensure_signed_in()
        print(f"Signed in: {ok}")
        if not ok:
            raise Exception("Could not sign in")

        print("Step A: Partial failure create flow")
        await goto_projects_root()
        await page.click('[data-testid="new-project-button"]', force=True)
        await page.wait_for_selector('[data-testid="form-modal"]', timeout=10000)
        mixed_code = f"TPFMIX-{int(asyncio.get_event_loop().time())%100000}"
        await page.fill('[data-testid="name-input"]', f"TEST_ProjectFiles_MIX_{mixed_code}")
        await page.fill('[data-testid="code-input"]', mixed_code)
        await page.fill('[data-testid="summary-input"]', 'Partial failure should keep project and good files')
        await page.set_input_files('[data-testid="project-files-input"]', [str(FILE_B), str(FILE_BAD_PDF), str(FILE_C)])
        await page.click('[data-testid="save-project-button"]', force=True)
        await page.wait_for_timeout(5000)
        await page.wait_for_selector('[data-testid="project-upload-warning"]', timeout=20000)
        warning_text = await page.locator('[data-testid="project-upload-warning"]').text_content()
        print(f"Warning contains invalid-content.pdf: {'invalid-content.pdf' in warning_text}")

        match = re.search(r'/projects/([^/?]+)', page.url)
        if match:
            created_project_ids.append(match.group(1))

        pane_text = await page.locator('.files-pane').text_content()
        print(f"Persisted valid-b.txt: {'valid-b.txt' in pane_text}")
        print(f"Persisted valid-c.txt: {'valid-c.txt' in pane_text}")

        await page.set_input_files('[data-testid="project-upload-input"]', [str(FILE_PDF)])
        await page.wait_for_timeout(3500)
        pane_text2 = await page.locator('.files-pane').text_content()
        print(f"Can upload replacement later (valid-doc.pdf present): {'valid-doc.pdf' in pane_text2}")

        await page.click('[data-testid="dismiss-project-upload-warning"]', force=True)
        await page.wait_for_timeout(700)
        warning_count = await page.locator('[data-testid="project-upload-warning"]').count()
        print(f"Warning dismissed count: {warning_count}")

        print("Step B: Edit project works and no file picker")
        await page.click('[data-testid="edit-project-button"]', force=True)
        await page.wait_for_selector('[data-testid="form-modal"]', timeout=10000)
        picker_count = await page.locator('[data-testid="project-files-input"]').count()
        print(f"File picker in edit modal (expected 0): {picker_count}")
        await page.fill('[data-testid="summary-input"]', 'Edited summary after partial-failure test')
        await page.click('[data-testid="save-project-button"]', force=True)
        await page.wait_for_timeout(1800)
        summary_text = await page.locator('[data-testid="project-summary"]').text_content()
        print(f"Edited summary persisted: {'Edited summary after partial-failure test' in summary_text}")

        print("Step C: Dashboard Add project uses picker and allows no-file create")
        await page.goto('https://project-pulse-641.preview.emergentagent.com/')
        await page.wait_for_selector('[data-testid="add-project-button"]', timeout=15000)
        await page.click('[data-testid="add-project-button"]', force=True)
        await page.wait_for_selector('[data-testid="form-modal"]', timeout=10000)
        dashboard_picker = await page.locator('[data-testid="project-files-input"]').count()
        print(f"Dashboard picker count: {dashboard_picker}")

        nofile_code = f"TPFNO-{int(asyncio.get_event_loop().time())%100000}"
        await page.fill('[data-testid="name-input"]', f"TEST_ProjectFiles_NOFILE_{nofile_code}")
        await page.fill('[data-testid="code-input"]', nofile_code)
        await page.click('[data-testid="save-project-button"]', force=True)
        await page.wait_for_timeout(2600)
        await page.wait_for_selector(f'[data-testid="project-row-{nofile_code}"]', timeout=15000)
        await page.click(f'[data-testid="project-row-{nofile_code}"]', force=True)
        await page.wait_for_timeout(1800)
        match2 = re.search(r'/projects/([^/?]+)', page.url)
        if match2:
            created_project_ids.append(match2.group(1))
        print("No-file project creation from dashboard verified")

        print("Step D: Responsive modal checks")
        for w in [390, 320]:
            await page.set_viewport_size({"width": w, "height": 844})
            await goto_projects_root()
            await page.click('[data-testid="new-project-button"]', force=True)
            await page.wait_for_selector('[data-testid="form-modal"]', timeout=10000)
            await page.fill('[data-testid="name-input"]', f"RESP-{w}")
            await page.fill('[data-testid="code-input"]', f"R{w}{int(asyncio.get_event_loop().time())%1000}")
            await page.locator('[data-testid="save-project-button"]').scroll_into_view_if_needed()
            vis = await page.locator('[data-testid="save-project-button"]').is_visible()
            box = await page.locator('[data-testid="form-modal"]').bounding_box()
            print(f"Viewport {w}: save visible={vis}, modal width={box['width'] if box else 'n/a'}")
            await page.click('[data-testid="close-modal-button"]', force=True)
            await page.wait_for_timeout(500)

        await page.set_viewport_size({"width": 1440, "height": 1080})
        await page.screenshot(path='/app/test_reports/ui/iteration_10/automation_output/20261027_202218_dbac1915d296/remaining_checks.jpeg', type="jpeg", quality=40, full_page=False)

        error_text = await page.evaluate("""() => {
    const errorElements = Array.from(document.querySelectorAll('.error, [class*=\"error\"], [id*=\"error\"]'));
    return errorElements.map(el => el.textContent).join(", ");
    }""")
        if error_text:
            print(f"Found error message: {error_text}")
        else:
            print("No error messages found on the page")

    except Exception as e:
        print(f"Follow-up UI flow failed: {str(e)}")

    finally:
        print(f"Cleanup IDs: {created_project_ids}")
        page.on("dialog", lambda dialog: asyncio.create_task(dialog.accept()))
        for pid in created_project_ids:
            try:
                await page.goto(f'https://project-pulse-641.preview.emergentagent.com/projects/{pid}')
                await page.wait_for_selector('[data-testid="delete-project-button"]', timeout=12000)
                await page.click('[data-testid="delete-project-button"]', force=True)
                await page.wait_for_timeout(1200)
                print(f"Cleanup attempted for {pid}")
            except Exception as ce:
                print(f"Cleanup warning for {pid}: {ce}")
        print("Follow-up run complete")
