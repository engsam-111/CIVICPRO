async def run_test(page, output_dir, page_url):
    import asyncio
    import re
    from pathlib import Path

    EMAIL = "qa.manager+clerk_test@civicpro.dev"
    PASSWORD = "CivicPro#Mgr2026"
    OTP = "424242"
    ASSET_DIR = Path('/app/tests/assets/iteration10')
    FILE_A = ASSET_DIR / 'valid-a.txt'
    FILE_B = ASSET_DIR / 'valid-b.txt'
    FILE_C = ASSET_DIR / 'valid-c.txt'
    FILE_PNG = ASSET_DIR / 'valid-image.png'
    FILE_PDF = ASSET_DIR / 'valid-doc.pdf'
    FILE_BAD_PDF = ASSET_DIR / 'invalid-content.pdf'

    created_project_ids = []
    created_codes = []

    page.on("console", lambda msg: print(f"CONSOLE: {msg.type}: {msg.text}"))


    def read_bytes(path):
        return Path(path).read_bytes()


    async def ensure_projects_page():
        if "/projects" not in page.url:
            await page.goto("https://project-pulse-641.preview.emergentagent.com/projects")
            await page.wait_for_timeout(1200)


    async def wait_signed_in():
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
        print("Step 1: Sign in as manager")
        await page.wait_for_selector('[data-testid="auth-email-input"]', timeout=15000)
        await page.fill('[data-testid="auth-email-input"]', EMAIL)
        await page.fill('[data-testid="auth-password-input"]', PASSWORD)
        await page.click('[data-testid="sign-in-submit-button"]', force=True)
        signed_in = await wait_signed_in()
        print(f"Signed in status: {signed_in}, current URL: {page.url}")
        if not signed_in:
            raise Exception("Could not reach signed-in screen")

        print("Step 2: Open Projects and capture baseline")
        await page.goto('https://project-pulse-641.preview.emergentagent.com/projects')
        await page.wait_for_selector('[data-testid="new-project-button"]', timeout=20000)
        baseline_count_text = await page.locator('[data-testid="projects-count"]').text_content()
        print(f"Baseline projects count text: {baseline_count_text}")

        print("Step 3: Test pre-save picker flow and cancel")
        cancel_code = f"TPFCAN-{int(asyncio.get_event_loop().time())%100000}"
        await page.click('[data-testid="new-project-button"]', force=True)
        await page.wait_for_selector('[data-testid="form-modal"]', timeout=10000)
        await page.fill('[data-testid="name-input"]', f"TEST_ProjectFiles_CANCEL_{cancel_code}")
        await page.fill('[data-testid="code-input"]', cancel_code)

        await page.set_input_files('[data-testid="project-files-input"]', [str(FILE_A), str(FILE_PNG)])
        await page.wait_for_timeout(600)
        c1 = await page.locator('[data-testid="project-selected-file-count"]').text_content()
        print(f"After first add: {c1}")

        await page.set_input_files('[data-testid="project-files-input"]', [str(FILE_A), str(FILE_B)])
        await page.wait_for_timeout(600)
        c2 = await page.locator('[data-testid="project-selected-file-count"]').text_content()
        print(f"After second add with duplicate: {c2}")

        await page.click('[data-testid="remove-selected-file-1"]', force=True)
        await page.wait_for_timeout(400)
        c3 = await page.locator('[data-testid="project-selected-file-count"]').text_content()
        print(f"After remove index 1: {c3}")

        await page.set_input_files('[data-testid="project-files-input"]', [str(FILE_PDF)])
        await page.wait_for_timeout(600)
        c4 = await page.locator('[data-testid="project-selected-file-count"]').text_content()
        print(f"After third batch add: {c4}")

        ids = await page.eval_on_selector_all('[data-testid^="download-selected-file-"]', 'els => els.map(e => e.getAttribute("data-testid"))')
        unique_ids = len(ids) == len(set(ids))
        print(f"Download selected-file testids unique: {unique_ids} -> {ids}")

        expected_a = read_bytes(FILE_A)
        async with page.expect_download(timeout=12000) as dlinfo:
            await page.click('[data-testid="download-selected-file-0"]', force=True)
        dl = await dlinfo.value
        dl_path = await dl.path()
        downloaded_bytes = Path(dl_path).read_bytes() if dl_path else b""
        print(f"Selected download filename: {dl.suggested_filename}")
        print(f"Selected download bytes match valid-a.txt: {downloaded_bytes == expected_a}")

        await page.click('[data-testid="close-modal-button"]', force=True)
        await page.wait_for_timeout(700)
        row_exists = await page.locator(f'[data-testid="project-row-{cancel_code}"]').count()
        print(f"Cancel flow created project count (expected 0): {row_exists}")

        print("Step 4: Create project with valid files")
        good_code = f"TPFOK-{int(asyncio.get_event_loop().time())%100000}"
        created_codes.append(good_code)
        await page.click('[data-testid="new-project-button"]', force=True)
        await page.wait_for_selector('[data-testid="form-modal"]', timeout=10000)
        await page.fill('[data-testid="name-input"]', f"TEST_ProjectFiles_OK_{good_code}")
        await page.fill('[data-testid="code-input"]', good_code)
        await page.fill('[data-testid="location-input"]', 'QA Site')
        await page.fill('[data-testid="client-input"]', 'QA Client')
        await page.fill('[data-testid="summary-input"]', 'Project file upload success path')
        await page.set_input_files('[data-testid="project-files-input"]', [str(FILE_PNG), str(FILE_A)])
        await page.click('[data-testid="save-project-button"]', force=True)
        await page.wait_for_timeout(3000)
        await page.wait_for_selector('[data-testid="tab-files"]', timeout=20000)

        m = re.search(r'/projects/([^/?]+)', page.url)
        if m:
            created_project_ids.append(m.group(1))
        print(f"Created project URL: {page.url}")
        print(f"Files tab selected: {await page.get_attribute('[data-testid="tab-files"]', 'aria-selected')}")

        await page.wait_for_selector('[data-testid="attachment-list"]', timeout=15000)
        files_text = await page.locator('[data-testid="attachment-list"]').text_content()
        print(f"Files list has valid-image.png: {'valid-image.png' in files_text}")
        print(f"Files list has valid-a.txt: {'valid-a.txt' in files_text}")

        local_map = {
            'valid-a.txt': read_bytes(FILE_A),
            'valid-image.png': read_bytes(FILE_PNG),
            'valid-doc.pdf': read_bytes(FILE_PDF),
            'valid-b.txt': read_bytes(FILE_B),
            'valid-c.txt': read_bytes(FILE_C),
        }
        async with page.expect_download(timeout=15000) as dlinfo2:
            await page.locator('[data-testid^="download-attachment-"]').first.click(force=True)
        dl2 = await dlinfo2.value
        dl2_path = await dl2.path()
        b2 = Path(dl2_path).read_bytes() if dl2_path else b""
        exp = local_map.get(dl2.suggested_filename)
        print(f"Attachment download filename: {dl2.suggested_filename}")
        print(f"Attachment download bytes verified: {exp == b2 if exp is not None else 'unknown'}")

        png_row = page.locator('[data-testid^="attachment-"]', has_text='valid-image.png').first
        if await png_row.count() > 0:
            try:
                async with page.context.expect_page(timeout=7000) as new_page_info:
                    await png_row.locator('[data-testid^="open-attachment-"]').first.click(force=True)
                opened = await new_page_info.value
                await opened.wait_for_timeout(1000)
                print(f"Open behavior works for image; new page URL={opened.url}")
                await opened.close()
            except Exception as ex:
                print(f"Open behavior check warning: {ex}")

        await page.reload()
        await page.wait_for_timeout(2000)
        print(f"Files tab selected after reload: {await page.get_attribute('[data-testid="tab-files"]', 'aria-selected')}")
        await page.wait_for_selector('[data-testid="attachment-list"]', timeout=15000)

        print("Step 5: Partial failure upload flow")
        await ensure_projects_page()
        await page.click('[data-testid="new-project-button"]', force=True)
        await page.wait_for_selector('[data-testid="form-modal"]', timeout=10000)
        mixed_code = f"TPFMIX-{int(asyncio.get_event_loop().time())%100000}"
        created_codes.append(mixed_code)
        await page.fill('[data-testid="name-input"]', f"TEST_ProjectFiles_MIX_{mixed_code}")
        await page.fill('[data-testid="code-input"]', mixed_code)
        await page.fill('[data-testid="summary-input"]', 'Partial failure should keep project and good files')
        await page.set_input_files('[data-testid="project-files-input"]', [str(FILE_B), str(FILE_BAD_PDF), str(FILE_C)])
        await page.click('[data-testid="save-project-button"]', force=True)
        await page.wait_for_timeout(4500)
        await page.wait_for_selector('[data-testid="project-upload-warning"]', timeout=20000)
        warning_text = await page.locator('[data-testid="project-upload-warning"]').text_content()
        print(f"Warning visible: {True}")
        print(f"Warning contains invalid-content.pdf: {'invalid-content.pdf' in warning_text}")

        m2 = re.search(r'/projects/([^/?]+)', page.url)
        if m2:
            created_project_ids.append(m2.group(1))

        pane_text = await page.locator('.files-pane').text_content()
        print(f"Persisted valid-b.txt: {'valid-b.txt' in pane_text}")
        print(f"Persisted valid-c.txt: {'valid-c.txt' in pane_text}")

        await page.set_input_files('[data-testid="project-upload-input"]', [str(FILE_PDF)])
        await page.wait_for_timeout(3500)
        pane_text2 = await page.locator('.files-pane').text_content()
        print(f"Can upload replacement later (valid-doc.pdf present): {'valid-doc.pdf' in pane_text2}")

        await page.click('[data-testid="dismiss-project-upload-warning"]', force=True)
        await page.wait_for_timeout(600)
        print(f"Warning dismissed count: {await page.locator('[data-testid="project-upload-warning"]').count()}")

        print("Step 6: Edit project keeps normal save, no creation picker")
        await page.click('[data-testid="edit-project-button"]', force=True)
        await page.wait_for_selector('[data-testid="form-modal"]', timeout=10000)
        picker_count_edit = await page.locator('[data-testid="project-files-input"]').count()
        print(f"File picker in edit modal (expected 0): {picker_count_edit}")
        await page.fill('[data-testid="summary-input"]', 'Edited summary for iteration10 check')
        await page.click('[data-testid="save-project-button"]', force=True)
        await page.wait_for_timeout(1800)
        summary_text = await page.locator('[data-testid="project-summary"]').text_content()
        print(f"Edited summary persisted: {'Edited summary for iteration10 check' in summary_text}")

        print("Step 7: Dashboard Add project uses same picker; create without files")
        await page.goto('https://project-pulse-641.preview.emergentagent.com/')
        await page.wait_for_selector('[data-testid="add-project-button"]', timeout=15000)
        await page.click('[data-testid="add-project-button"]', force=True)
        await page.wait_for_selector('[data-testid="form-modal"]', timeout=10000)
        print(f"Dashboard picker count: {await page.locator('[data-testid="project-files-input"]').count()}")

        nofile_code = f"TPFNO-{int(asyncio.get_event_loop().time())%100000}"
        created_codes.append(nofile_code)
        await page.fill('[data-testid="name-input"]', f"TEST_ProjectFiles_NOFILE_{nofile_code}")
        await page.fill('[data-testid="code-input"]', nofile_code)
        await page.click('[data-testid="save-project-button"]', force=True)
        await page.wait_for_timeout(2600)
        await page.wait_for_selector(f'[data-testid="project-row-{nofile_code}"]', timeout=15000)
        print("Create without files from Dashboard succeeded")

        await page.click(f'[data-testid="project-row-{nofile_code}"]', force=True)
        await page.wait_for_timeout(1800)
        m3 = re.search(r'/projects/([^/?]+)', page.url)
        if m3:
            created_project_ids.append(m3.group(1))

        print("Step 8: Responsive checks")
        for w in [390, 320]:
            await page.set_viewport_size({"width": w, "height": 844})
            await ensure_projects_page()
            await page.click('[data-testid="new-project-button"]', force=True)
            await page.wait_for_selector('[data-testid="form-modal"]', timeout=10000)
            await page.fill('[data-testid="name-input"]', f"RESP-{w}")
            await page.fill('[data-testid="code-input"]', f"R{w}{int(asyncio.get_event_loop().time())%1000}")
            await page.locator('[data-testid="save-project-button"]').scroll_into_view_if_needed()
            visible = await page.locator('[data-testid="save-project-button"]').is_visible()
            modal_box = await page.locator('[data-testid="form-modal"]').bounding_box()
            print(f"Viewport {w}: save visible={visible}, modal width={modal_box['width'] if modal_box else 'n/a'}")
            await page.click('[data-testid="close-modal-button"]', force=True)
            await page.wait_for_timeout(400)

        await page.set_viewport_size({"width": 1440, "height": 1080})
        await page.screenshot(path='/app/test_reports/ui/iteration_10/automation_output/20261027_201932_98f8ce0b00d8/final_feature_state.jpeg', type="jpeg", quality=40, full_page=False)

        error_text = await page.evaluate("""() => {
    const errorElements = Array.from(document.querySelectorAll('.error, [class*=\"error\"], [id*=\"error\"]'));
    return errorElements.map(el => el.textContent).join(", ");
    }""")
        if error_text:
            print(f"Found error message: {error_text}")
        else:
            print("No error messages found on the page")

    except Exception as e:
        print(f"E2E test flow failed: {str(e)}")

    finally:
        print(f"Cleanup started for project IDs: {created_project_ids}")
        page.on("dialog", lambda dialog: asyncio.create_task(dialog.accept()))
        for pid in created_project_ids:
            try:
                await page.goto(f'https://project-pulse-641.preview.emergentagent.com/projects/{pid}')
                await page.wait_for_selector('[data-testid="delete-project-button"]', timeout=12000)
                await page.click('[data-testid="delete-project-button"]', force=True)
                await page.wait_for_timeout(1200)
                print(f"Cleanup attempted for project {pid}")
            except Exception as ce:
                print(f"Cleanup warning for project {pid}: {ce}")
        await page.goto('https://project-pulse-641.preview.emergentagent.com/projects')
        await page.wait_for_timeout(1200)
        print("UI feature test run completed")
