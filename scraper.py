import time
import datetime
from selenium.common import NoSuchElementException
from selenium.webdriver import Chrome
from selenium.common.exceptions import ElementNotInteractableException, ElementClickInterceptedException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver import Keys
import pandas as pd
from bs4 import BeautifulSoup

# Initialization
POSTCODES = {"WA1": "01-354", "WA3": "00-510", "WRO": "50-159", "GDA": "80-834", "KRA": "31-154"}
CATS = ["c,18703/cat,warzywa-i-owoce/"]
date = datetime.datetime.now().strftime("%d-%m-%Y %H-%M")

options = Options()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

driver = Chrome(options=options)
driver.get(f"https://www.frisco.pl/{CATS[0]}/stn,searchResults")
time.sleep(1)

# Popup click
driver.find_element("xpath", "/html/body/div[1]/div/div[1]/div/div/div/div/div[2]/div/button[1]").click()
time.sleep(1)

# Initial postcode
driver.find_element("id", "postcode").send_keys(list(POSTCODES.values())[0])
driver.find_element("xpath", "/html/body/div[1]/div/div[10]/div/div/div/div[2]/button").click()

timer = time.time()

def get_timer():
    current_time = time.time() - timer
    return f"{int(current_time)//60:02d}:{int(current_time)%60:02d}:{int(current_time%1*100):02d}"

# Compiling raw html into dataframe
def compile_today(raw_html):
    soup = BeautifulSoup(raw_html, features="html.parser")
    items = soup.find_all("div", class_="product-box_holder")

    data = [{
        "id": item.find("a", title=True, href=True, class_="product-box-layout__name")["href"].split("/n")[0][5:],
        "name": item.find("a", title=True, href=True, class_="product-box-layout__name")["title"],
        "weight": item.find("span", class_="product-box-layout__desc-weight").text,
        "status": item.find("div", class_="cart-button_add").text,
        "main_price": item.find("span", class_="product-box-layout__price-main").text if item.find("div", class_="cart-button_add").text=="Do koszyka" else 0,
        "original_price": item.find("div", class_="product-box-layout__price-wrapper is-secondary").text  if item.find("div", class_="cart-button_add").text=="Do koszyka" else 0,
        "promo_text": item.find("div", class_="product-box-layout__tags-promo-box").text
    }for item in items]

    return pd.DataFrame(data)

for city in list(POSTCODES.keys()):
    # Changing city
    if city != list(POSTCODES.keys())[0]:
        # Open postcode selection
        driver.find_element("class name", "header-postcode").click()
        time.sleep(1)

        # Postcode selection button
        try:
            driver.find_element("class name", "header-post-code-dropdown").find_element("tag name", "button").click()
        except NoSuchElementException:
            time.sleep(1)
            driver.find_element("class name", "header-post-code-dropdown").find_element("tag name", "button").click()
        time.sleep(0.5)

        # Remove previous postcode
        for i in range(6):
            driver.find_element("id", "postcode").send_keys(Keys.BACKSPACE)

        # Write and save postcode
        driver.find_element("id", "postcode").send_keys(POSTCODES[city])
        driver.find_element("class name", "postcode-form_actions").find_element("class name", "cta").click()
        time.sleep(1)
        driver.get(f"https://www.frisco.pl/{CATS[0]}/stn,searchResults")
        time.sleep(1)

    htmls = []

    # Getting number of pages and number of items
    n_pagers = len(driver.find_elements("class name", "page-selector__page"))
    total_items = int(driver.find_element("class name", "biggish-title").find_element("xpath", "following-sibling::*").text.split(": ")[1])
    found_items = 0

    # Going through each page
    print(f"{city}\t-\t\t\t\t\t{get_timer()}")
    for page in range(n_pagers):

        # Click pager
        try:
            driver.find_elements("class name", "page-selector__page")[page].click()
        except ElementClickInterceptedException:
            driver.find_elements("class name", "page-selector__page")[page].click()
        except ElementNotInteractableException:
            pass
        time.sleep(1)

        # Get html
        inner = driver.find_element("class name", "list-view_content")
        n_products = len(inner.find_elements('class name', 'product-box-layout'))
        found_items += n_products

        # Retry if there are too litle items
        if n_products < 70 and page != (n_pagers-1):
            print(f"\t! found only {n_products}, retrying\t\t{get_timer()}")
            time.sleep(3)
            inner = driver.find_element("class name", "list-view_content")
            n_products = len(inner.find_elements('class name', 'product-box-layout'))
        elif page == (n_pagers-1) and n_products < (total_items - found_items):
            print(f"\t! found only {n_products}, retrying\t\t{get_timer()}")
            time.sleep(3)
            inner = driver.find_element("class name", "list-view_content")
            n_products = len(inner.find_elements('class name', 'product-box-layout'))

        print(f"\t-{found_items}/{total_items} (+{n_products})\t\t\t\t{get_timer()}")

        htmls.append(inner.get_attribute("innerHTML"))

    if found_items != total_items:
        print(f"\t ! Missing {total_items - found_items}")

    df = compile_today("".join(htmls))
    df["timestamp"] = date
    print(f"\t- Compiled\t\t\t{get_timer()}")

    df.to_csv(f"data/{city}.csv", index=False, header=False, mode="a")
    print(f"\t- Saved\t\t\t\t{get_timer()}")
