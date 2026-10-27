async def run_test(page, output_dir, page_url):
    try:
        await page.set_viewport_size({"width": 390, "height": 844})

        # Manifest and icon checks
        manifest = await page.evaluate("""async () => {
          const r = await fetch('/manifest.json', {cache:'no-store'});
          const j = await r.json();
          return {status:r.status, json:j};
        }""")
        m = manifest['json']
        print(f"D1 manifest status={manifest['status']} start={m.get('start_url')} scope={m.get('scope')} display={m.get('display')}")

        icon_checks = await page.evaluate("""async () => {
          const paths = ['/icons/icon-192.png','/icons/icon-512.png','/icons/maskable-512.png','/icons/apple-touch-icon.png'];
          const out = [];
          for (const p of paths) {
            const r = await fetch(p, {cache:'no-store'});
            out.push({path:p, status:r.status, type:r.headers.get('content-type')});
          }
          return out;
        }""")
        print(f"D2 icon checks={icon_checks}")

        # Service worker registration + active control
        sw_info = await page.evaluate("""async () => {
          await new Promise(r => setTimeout(r, 800));
          const regs = await navigator.serviceWorker.getRegistrations();
          return regs.map(x => ({scope:x.scope, active:!!x.active, script:x.active?.scriptURL || x.installing?.scriptURL || ''}));
        }""")
        print(f"D3 service worker registrations={sw_info}")

        # Simulate beforeinstallprompt and appinstalled (emulated)
        sim = await page.evaluate("""() => {
          const ev = new Event('beforeinstallprompt');
          ev.prompt = () => Promise.resolve();
          ev.userChoice = Promise.resolve({outcome:'accepted', platform:'web'});
          window.dispatchEvent(ev);
          window.dispatchEvent(new Event('appinstalled'));
          return {emulated:true};
        }""")
        print(f"D4 install events emulated={sim['emulated']}")

        # Login manager for offline banner and save-failure checks
        await page.fill('[data-testid="auth-email-input"]', 'qa.manager+clerk_test@civicpro.dev')
        await page.fill('[data-testid="auth-password-input"]', 'CivicPro#Mgr2026')
        await page.click('[data-testid="sign-in-submit-button"]', force=True)
        await page.wait_for_timeout(2400)
        if await page.locator('[data-testid="auth-code-input"]').count() > 0:
            await page.fill('[data-testid="auth-code-input"]', '424242')
            await page.click('[data-testid="auth-verify-button"]', force=True)
            await page.wait_for_timeout(2200)
        await page.wait_for_selector('[data-testid="mobile-navigation"]', timeout=20000)

        # Ensure page is under SW control after navigation
        await page.goto('https://project-pulse-641.preview.emergentagent.com/more')
        await page.wait_for_timeout(1200)
        controller = await page.evaluate("""() => !!navigator.serviceWorker.controller""")
        print(f"D5 service worker controller active={controller}")

        # CacheStorage safety check
        cache_contents = await page.evaluate("""async () => {
          const keys = await caches.keys();
          const map = {};
          for (const k of keys) {
            const c = await caches.open(k);
            const reqs = await c.keys();
            map[k] = reqs.map(r => new URL(r.url).pathname);
          }
          return map;
        }""")
        print(f"D6 cache contents={cache_contents}")

        # Go offline and check runtime banner + save behavior
        await page.context.set_offline(True)
        await page.goto('https://project-pulse-641.preview.emergentagent.com/projects')
        await page.wait_for_timeout(1800)
        offline_banner = await page.locator('[data-testid="offline-banner"]').count() > 0
        print(f"D7 offline banner visible={offline_banner}")

        # Attempt save while offline (should fail honestly)
        if await page.locator('[data-testid="new-project-button"]').count() > 0:
            await page.click('[data-testid="new-project-button"]', force=True)
            await page.wait_for_selector('[data-testid="form-modal"]', timeout=10000)
            await page.fill('[data-testid="name-input"]', 'TEST_MOBILE_OFFLINE')
            await page.fill('[data-testid="code-input"]', 'OFF-MOB')
            await page.click('[data-testid="save-project-button"]', force=True)
            await page.wait_for_timeout(1500)
            still_open = await page.locator('[data-testid="form-modal"]').count() > 0
            print(f"D8 offline save blocked (modal still open)={still_open}")
            if still_open and await page.locator('[data-testid="close-modal-button"]').count() > 0:
                await page.click('[data-testid="close-modal-button"]', force=True)

        # Offline fallback route check
        await page.goto('https://project-pulse-641.preview.emergentagent.com/nonexistent-offline-route')
        await page.wait_for_timeout(1500)
        offline_page = await page.locator('[data-testid="offline-page"]').count() > 0
        print(f"D9 offline fallback page visible={offline_page}")

        # Reconnect and verify banner clears/refetch path
        await page.context.set_offline(False)
        await page.goto('https://project-pulse-641.preview.emergentagent.com/projects')
        await page.wait_for_timeout(1600)
        banner_after = await page.locator('[data-testid="offline-banner"]').count() > 0
        count_present = await page.locator('[data-testid="projects-count"]').count() > 0
        print(f"D10 reconnect bannerVisible={banner_after} projectsCountVisible={count_present}")

        error_text = await page.evaluate("""() => {
        const errorElements = Array.from(document.querySelectorAll('.error, [class*="error"], [id*="error"]'));
        return errorElements.map(el => el.textContent).join(", ");
        }""")
        if error_text:
            print(f"Found error message: {error_text}")
        else:
            print("No error messages found on the page")

    except Exception as e:
        print(f"PWA/offline check failed: {str(e)}")
