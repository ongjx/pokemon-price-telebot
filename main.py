import os
import time
import requests
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    ContextTypes,
    filters
)
import asyncio
import nest_asyncio

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

def get_card_name_from_tcg_republic(series: str, serial: str):
    try:
        serial_padded = serial.zfill(3)
        url = f"https://tcgrepublic.com/product/text_search.html?q={series}%09{serial_padded}"
        print(f"[INFO] Fetching card name from: {url}")
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f"[ERROR] HTTP {response.status_code}")
            return "-", "-"

        soup = BeautifulSoup(response.text, 'html.parser')
        img_tags = soup.select('.product_thumbnail_image img')

        if len(img_tags) != 1:
            print(f"[WARN] Expected 1 image, got {len(img_tags)}")
            return "-", "-"

        alt_text = img_tags[0].get('alt', '').strip()
        name_part = alt_text.split('/')[0].strip()
        name_tokens = name_part.split()
        if not name_tokens:
            return "-", "-"
        *name_words, number = name_tokens
        name_clean = " ".join(name_words)
        query = f"{name_clean} #{int(number)}"
        return name_clean, query
    except Exception as e:
        print(f"[EXCEPTION] Error parsing TCGRepublic: {e}")
        return "-", "-"

def get_ungraded_price(card_query: str) -> str:
    try:
        print(f"[INFO] Fetching price for: {card_query}")
        base_url = "https://www.pricecharting.com/search-products"
        params = {"q": card_query, "type": "prices"}
        session = requests.Session()
        response = session.get(base_url, params=params, allow_redirects=True)

        if response.status_code != 200:
            return "-"

        soup = BeautifulSoup(response.text, 'html.parser')
        full_prices_div = soup.find('div', {'id': 'full-prices'})
        if not full_prices_div:
            return "-"

        rows = full_prices_div.find_all('tr')
        for row in rows:
            cols = row.find_all('td')
            if len(cols) >= 2 and "Ungraded" in cols[0].text:
                return cols[1].text.strip()

        return "-"
    except Exception as e:
        print(f"[ERROR] Failed to get price for {card_query}: {e}")
        return "-"

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    print(f"[RECEIVED] {text}")
    lines = [line.strip() for line in text.replace(',', '\n').split('\n') if line.strip()]

    names = []
    prices = []

    for line in lines:
        parts = line.split()
        if "#" in line:
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

        names.append(name)
        prices.append(get_ungraded_price(query))
        time.sleep(1.5)

    result = "\n".join(names + prices)
    await update.message.reply_text(result)

async def main():
    if not TELEGRAM_TOKEN:
        raise ValueError("Missing TELEGRAM_TOKEN")

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("[INFO] Bot is running...")
    await app.run_polling()

if __name__ == "__main__":
    nest_asyncio.apply()
    asyncio.get_event_loop().run_until_complete(main())
