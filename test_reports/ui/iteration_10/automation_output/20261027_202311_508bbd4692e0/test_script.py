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

    async def sign_in():
        await page.goto('https://project-pulse-641.preview.emergentagent.com/sign-in')
        await page.wait_for_selector('[data-testid="auth-email-input"]', timeout=20000)
        await page.fill('[data-testid="auth-email-input"]', EMAIL)
        await page.fill('[data-testid="auth-password-input"]', PASSWORD)
        await page.click('[data-testid="sign-in-submit-button"]', force=True)
        for _ in range(35):
            if await page.locator('[data-testid="page-title"]').count() > 0:
                return True
            if await page.locator('[data-testid="auth-code-form"]').count() > 0:
                await page.fill('[data-testid="auth-code-input"]', OTP)
                await page.click('[data-testid="auth-verify-button"]', force=True)
            await page.wait_for_timeout(1000)
        return False

    async def goto_projects_root():
        await page.goto('https://project-pulse-641.preview.emergentagent.com/projects')
        await page.wait_for_selector('[data-testid="new-project-button"]', timeout=20000)

    try:
        await page.set_viewport_size({"width": 1440, "height": 1080})
        ok = await sign_in()
        print(f"Signed in result: {ok}")
        if not ok:
            raise Exception('Sign in failed')

        print('Run: partial failure flow')
        await goto_projects_root()
        await page.click('[data-testid="new-project-button"]', force=True)
        await page.wait_for_selector('[data-testid="form-modal"]', timeout=10000)
        code = f"TPFMIX-{int(asyncio.get_event_loop().time())%100000}"
        await page.fill('[data-testid="name-input"]', f"TEST_ProjectFiles_MIX_{code}")
        await page.fill('[data-testid="code-input"]', code)
        await page.set_input_files('[data-testid="project-files-input"]', [str(FILE_B), str(FILE_BAD_PDF), str(FILE_C)])
        await page.click('[data-testid="save-project-button"]', force=True)
        await page.wait_for_selector('[data-testid="project-upload-warning"]', timeout=25000)
        wt = await page.locator('[data-testid="project-upload-warning"]').text_content()
        print(f"Warning shown with invalid-content.pdf: {'invalid-content.pdf' in wt}")

        match = re.search(r'/projects/([^/?]+)', page.url)
        if match:
            created_project_ids.append(match.group(1))

        pane_text = await page.locator('.files-pane').text_content()
        print(f"valid-b persisted: {'valid-b.txt' in pane_text}")
        print(f"valid-c persisted: {'valid-c.txt' in pane_text}")

        await page.set_input_files('[data-testid="project-upload-input"]', [str(FILE_PDF)])
        await page.wait_for_timeout(3500)
        pane_text2 = await page.locator('.files-pane').text_content()
        print(f"Replacement upload works: {'valid-doc.pdf' in pane_text2}")
        await page.click('[data-testid="dismiss-project-upload-warning"]', force=True)
        await page.wait_for_timeout(500)
        wc = await page.locator('[data-testid="project-upload-warning"]').count()
        print(f"Warning dismissed count: {wc}")

        print('Run: edit modal and dashboard no-file create')
        await page.click('[data-testid="edit-project-button"]', force=True)
        await page.wait_for_selector('[data-testid="form-modal"]', timeout=10000)
        picker_count = await page.locator('[data-testid="project-files-input"]').count()
        print(f"Edit modal project-files-input count: {picker_count}")
        await page.click('[data-testid="close-modal-button"]', force=True)

        await page.goto('https://project-pulse-641.preview.emergentagent.com/')
        await page.wait_for_selector('[data-testid="add-project-button"]', timeout=15000)
        await page.click('[data-testid="add-project-button"]', force=True)
        await page.wait_for_selector('[data-testid="form-modal"]', timeout=10000)
        db_picker = await page.locator('[data-testid="project-files-input"]').count()
        print(f"Dashboard add-project picker count: {db_picker}")
        nofile_code = f"TPFNO-{int(asyncio.get_event_loop().time())%100000}"
        await page.fill('[data-testid="name-input"]', f"TEST_ProjectFiles_NOFILE_{nofile_code}")
        await page.fill('[data-testid="code-input"]', nofile_code)
        await page.click('[data-testid="save-project-button"]', force=True)
        await page.wait_for_timeout(2600)
        await page.wait_for_selector(f'[data-testid="project-row-{nofile_code}"]', timeout=15000)
        await page.click(f'[data-testid="project-row-{nofile_code}"]', force=True)
        await page.wait_for_timeout(1600)
        match2 = re.search(r'/projects/([^/?]+)', page.url)
        if match2:
            created_project_ids.append(match2.group(1))

        print('Run: responsive checks 390 and 320')
        for w in [390, 320]:
            await page.set_viewport_size({"width": w, "height": 844})
            await goto_projects_root()
            await page.click('[data-testid="new-project-button"]', force=True)
            await page.wait_for_selector('[data-testid="form-modal"]', timeout=10000)
            await page.locator('[data-testid="save-project-button"]').scroll_into_view_if_needed()
            vis = await page.locator('[data-testid="save-project-button"]').is_visible()
            print(f"Viewport {w} save visible: {vis}")
            await page.click('[data-testid="close-modal-button"]', force=True)

        await page.set_viewport_size({"width": 1440, "height": 1080})

        error_text = await page.evaluate("""() => {
    const errorElements = Array.from(document.querySelectorAll('.error, [class*=\"error\"], [id*=\"error\"]'));
    return errorElements.map(el => el.textContent).join(", ");
    }""")
        if error_text:
            print(f"Found error message: {error_text}")
        else:
            print("No error messages found on the page")

    except Exception as e:
        print(f"Run failed: {str(e)}")

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
        print('Final follow-up run complete')
