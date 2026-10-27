async def run_test(page, output_dir, page_url):
    try:
        manager_email = "qa.manager+clerk_test@civicpro.dev"
        manager_password = "CivicPro#Mgr2026"
        engineer_email = "qa.engineer+clerk_test@civicpro.dev"
        engineer_password_old = "CivicPro#Test2026"
        engineer_password_new = "CivicPro#Tmp2026!"
        pending_email = "qa.newbie+clerk_test@civicpro.dev"
        pending_password = "CivicPro#New2026"

        await page.set_viewport_size({"width": 390, "height": 844})
        print("B1 viewport set")

        async def sign_out_if_possible():
            if await page.locator('[data-testid="account-menu"]').count() > 0:
                await page.click('[data-testid="account-menu"]', force=True)
                await page.wait_for_timeout(700)
                if await page.get_by_text('Sign out').count() > 0:
                    await page.get_by_text('Sign out').first.click(force=True)
                    await page.wait_for_timeout(1600)
                elif await page.get_by_text('Sign Out').count() > 0:
                    await page.get_by_text('Sign Out').first.click(force=True)
                    await page.wait_for_timeout(1600)

        async def login(email, password):
            await page.goto('https://project-pulse-641.preview.emergentagent.com/sign-in')
            await page.wait_for_selector('[data-testid="auth-email-input"]', timeout=15000)
            await page.fill('[data-testid="auth-email-input"]', email)
            await page.fill('[data-testid="auth-password-input"]', password)
            await page.click('[data-testid="sign-in-submit-button"]', force=True)
            await page.wait_for_timeout(2200)
            if await page.locator('[data-testid="auth-code-input"]').count() > 0:
                await page.fill('[data-testid="auth-code-input"]', "424242")
                await page.click('[data-testid="auth-verify-button"]', force=True)
                await page.wait_for_timeout(2200)

        await login(manager_email, manager_password)
        await page.goto('https://project-pulse-641.preview.emergentagent.com/team')
        await page.wait_for_timeout(1400)

        # Team reset restrictions visible in UI
        self_reset = await page.locator('[data-testid="reset-password-user_3L9leJprjujidpKUxS1z426Gv5L"]').count()
        owner_reset = await page.locator('[data-testid="reset-password-user_3L9lY32nl7VmhC0M9CP0BBmp9zm"]').count()
        engineer_reset = await page.locator('[data-testid="reset-password-user_3L9kur0VSQjT1w7CtIMJJu2w45c"]').count()
        print(f"B2 manager team reset buttons self={self_reset} owner={owner_reset} engineer={engineer_reset}")

        # Short password should be blocked by disabled button
        if engineer_reset > 0:
            await page.click('[data-testid="reset-password-user_3L9kur0VSQjT1w7CtIMJJu2w45c"]', force=True)
            await page.wait_for_selector('[data-testid="new-password-input"]', timeout=10000)
            await page.fill('[data-testid="new-password-input"]', "short")
            short_disabled = await page.locator('[data-testid="save-password-button"]').is_disabled()
            print(f"B3 short password button disabled={short_disabled}")
            await page.click('[data-testid="close-modal-button"]', force=True)
            await page.wait_for_timeout(400)

        # Set temporary engineer password
        await page.click('[data-testid="reset-password-user_3L9kur0VSQjT1w7CtIMJJu2w45c"]', force=True)
        await page.wait_for_selector('[data-testid="new-password-input"]', timeout=10000)
        await page.fill('[data-testid="new-password-input"]', engineer_password_new)
        await page.click('[data-testid="save-password-button"]', force=True)
        await page.wait_for_timeout(2200)
        print("B4 manager reset engineer password")

        await sign_out_if_possible()

        # Engineer old password rejected
        await page.goto('https://project-pulse-641.preview.emergentagent.com/sign-in')
        await page.wait_for_selector('[data-testid="auth-email-input"]', timeout=15000)
        await page.fill('[data-testid="auth-email-input"]', engineer_email)
        await page.fill('[data-testid="auth-password-input"]', engineer_password_old)
        await page.click('[data-testid="sign-in-submit-button"]', force=True)
        await page.wait_for_timeout(1500)
        old_err = await page.locator('[data-testid="auth-error"]').count() > 0
        print(f"B5 engineer old password rejected={old_err}")

        # Engineer new password works
        await page.fill('[data-testid="auth-email-input"]', engineer_email)
        await page.fill('[data-testid="auth-password-input"]', engineer_password_new)
        await page.click('[data-testid="sign-in-submit-button"]', force=True)
        await page.wait_for_timeout(2400)
        if await page.locator('[data-testid="auth-code-input"]').count() > 0:
            await page.fill('[data-testid="auth-code-input"]', "424242")
            await page.click('[data-testid="auth-verify-button"]', force=True)
            await page.wait_for_timeout(2200)
        eng_nav = await page.locator('[data-testid="mobile-navigation"]').count() > 0
        print(f"B6 engineer login with new password success={eng_nav}")

        await page.goto('https://project-pulse-641.preview.emergentagent.com/more')
        await page.wait_for_timeout(1200)
        engineer_team_link = await page.locator('[data-testid="more-team-link"]').count() > 0
        await page.goto('https://project-pulse-641.preview.emergentagent.com/team')
        await page.wait_for_timeout(1200)
        redirected_from_team = '/team' not in page.url
        print(f"B7 engineer access checks team-link={engineer_team_link} redirected={redirected_from_team}")

        await sign_out_if_possible()

        # Pending user gate
        await login(pending_email, pending_password)
        pending_gate = await page.locator('[data-testid="pending-approval"]').count() > 0
        print(f"B8 pending user gate visible={pending_gate}")

        await sign_out_if_possible()

        # Restore engineer original password
        await login(manager_email, manager_password)
        await page.goto('https://project-pulse-641.preview.emergentagent.com/team')
        await page.wait_for_timeout(1400)
        await page.click('[data-testid="reset-password-user_3L9kur0VSQjT1w7CtIMJJu2w45c"]', force=True)
        await page.wait_for_selector('[data-testid="new-password-input"]', timeout=10000)
        await page.fill('[data-testid="new-password-input"]', engineer_password_old)
        await page.click('[data-testid="save-password-button"]', force=True)
        await page.wait_for_timeout(2200)
        print("B9 engineer password restored")

        error_text = await page.evaluate("""() => {
        const errorElements = Array.from(document.querySelectorAll('.error, [class*="error"], [id*="error"]'));
        return errorElements.map(el => el.textContent).join(", ");
        }""")
        if error_text:
            print(f"Found error message: {error_text}")
        else:
            print("No error messages found on the page")

    except Exception as e:
        print(f"UI flow B failed: {str(e)}")
