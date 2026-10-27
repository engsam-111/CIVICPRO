async def run_test(page, output_dir, page_url):
    import asyncio

    try:
        manager_email = "qa.manager+clerk_test@civicpro.dev"
        manager_password = "CivicPro#Mgr2026"
        created_project_name = "TEST_MOBILE Project"
        created_project_code = "TEST-MOB-01"

        await page.set_viewport_size({"width": 390, "height": 844})
        page.on("console", lambda msg: print(f"CONSOLE: {msg.text}"))
        print("A1 viewport set")

        await page.wait_for_selector('[data-testid="auth-email-input"]', timeout=15000)
        await page.fill('[data-testid="auth-email-input"]', manager_email)
        await page.fill('[data-testid="auth-password-input"]', "WrongPassword123")
        await page.click('[data-testid="sign-in-submit-button"]', force=True)
        await page.wait_for_timeout(1500)
        wrong_err = await page.locator('[data-testid="auth-error"]').count()
        print(f"A2 wrong-password-error-visible={wrong_err > 0}")

        await page.fill('[data-testid="auth-email-input"]', manager_email)
        await page.fill('[data-testid="auth-password-input"]', manager_password)
        await page.click('[data-testid="sign-in-submit-button"]', force=True)
        await page.wait_for_timeout(2600)
        if await page.locator('[data-testid="auth-code-input"]').count() > 0:
            await page.fill('[data-testid="auth-code-input"]', "424242")
            await page.click('[data-testid="auth-verify-button"]', force=True)
            await page.wait_for_timeout(2600)

        await page.wait_for_selector('[data-testid="mobile-navigation"]', timeout=20000)
        print("A3 manager login success")

        await page.goto('https://project-pulse-641.preview.emergentagent.com/sign-in')
        await page.wait_for_timeout(1500)
        print(f"A4 signed-in redirect away from sign-in={('/sign-in' not in page.url)}")

        widths = [320, 390, 768, 1024, 1440]
        routes = ["/", "/projects", "/reports", "/issues", "/more"]
        for w in widths:
            await page.set_viewport_size({"width": w, "height": 844 if w < 900 else 900})
            for r in routes:
                await page.goto(f'https://project-pulse-641.preview.emergentagent.com{r}')
                await page.wait_for_timeout(900)
                m = await page.evaluate("""() => ({ sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth, bsw: document.body.scrollWidth, iw: window.innerWidth })""")
                overflow = m["sw"] > m["cw"] + 1 or m["bsw"] > m["iw"] + 1
                print(f"A5 overflow width={w} route={r} -> {overflow}")

        await page.set_viewport_size({"width": 390, "height": 844})
        await page.goto('https://project-pulse-641.preview.emergentagent.com/')
        await page.wait_for_selector('[data-testid="mobile-navigation"]', timeout=10000)
        for nav in ["home", "projects", "reports", "issues", "more"]:
            c = await page.locator(f'[data-testid="mobile-nav-{nav}"]').count()
            print(f"A6 mobile-nav-{nav}-present={c>0}")

        await page.goto('https://project-pulse-641.preview.emergentagent.com/more')
        await page.wait_for_selector('[data-testid="workspace-account"]', timeout=10000)
        has_ai = await page.locator('[data-testid="more-assistant-link"]').count() > 0
        has_team = await page.locator('[data-testid="more-team-link"]').count() > 0
        print(f"A7 manager-more-links ai={has_ai} team={has_team}")

        await page.goto('https://project-pulse-641.preview.emergentagent.com/projects')
        await page.wait_for_selector('[data-testid="new-project-button"]', timeout=10000)
        await page.click('[data-testid="new-project-button"]', force=True)
        await page.wait_for_selector('[data-testid="form-modal"]', timeout=10000)
        await page.fill('[data-testid="name-input"]', created_project_name)
        await page.fill('[data-testid="code-input"]', created_project_code)
        await page.fill('[data-testid="location-input"]', "QA mobile site")
        await page.fill('[data-testid="client-input"]', "QA client")
        await page.fill('[data-testid="progress-input"]', "15")
        await page.click('[data-testid="save-project-button"]', force=True)
        await page.wait_for_timeout(2200)
        await page.get_by_text(created_project_name, exact=False).first.click(force=True)
        await page.wait_for_selector('[data-testid="project-hero"]', timeout=10000)
        print("A8 created/opened test project")

        await page.click('[data-testid="tab-activities"]', force=True)
        await page.click('[data-testid="add-activity-button"]', force=True)
        await page.wait_for_selector('[data-testid="form-modal"]', timeout=10000)
        await page.fill('[data-testid="name-input"]', "TEST_MOBILE Activity")
        await page.fill('[data-testid="owner-input"]', "QA Owner")
        await page.fill('[data-testid="weight-input"]', "1")
        await page.fill('[data-testid="progress-input"]', "20")
        await page.fill('[data-testid="due_date-input"]', "2026-12-31")
        await page.click('[data-testid="save-activity-button"]', force=True)
        await page.wait_for_timeout(1800)
        if await page.locator('[data-testid^="activity-progress-input-"]').count() > 0:
            p = page.locator('[data-testid^="activity-progress-input-"]').first
            await p.fill("45")
            await p.blur()
            await page.wait_for_timeout(700)
        if await page.locator('[data-testid^="activity-status-"]').count() > 0:
            await page.locator('[data-testid^="activity-status-"]').first.select_option("Completed")
            await page.wait_for_timeout(700)
        print("A9 activity add/update done")

        await page.click('[data-testid="tab-reports"]', force=True)
        await page.wait_for_timeout(400)
        await page.click('[data-testid="add-report-button"]', force=True)
        await page.wait_for_selector('[data-testid="form-modal"]', timeout=10000)
        await page.fill('[data-testid="title-input"]', "TEST_MOBILE Report")
        await page.fill('[data-testid="summary-input"]', "Mobile report summary")
        await page.fill('[data-testid="next_steps-input"]', "Mobile next steps")
        await page.fill('[data-testid="workforce-input"]', "4")
        await page.fill('[data-testid="progress-input"]', "55")
        await page.set_input_files('[data-testid="form-attachments-input"]', [
            {"name": "mobile_image.png", "mimeType": "image/png", "buffer": b"\x89PNG\r\n\x1a\n" + b"B" * 128},
            {"name": "mobile_note.txt", "mimeType": "text/plain", "buffer": b"mobile note"}
        ])
        await page.click('[data-testid="save-report-button"]', force=True)
        await page.wait_for_timeout(2500)
        rt = page.locator('[data-testid^="report-"][data-testid$="-toggle"]').first
        if await rt.count() > 0:
            await rt.click(force=True)
            await page.wait_for_timeout(600)
        print("A10 report add/expand done")

        await page.click('[data-testid="tab-issues"]', force=True)
        await page.wait_for_timeout(400)
        await page.click('[data-testid="add-issue-button"]', force=True)
        await page.wait_for_selector('[data-testid="form-modal"]', timeout=10000)
        await page.fill('[data-testid="title-input"]', "TEST_MOBILE Issue")
        await page.select_option('[data-testid="issue-category-select"]', "Issue")
        await page.select_option('[data-testid="issue-severity-select"]', "High")
        await page.fill('[data-testid="due_date-input"]', "2026-12-31")
        await page.fill('[data-testid="description-input"]', "Mobile issue details")
        await page.set_input_files('[data-testid="form-attachments-input"]', [{"name": "issue_note.txt", "mimeType": "text/plain", "buffer": b"issue note"}])
        await page.click('[data-testid="save-issue-button"]', force=True)
        await page.wait_for_timeout(2500)
        it = page.locator('[data-testid^="issue-"][data-testid$="-toggle"]').first
        if await it.count() > 0:
            await it.click(force=True)
        if await page.locator('[data-testid^="issue-status-"]').count() > 0:
            await page.locator('[data-testid^="issue-status-"]').first.select_option("Resolved")
            await page.wait_for_timeout(1000)
        print("A11 issue add/update done")

        await page.click('[data-testid="export-menu-button"]', force=True)
        await page.wait_for_selector('[data-testid="export-menu"]', timeout=7000)
        try:
            async with page.expect_download(timeout=15000) as d1:
                await page.click('[data-testid="export-full-pdf-button"]', force=True)
            pdf = await d1.value
            print(f"A12 pdf download started={pdf.suggested_filename}")
        except Exception as e:
            print(f"A12 pdf download failed: {e}")

        await page.click('[data-testid="export-menu-button"]', force=True)
        await page.wait_for_selector('[data-testid="export-menu"]', timeout=7000)
        try:
            async with page.expect_download(timeout=15000) as d2:
                await page.click('[data-testid="export-excel-button"]', force=True)
            xlsx = await d2.value
            print(f"A13 xlsx download started={xlsx.suggested_filename}")
        except Exception as e:
            print(f"A13 xlsx download failed: {e}")

        await page.goto('https://project-pulse-641.preview.emergentagent.com/assistant')
        await page.wait_for_selector('[data-testid="chat-input"]', timeout=12000)
        await page.fill('[data-testid="chat-input"]', "Give one short portfolio status line.")
        await page.click('[data-testid="chat-send-button"]', force=True)
        await page.wait_for_timeout(9000)
        await page.fill('[data-testid="chat-input"]', "Now one follow-up action.")
        await page.click('[data-testid="chat-send-button"]', force=True)
        await page.wait_for_timeout(9000)
        sess = await page.locator('[data-testid^="chat-session-"]').count()
        msgs = await page.locator('[data-testid^="chat-message-"]').count()
        print(f"A14 ai chat done sessions={sess} messages={msgs}")
        if await page.locator('[data-testid^="delete-chat-"]').count() > 0:
            await page.locator('[data-testid^="delete-chat-"]').first.click(force=True)
            await page.wait_for_timeout(1000)
            print("A15 ai chat cleanup attempted")

        # cleanup created project quickly via project detail delete
        await page.goto('https://project-pulse-641.preview.emergentagent.com/projects')
        await page.wait_for_timeout(1200)
        if await page.get_by_text(created_project_name, exact=False).count() > 0:
            await page.get_by_text(created_project_name, exact=False).first.click(force=True)
            await page.wait_for_timeout(1000)
            page.once("dialog", lambda dialog: asyncio.create_task(dialog.accept()))
            await page.click('[data-testid="delete-project-button"]', force=True)
            await page.wait_for_timeout(2000)
            print("A16 test project delete attempted")
        else:
            print("A16 no test project found for delete")

        await page.goto('https://project-pulse-641.preview.emergentagent.com/more')
        await page.wait_for_selector('[data-testid="install-panel"]', timeout=10000)
        await page.screenshot(path="/app/test_reports/ui/iteration_9/automation_output/20261027_193406_1f3131f88715/mobile_more_390.jpeg", type="jpeg", quality=40, full_page=False)
        print("A17 mobile screenshot captured")

        error_text = await page.evaluate("""() => {
        const errorElements = Array.from(document.querySelectorAll('.error, [class*="error"], [id*="error"]'));
        return errorElements.map(el => el.textContent).join(", ");
        }""")
        if error_text:
            print(f"Found error message: {error_text}")
        else:
            print("No error messages found on the page")

    except Exception as e:
        print(f"UI flow A failed: {str(e)}")
