import requests
from bs4 import BeautifulSoup
import csv
import time

BASE_URL = "https://books.toscrape.com/catalogue/"
START_URL = "https://books.toscrape.com/catalogue/page-1.html"

# Map word ratings to numbers
RATING_MAP = {
    "One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5
}

def parse_page(url):
    """Scrape all books from a single listing page."""
    response = requests.get(url)
    response.encoding = "utf-8"
    soup = BeautifulSoup(response.text, "html.parser")

    books = []
    for article in soup.select("article.product_pod"):
        # Title (full title is in the <a> tag's title attribute)
        title = article.select_one("h3 a")["title"]

        # Price
        price = article.select_one("p.price_color").text.strip()

        # Star rating
        rating_word = article.select_one("p.star-rating")["class"][1]
        rating = RATING_MAP.get(rating_word, 0)

        # Availability
        availability = article.select_one("p.instock.availability").text.strip()

        # Relative image URL → absolute
        img_src = article.select_one("img.thumbnail")["src"]
        img_url = "https://books.toscrape.com/" + img_src.replace("../", "")

        # Book detail page URL
        relative_href = article.select_one("h3 a")["href"]
        book_url = BASE_URL + relative_href.replace("../", "")

        books.append({
            "title": title,
            "price": price,
            "rating": rating,
            "availability": availability,
            "image_url": img_url,
            "book_url": book_url,
        })

    # Find the "next" button for pagination
    next_btn = soup.select_one("li.next a")
    next_url = BASE_URL + next_btn["href"] if next_btn else None

    return books, next_url


def scrape_all_books(output_file="books_dataset.csv"):
    all_books = []
    url = START_URL
    page = 1

    while url:
        print(f"Scraping page {page}...")
        books, url = parse_page(url)
        all_books.extend(books)
        page += 1
        time.sleep(0.5)  # Be polite — small delay between requests

    # Write to CSV
    fieldnames = ["title", "price", "rating", "availability", "image_url", "book_url"]
    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_books)

    print(f"\n✅ Done! Scraped {len(all_books)} books → saved to '{output_file}'")
    return all_books


if __name__ == "__main__":
    scrape_all_books()