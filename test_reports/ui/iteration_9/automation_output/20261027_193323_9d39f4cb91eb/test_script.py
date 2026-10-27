async def run_test(page, output_dir, page_url):
    try:
        manager_email = "qa.manager+clerk_test@civicpro.dev"
        manager_password = "CivicPro#Mgr2026"
        engineer_email = "qa.engineer+clerk_test@civicpro.dev"
        engineer_password_old = "CivicPro#Test2026"
        engineer_password_new = "CivicPro#Tmp2026!"
        pending_email = "qa.newbie+clerk_test@civicpro.dev"
        pending_password = "CivicPro#New2026"

        created_project_name = "TEST_MOBILE Project"
        created_project_code = "TEST-MOB-01"
        created_activity_name = "TEST_MOBILE Activity"
        created_report_title = "TEST_MOBILE Report"
        created_issue_title = "TEST_MOBILE Issue"

        page.on("console", lambda msg: print(f"CONSOLE: {msg.type}: {msg.text}"))
        await page.set_viewport_size({"width": 390, "height": 844})
        print("Step 1: Mobile viewport set")

        # Wrong password path
        await page.wait_for_selector('[data-testid="auth-email-input"]', timeout=15000)
        await page.fill('[data-testid="auth-email-input"]', manager_email)
        await page.fill('[data-testid="auth-password-input"]', "WrongPassword123")
        await page.click('[data-testid="sign-in-submit-button"]', force=True)
        await page.wait_for_timeout(1200)
        if await page.locator('[data-testid="auth-error"]').count() > 0:
            err = await page.locator('[data-testid="auth-error"]').first.text_content()
            print(f"Step 2: Wrong password error shown: {err}")
        else:
            print("Step 2: Wrong password error not found")

        # Valid login manager
        await page.fill('[data-testid="auth-email-input"]', manager_email)
        await page.fill('[data-testid="auth-password-input"]', manager_password)
        await page.click('[data-testid="sign-in-submit-button"]', force=True)
        await page.wait_for_timeout(2000)

        # Optional code challenge
        if await page.locator('[data-testid="auth-code-input"]').count() > 0:
            await page.fill('[data-testid="auth-code-input"]', "424242")
            await page.click('[data-testid="auth-verify-button"]', force=True)
            await page.wait_for_timeout(2500)

        await page.wait_for_selector('[data-testid="mobile-navigation"]', timeout=20000)
        print("Step 3: Manager login success and dashboard loaded")
        await page.screenshot(path="/app/test_reports/ui/iteration_9/automation_output/20261027_193323_9d39f4cb91eb/mobile_dashboard_390.jpeg", type="jpeg", quality=40, full_page=False)

        # Signed-in redirect check from /sign-in
        await page.goto('https://project-pulse-641.preview.emergentagent.com/sign-in')
        await page.wait_for_timeout(1500)
        if '/sign-in' in page.url:
            print(f"Step 4: Redirect check failed, still on {page.url}")
        else:
            print(f"Step 4: Signed-in redirect working -> {page.url}")

        # Responsive overflow checks
        widths = [320, 390, 768, 1024, 1440]
        routes = ["/", "/projects", "/reports", "/issues", "/more"]
        for w in widths:
            await page.set_viewport_size({"width": w, "height": 844 if w < 900 else 900})
            await page.wait_for_timeout(300)
            for r in routes:
                await page.goto(f'https://project-pulse-641.preview.emergentagent.com{r}')
                await page.wait_for_timeout(1200)
                metrics = await page.evaluate("""() => ({
                    sw: document.documentElement.scrollWidth,
                    cw: document.documentElement.clientWidth,
                    bodySw: document.body ? document.body.scrollWidth : 0,
                    innerW: window.innerWidth
                })""")
                overflow = metrics["sw"] > metrics["cw"] + 1 or metrics["bodySw"] > metrics["innerW"] + 1
                print(f"Step 5: width={w}, route={r}, overflow={overflow}, metrics={metrics}")

        # Mobile nav checks
        await page.set_viewport_size({"width": 390, "height": 844})
        await page.goto('https://project-pulse-641.preview.emergentagent.com/')
        await page.wait_for_selector('[data-testid="mobile-nav-home"]', timeout=10000)
        for nav in ["home", "projects", "reports", "issues", "more"]:
            sel = f'[data-testid="mobile-nav-{nav}"]'
            if await page.locator(sel).count() > 0:
                print(f"Step 6: Mobile nav present -> {nav}")
            else:
                print(f"Step 6: Mobile nav missing -> {nav}")

        # Create TEST_MOBILE project
        await page.goto('https://project-pulse-641.preview.emergentagent.com/projects')
        await page.wait_for_selector('[data-testid="new-project-button"]', timeout=10000)
        await page.click('[data-testid="new-project-button"]', force=True)
        await page.wait_for_selector('[data-testid="form-modal"]', timeout=10000)
        await page.fill('[data-testid="name-input"]', created_project_name)
        await page.fill('[data-testid="code-input"]', created_project_code)
        await page.fill('[data-testid="location-input"]', "QA mobile site")
        await page.fill('[data-testid="client-input"]', "QA Client")
        await page.fill('[data-testid="progress-input"]', "10")
        await page.click('[data-testid="save-project-button"]', force=True)
        await page.wait_for_timeout(2000)
        await page.click(f'text={created_project_name}', force=True)
        await page.wait_for_selector('[data-testid="project-hero"]', timeout=10000)
        print("Step 7: TEST_MOBILE project created and opened")

        # Add activity
        await page.click('[data-testid="tab-activities"]', force=True)
        await page.wait_for_timeout(400)
        await page.click('[data-testid="add-activity-button"]', force=True)
        await page.wait_for_selector('[data-testid="form-modal"]', timeout=10000)
        await page.fill('[data-testid="name-input"]', created_activity_name)
        await page.fill('[data-testid="owner-input"]', "QA Engineer")
        await page.fill('[data-testid="weight-input"]', "1")
        await page.fill('[data-testid="progress-input"]', "20")
        await page.fill('[data-testid="due_date-input"]', "2026-12-31")
        await page.click('[data-testid="save-activity-button"]', force=True)
        await page.wait_for_timeout(1800)
        print("Step 8: Activity created")

        # Update activity progress and status
        progress_input = page.locator('[data-testid^="activity-progress-input-"]').first
        if await progress_input.count() > 0:
            await progress_input.fill("45")
            await progress_input.blur()
            await page.wait_for_timeout(900)
        status_select = page.locator('[data-testid^="activity-status-"]').first
        if await status_select.count() > 0:
            await status_select.select_option("Completed")
            await page.wait_for_timeout(900)
        print("Step 9: Activity progress/status updated")

        # Add report with attachments
        await page.click('[data-testid="tab-reports"]', force=True)
        await page.wait_for_timeout(500)
        await page.click('[data-testid="add-report-button"]', force=True)
        await page.wait_for_selector('[data-testid="form-modal"]', timeout=10000)
        await page.fill('[data-testid="title-input"]', created_report_title)
        await page.fill('[data-testid="summary-input"]', "Work completed from mobile QA flow")
        await page.fill('[data-testid="next_steps-input"]', "Next mobile verification step")
        await page.fill('[data-testid="workforce-input"]', "5")
        await page.fill('[data-testid="progress-input"]', "50")
        await page.set_input_files('[data-testid="form-attachments-input"]', [
            {
                "name": "test_mobile.png",
                "mimeType": "image/png",
                "buffer": b"\x89PNG\r\n\x1a\n" + b"A" * 200
            },
            {
                "name": "test_mobile.txt",
                "mimeType": "text/plain",
                "buffer": b"mobile attachment text"
            }
        ])
        await page.click('[data-testid="save-report-button"]', force=True)
        await page.wait_for_timeout(2500)
        print("Step 10: Report with attachment created")

        # Expand report row
        report_toggle = page.locator('[data-testid^="report-"][data-testid$="-toggle"]').first
        if await report_toggle.count() > 0:
            await report_toggle.click(force=True)
            await page.wait_for_timeout(700)
            print("Step 11: Report row expanded")
        else:
            print("Step 11: Report toggle not found")

        # Add issue with attachments
        await page.click('[data-testid="tab-issues"]', force=True)
        await page.wait_for_timeout(500)
        await page.click('[data-testid="add-issue-button"]', force=True)
        await page.wait_for_selector('[data-testid="form-modal"]', timeout=10000)
        await page.fill('[data-testid="title-input"]', created_issue_title)
        await page.select_option('[data-testid="issue-category-select"]', "Issue")
        await page.select_option('[data-testid="issue-severity-select"]', "High")
        await page.fill('[data-testid="due_date-input"]', "2026-12-31")
        await page.fill('[data-testid="description-input"]', "Mobile issue flow validation")
        await page.set_input_files('[data-testid="form-attachments-input"]', [{
            "name": "test_issue.txt",
            "mimeType": "text/plain",
            "buffer": b"issue attachment"
        }])
        await page.click('[data-testid="save-issue-button"]', force=True)
        await page.wait_for_timeout(2500)
        print("Step 12: Issue with attachment created")

        # Expand issue and update status
        issue_toggle = page.locator('[data-testid^="issue-"][data-testid$="-toggle"]').first
        if await issue_toggle.count() > 0:
            await issue_toggle.click(force=True)
            await page.wait_for_timeout(700)
        issue_status = page.locator('[data-testid^="issue-status-"]').first
        if await issue_status.count() > 0:
            await issue_status.select_option("Resolved")
            await page.wait_for_timeout(1200)
        print("Step 13: Issue status updated")

        # Export PDF/XLSX
        await page.click('[data-testid="export-menu-button"]', force=True)
        await page.wait_for_selector('[data-testid="export-menu"]', timeout=6000)
        try:
            async with page.expect_download(timeout=15000) as d1:
                await page.click('[data-testid="export-full-pdf-button"]', force=True)
            dl1 = await d1.value
            print(f"Step 14: PDF export download started: {dl1.suggested_filename}")
        except Exception as e:
            print(f"Step 14: PDF download capture failed: {e}")

        await page.click('[data-testid="export-menu-button"]', force=True)
        await page.wait_for_selector('[data-testid="export-menu"]', timeout=6000)
        try:
            async with page.expect_download(timeout=15000) as d2:
                await page.click('[data-testid="export-excel-button"]', force=True)
            dl2 = await d2.value
            print(f"Step 15: XLSX export download started: {dl2.suggested_filename}")
        except Exception as e:
            print(f"Step 15: XLSX download capture failed: {e}")

        # More page links for manager
        await page.goto('https://project-pulse-641.preview.emergentagent.com/more')
        await page.wait_for_selector('[data-testid="workspace-account"]', timeout=10000)
        print(f"Step 16: Manager sees assistant link={await page.locator('[data-testid="more-assistant-link"]').count() > 0}, team link={await page.locator('[data-testid="more-team-link"]').count() > 0}")

        # Team reset password UI on phone
        await page.goto('https://project-pulse-641.preview.emergentagent.com/team')
        await page.wait_for_timeout(1500)
        reset_btn = page.locator('[data-testid="reset-password-user_3L9kur0VSQjT1w7CtIMJJu2w45c"]')
        if await reset_btn.count() > 0:
            await reset_btn.click(force=True)
            await page.wait_for_selector('[data-testid="new-password-input"]', timeout=10000)
            await page.fill('[data-testid="new-password-input"]', engineer_password_new)
            await page.click('[data-testid="save-password-button"]', force=True)
            await page.wait_for_timeout(2500)
            print("Step 17: Manager reset engineer password via Team UI")
        else:
            print("Step 17: Reset password button for engineer not found")

        # Check self/owner/manager reset restrictions by UI presence
        self_reset = await page.locator('[data-testid="reset-password-user_3L9leJprjujidpKUxS1z426Gv5L"]').count()
        owner_reset = await page.locator('[data-testid="reset-password-user_3L9lY32nl7VmhC0M9CP0BBmp9zm"]').count()
        print(f"Step 18: self reset button count={self_reset}, owner reset button count={owner_reset}")

        # Sign out manager
        await page.click('[data-testid="account-menu"]', force=True)
        await page.wait_for_timeout(800)
        if await page.get_by_text('Sign out').count() > 0:
            await page.get_by_text('Sign out').first.click(force=True)
        elif await page.get_by_text('Sign Out').count() > 0:
            await page.get_by_text('Sign Out').first.click(force=True)
        await page.wait_for_timeout(2500)
        print(f"Step 19: Manager sign-out attempted, url={page.url}")

        # Engineer old password should fail
        await page.goto('https://project-pulse-641.preview.emergentagent.com/sign-in')
        await page.wait_for_selector('[data-testid="auth-email-input"]', timeout=15000)
        await page.fill('[data-testid="auth-email-input"]', engineer_email)
        await page.fill('[data-testid="auth-password-input"]', engineer_password_old)
        await page.click('[data-testid="sign-in-submit-button"]', force=True)
        await page.wait_for_timeout(1500)
        old_rejected = await page.locator('[data-testid="auth-error"]').count() > 0
        print(f"Step 20: Engineer old password rejected={old_rejected}")

        # Engineer new password should work
        await page.fill('[data-testid="auth-email-input"]', engineer_email)
        await page.fill('[data-testid="auth-password-input"]', engineer_password_new)
        await page.click('[data-testid="sign-in-submit-button"]', force=True)
        await page.wait_for_timeout(2500)
        if await page.locator('[data-testid="auth-code-input"]').count() > 0:
            await page.fill('[data-testid="auth-code-input"]', "424242")
            await page.click('[data-testid="auth-verify-button"]', force=True)
            await page.wait_for_timeout(2500)
        eng_signed = await page.locator('[data-testid="mobile-navigation"]').count() > 0
        print(f"Step 21: Engineer login with new password success={eng_signed}")

        # Engineer should not access Team / no Team link in More
        await page.goto('https://project-pulse-641.preview.emergentagent.com/more')
        await page.wait_for_timeout(1200)
        eng_team_link = await page.locator('[data-testid="more-team-link"]').count() > 0
        await page.goto('https://project-pulse-641.preview.emergentagent.com/team')
        await page.wait_for_timeout(1200)
        print(f"Step 22: Engineer team link visible={eng_team_link}, team-url-after-open={page.url}")

        # Sign out engineer
        await page.click('[data-testid="account-menu"]', force=True)
        await page.wait_for_timeout(800)
        if await page.get_by_text('Sign out').count() > 0:
            await page.get_by_text('Sign out').first.click(force=True)
        elif await page.get_by_text('Sign Out').count() > 0:
            await page.get_by_text('Sign Out').first.click(force=True)
        await page.wait_for_timeout(2200)
        print("Step 23: Engineer sign-out attempted")

        # Login manager again and restore original engineer password
        await page.goto('https://project-pulse-641.preview.emergentagent.com/sign-in')
        await page.wait_for_selector('[data-testid="auth-email-input"]', timeout=15000)
        await page.fill('[data-testid="auth-email-input"]', manager_email)
        await page.fill('[data-testid="auth-password-input"]', manager_password)
        await page.click('[data-testid="sign-in-submit-button"]', force=True)
        await page.wait_for_timeout(2500)
        if await page.locator('[data-testid="auth-code-input"]').count() > 0:
            await page.fill('[data-testid="auth-code-input"]', "424242")
            await page.click('[data-testid="auth-verify-button"]', force=True)
            await page.wait_for_timeout(2500)

        await page.goto('https://project-pulse-641.preview.emergentagent.com/team')
        await page.wait_for_timeout(1400)
        reset_btn2 = page.locator('[data-testid="reset-password-user_3L9kur0VSQjT1w7CtIMJJu2w45c"]')
        if await reset_btn2.count() > 0:
            await reset_btn2.click(force=True)
            await page.wait_for_selector('[data-testid="new-password-input"]', timeout=10000)
            await page.fill('[data-testid="new-password-input"]', engineer_password_old)
            await page.click('[data-testid="save-password-button"]', force=True)
            await page.wait_for_timeout(2200)
            print("Step 24: Engineer password restored to original")
        else:
            print("Step 24: Could not restore engineer password via UI")

        # Pending user gate
        await page.click('[data-testid="account-menu"]', force=True)
        await page.wait_for_timeout(700)
        if await page.get_by_text('Sign out').count() > 0:
            await page.get_by_text('Sign out').first.click(force=True)
        elif await page.get_by_text('Sign Out').count() > 0:
            await page.get_by_text('Sign Out').first.click(force=True)
        await page.wait_for_timeout(2000)

        await page.goto('https://project-pulse-641.preview.emergentagent.com/sign-in')
        await page.fill('[data-testid="auth-email-input"]', pending_email)
        await page.fill('[data-testid="auth-password-input"]', pending_password)
        await page.click('[data-testid="sign-in-submit-button"]', force=True)
        await page.wait_for_timeout(2500)
        if await page.locator('[data-testid="auth-code-input"]').count() > 0:
            await page.fill('[data-testid="auth-code-input"]', "424242")
            await page.click('[data-testid="auth-verify-button"]', force=True)
            await page.wait_for_timeout(2500)
        pending_gate = await page.locator('[data-testid="pending-approval"]').count() > 0
        print(f"Step 25: Pending user gated screen visible={pending_gate}")

        # Sign back as manager for AI and cleanup
        await page.click('[data-testid="account-menu"]', force=True)
        await page.wait_for_timeout(700)
        if await page.get_by_text('Sign out').count() > 0:
            await page.get_by_text('Sign out').first.click(force=True)
        elif await page.get_by_text('Sign Out').count() > 0:
            await page.get_by_text('Sign Out').first.click(force=True)
        await page.wait_for_timeout(1800)

        await page.goto('https://project-pulse-641.preview.emergentagent.com/sign-in')
        await page.fill('[data-testid="auth-email-input"]', manager_email)
        await page.fill('[data-testid="auth-password-input"]', manager_password)
        await page.click('[data-testid="sign-in-submit-button"]', force=True)
        await page.wait_for_timeout(2400)
        if await page.locator('[data-testid="auth-code-input"]').count() > 0:
            await page.fill('[data-testid="auth-code-input"]', "424242")
            await page.click('[data-testid="auth-verify-button"]', force=True)
            await page.wait_for_timeout(2400)

        await page.goto('https://project-pulse-641.preview.emergentagent.com/assistant')
        await page.wait_for_selector('[data-testid="chat-input"]', timeout=12000)
        await page.fill('[data-testid="chat-input"]', "Give one short status line for the portfolio.")
        await page.click('[data-testid="chat-send-button"]', force=True)
        await page.wait_for_timeout(9000)
        await page.fill('[data-testid="chat-input"]', "Now give one follow-up action.")
        await page.click('[data-testid="chat-send-button"]', force=True)
        await page.wait_for_timeout(9000)
        print("Step 26: AI two-message flow executed")

        # Delete created chat session if exists
        del_btn = page.locator('[data-testid^="delete-chat-"]').first
        if await del_btn.count() > 0:
            await del_btn.click(force=True)
            await page.wait_for_timeout(1200)
            print("Step 27: Test AI chat session deleted")

        # Cleanup created issue/report/activity/project from project detail
        await page.goto('https://project-pulse-641.preview.emergentagent.com/projects')
        await page.wait_for_timeout(1200)
        if await page.get_by_text(created_project_name).count() > 0:
            await page.get_by_text(created_project_name).first.click(force=True)
            await page.wait_for_timeout(1200)

            await page.click('[data-testid="tab-issues"]', force=True)
            await page.wait_for_timeout(500)
            del_issue = page.locator('[data-testid^="delete-issue-"]').first
            if await del_issue.count() > 0:
                page.once("dialog", lambda d: asyncio.create_task(d.accept()))
                await del_issue.click(force=True)
                await page.wait_for_timeout(1000)

            await page.click('[data-testid="tab-reports"]', force=True)
            await page.wait_for_timeout(500)
            del_report = page.locator('[data-testid^="delete-report-"]').first
            if await del_report.count() > 0:
                page.once("dialog", lambda d: asyncio.create_task(d.accept()))
                await del_report.click(force=True)
                await page.wait_for_timeout(1000)

            await page.click('[data-testid="tab-activities"]', force=True)
            await page.wait_for_timeout(500)
            del_activity = page.locator('[data-testid^="delete-activity-"]').first
            if await del_activity.count() > 0:
                page.once("dialog", lambda d: asyncio.create_task(d.accept()))
                await del_activity.click(force=True)
                await page.wait_for_timeout(1000)

            page.once("dialog", lambda d: asyncio.create_task(d.accept()))
            await page.click('[data-testid="delete-project-button"]', force=True)
            await page.wait_for_timeout(1800)
            print("Step 28: Cleanup for TEST_MOBILE entities attempted")
        else:
            print("Step 28: TEST_MOBILE project not found for cleanup")

        # Error scraping block
        error_text = await page.evaluate("""() => {
        const errorElements = Array.from(document.querySelectorAll('.error, [class*="error"], [id*="error"]'));
        return errorElements.map(el => el.textContent).join(", ");
        }""")
        if error_text:
            print(f"Found error message: {error_text}")
        else:
            print("No error messages found on the page")

        await page.screenshot(path="/app/test_reports/ui/iteration_9/automation_output/20261027_193323_9d39f4cb91eb/mobile_final_state.jpeg", type="jpeg", quality=40, full_page=False)
        print("UI integration run completed")

    except Exception as e:
        print(f"UI integration test failed: {str(e)}")
