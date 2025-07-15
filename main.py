import requests
from bs4 import BeautifulSoup
from telegram.ext import Updater, MessageHandler, Filters
import os
# Replace with your bot token
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")


def get_ungraded_price(card_query: str) -> str:
    try:
        print(f"[INFO] Fetching: {card_query}")
        base_url = "https://www.pricecharting.com/search-products"
        params = {"q": card_query, "type": "prices"}
        session = requests.Session()
        response = session.get(base_url, params=params, allow_redirects=True)

        if response.status_code != 200:
            print(f"[ERROR] HTTP {response.status_code} for '{card_query}'")
            return "-"

        soup = BeautifulSoup(response.text, 'html.parser')
        full_prices_div = soup.find('div', {'id': 'full-prices'})
        if not full_prices_div:
            print(f"[WARN] No full-prices section found for '{card_query}'")
            return "-"

        rows = full_prices_div.find_all('tr')
        for row in rows:
            cols = row.find_all('td')
            if len(cols) >= 2 and "Ungraded" in cols[0].text:
                price = cols[1].text.strip()
                print(f"[SUCCESS] {card_query} → {price}")
                return price

        print(f"[WARN] Ungraded price not found for '{card_query}'")
        return "-"
    except Exception as e:
        print(f"[EXCEPTION] Error while fetching '{card_query}': {e}")
        return "-"

def get_card_name_from_tcg_republic(series: str, serial: str):
    try:
        serial_padded = serial.zfill(3)
        url = f"https://tcgrepublic.com/product/text_search.html?q={series}%09{serial_padded}"
        print(f"[INFO] Fetching card name from: {url}")
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f"[ERROR] HTTP {response.status_code} for {series} {serial}")
            return "-", "-"

        soup = BeautifulSoup(response.text, 'html.parser')
        img_tags = soup.select('.product_thumbnail_image img')

        if len(img_tags) == 0:
            print(f"[WARN] No image found for {series} {serial}")
            return "-", "-"
        elif len(img_tags) > 1:
            print(f"[WARN] Multiple images found for {series} {serial}")
            return "-", "-"

        alt_text = img_tags[0].get('alt', '').strip()
        if not alt_text:
            print(f"[WARN] Image found but no alt text for {series} {serial}")
            return "-", "-"

        # Example: "Spiritomb 076/071 AR Foil"
        name_part = alt_text.split('/')[0].strip()  # "Spiritomb 076"
        name_tokens = name_part.split()
        if not name_tokens:
            return "-", "-"

        *name_words, number = name_tokens
        name_clean = " ".join(name_words)             # "Spiritomb"
        query = f"{name_clean} #{int(number)}"        # "Spiritomb #76"
        return name_clean, query

    except Exception as e:
        print(f"[EXCEPTION] Error parsing TCGRepublic for {series} {serial}: {e}")
        return "-", "-"



def handle_message(update, context):
    raw_text = update.message.text.strip()
    print(f"[RECEIVED] {raw_text}")

    lines = [line.strip() for line in raw_text.replace(',', '\n').split('\n') if line.strip()]
    names = []
    prices = []

    for line in lines:
        parts = line.split()
        if "#" in line:
            # e.g., "Blaziken V #18"
            name = line.rsplit('#', 1)[0].strip()
            query = line
        elif len(parts) == 2:
            series, serial = parts
            name, query = get_card_name_from_tcg_republic(series.lower(), serial)
            if name == "-" or query == "-":
                names.append("-")
                prices.append("-")
                continue
        else:
            names.append("-")
            prices.append("-")
            continue

        price = get_ungraded_price(query)
        names.append(name)
        prices.append(price)

    update.message.reply_text("\n\n".join(names + prices))


def main():
    updater = Updater(TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
