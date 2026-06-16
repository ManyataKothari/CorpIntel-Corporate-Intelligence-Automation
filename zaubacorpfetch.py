from playwright.sync_api import sync_playwright
import time, re, csv, os

CIN_FILE = r"C:\Users\Manyata Kothari\OneDrive\Desktop\ZaubaCorp\cin_list.txt"
OUT_FILE = "zauba_results.csv"
USER_DATA_DIR = "chrome_profile"   # persistent session


def human_delay(min_s=4, max_s=7):
    time.sleep((min_s + max_s) / 2)


def fetch_company_data(context, cin):
    page = context.new_page()
    data = {"CIN": cin}

    url = f"https://www.zaubacorp.com/company/{cin}"
    page.goto(url, timeout=120000)

    # Ensure page loaded (Cloudflare-safe)
    try:
        page.wait_for_selector("h1", timeout=20000)
    except:
        print("⚠️ Blocked again for:", cin)
        page.close()
        return None

    # Human-like scroll
    for _ in range(4):
        page.mouse.wheel(0, 1200)
        time.sleep(1.5)

    full_text = page.evaluate("() => document.body.innerText")

    # 1️⃣ Company Name
    try:
        data["company_name"] = page.locator("h1").inner_text().strip()
    except:
        data["company_name"] = ""

    # 2️⃣ Date of Incorporation
    try:
        doi = page.locator(
            "//tr[td[contains(., 'Date of Incorporation')]]/td[2]"
        ).first.inner_text()
        data["date_of_incorporation"] = doi.strip()
    except:
        match = re.search(
            r"Date of Incorporation\s*[:\-]?\s*([0-9]{2}/[0-9]{2}/[0-9]{4})",
            full_text
        )
        data["date_of_incorporation"] = match.group(1) if match else ""

    # 3️⃣ Directors
    try:
        directors = page.locator(
            "//h3[contains(.,'Directors')]/following::table[1]//tr/td[2]"
        ).all_inner_texts()
        data["directors"] = ", ".join(d.strip() for d in directors if d.strip())
    except:
        data["directors"] = ""

    # 4️⃣ Email
    email_match = re.search(
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        full_text
    )
    data["email"] = email_match.group(0) if email_match else ""

    # 5️⃣ Last Filed Balance Sheet
    try:
        last_bs = page.locator(
            "//h3[contains(., 'Annual Compliance Status')]/following::table[1]"
            "//tr[td[contains(., 'Balance Sheet')]]/td[2]"
        ).first.inner_text()
        data["last_filed_bs"] = last_bs.strip()
    except:
        bs_match = re.search(
            r"Balance Sheet\s*[:\-]?\s*([0-9]{4})",
            full_text
        )
        data["last_filed_bs"] = bs_match.group(1) if bs_match else ""

    # 6️⃣ Authorised Capital (EXPLICIT)
    try:
        auth_cap = page.locator(
            "//tr[td[contains(., 'Authorised')]]/td[2]"
        ).first.inner_text()
        data["authorised_share_capital"] = auth_cap.strip()
    except:
        auth_match = re.search(
            r"Authorised.*?₹\s*([\d,]+)",
            full_text,
            re.IGNORECASE
        )
        data["authorised_share_capital"] = auth_match.group(1) if auth_match else ""

    # 7️⃣ Paid-up Capital (EXPLICIT – FIXED)
    try:
        paid_cap = page.locator(
            "//tr[td[contains(., 'Paid') and contains(., 'Capital')]]/td[2]"
        ).first.inner_text()
        data["paidup_share_capital"] = paid_cap.strip()
    except:
        paid_match = re.search(
            r"Paid[\s-]*up.*?₹\s*([\d,]+)",
            full_text,
            re.IGNORECASE
        )
        data["paidup_share_capital"] = paid_match.group(1) if paid_match else ""

    # 8️⃣ Current Status
    status_match = re.search(
        r"(Active|Strike Off|Dormant|Liquidated|Amalgamated)",
        full_text,
        re.IGNORECASE
    )
    data["current_status"] = status_match.group(1).title() if status_match else ""

    page.close()
    return data


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            USER_DATA_DIR,
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )

        # 🔐 One-time Cloudflare verification
        page = browser.new_page()
        page.goto("https://www.zaubacorp.com/", timeout=120000)
        print("\n🔐 Solve Cloudflare ONLY ONCE.")
        input("✅ Press ENTER after verification...")

        with open(CIN_FILE) as f:
            cins = [c.strip() for c in f if c.strip()]

        write_header = not os.path.exists(OUT_FILE)
        with open(OUT_FILE, "a", newline="", encoding="utf-8") as f:
            fields = [
                "CIN",
                "company_name",
                "date_of_incorporation",
                "directors",
                "email",
                "last_filed_bs",
                "authorised_share_capital",
                "paidup_share_capital",
                "current_status"
            ]
            writer = csv.DictWriter(f, fieldnames=fields)
            if write_header:
                writer.writeheader()

            for i, cin in enumerate(cins, 1):
                print(f"➡️ {i}/{len(cins)} Processing {cin}")
                data = fetch_company_data(browser, cin)
                if data:
                    writer.writerow(data)
                    f.flush()
                    print("✅ Saved:", cin)
                human_delay()

        browser.close()
        print("\n🎉 DONE. Data saved in:", OUT_FILE)


if __name__ == "__main__":
    main()