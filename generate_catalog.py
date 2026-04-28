import csv
import html
import os
import re
import urllib.request
from datetime import datetime
from pathlib import Path


PRICE_DROP_WINDOW_DAYS = 30

BUYING_GUIDELINES = [
    "Ask for a video of the artwork they are selling and have them state their name and date in the video as well. If they cannot provide you with that video, then do not proceed with the transaction and please report that member to the admin/moderator team.",
    "Ask the admins and moderators if they know of the seller. One of us may be able to provide you with insight. Also ask the seller if they have any sales references of people that you can contact to ask how their transaction went with the seller.",
    "Always use goods and services via PayPal or Venmo if it is a new seller that has no sales references.",
    "Always obtain shipping insurance for the total purchase price.",
]

SHIPPING_GUIDELINES = [
    "Always obtain shipping insurance for the total purchase price.",
    "For transactions $10,000 and less, UPS through Pirate Ship’s website provides by far the best shipping rates and can fully insure the package for the sale price.",
    "For transactions above $10,000, you will need to seek alternative shipping options to fully insure. We recommend utilizing goshippo.com to find the best shipping rates that will fully cover the transaction cost.",
    "For packaging the art, Park West art boxes are highly recommended since they provide proper spacing and styrofoam corners. You can also use TV boxes from U-Haul, Lowe’s, or Home Depot, but make sure to use packaging materials that provide proper shock absorption protection to the art during shipping. Bubble wrap, packing peanuts, and styrofoam are all good options. Make sure the art itself cannot jostle around in the box.",
    "When packaging, never place any packing materials directly on the canvas itself as you run the risk of damage to the art due to the added weight that can cause the canvas to sag onto its stretcher bars on the back.",
    "Before shipping, take pictures and videos of the art in the packaging as proof of proper packaging. This will help if you need to file a shipping insurance claim if the art gets damaged during shipping. Insurance claims will not go through if you improperly package your art beforehand, so please take the necessary added precautions to ensure you have done this properly. The admin and moderators can provide advice if anyone needs help on packaging.",
    "If the art arrives damaged due to shipping carrier mishandling, do not panic. The receiver or buyer of the art will need to take pictures of the packaging and where the damage on the art has occurred. Do not throw away any of the packaging or ship the damaged art anywhere during the insurance claim process. The insurance claim may ask for the buyer to get a third-party letter stating the art or frame cannot be repaired. Michael’s, Hobby Lobby custom framing, or another art framer may be able to provide this.",
    "For expensive pieces, we also recommend requiring a signature upon delivery. This helps prevent issues from inclement weather and reduces the risk of package theft.",
]


INPUT_TO_OUTPUT = {
    "Timestamp": "processed_at",
    "Seller Name": "seller_name",
    "Artist Name": "artist_name",
    "Artwork Title": "artwork_title",
    "Medium/Type": "medium",
    "Is this artwork a unique/original or limited edition?": "artwork_category",
    "Artwork Size (inches)": "artwork_size_inches",
    "Framed Size (inches)": "framed_size_inches",
    "Price (USD)": "price",
    "Shipping Included?": "shipping_included",
    "Certificate of Authenticity Included?": "certificate_of_authenticity_included",
    "Seller Notes/ Description": "seller_notes",
    "Seller Notes/ Description ": "seller_notes",
    "Upload Artwork Image (ONE image per submission)": "source_image_url",
    "Link to Seller Facebook Profile (Make sure your link works before submitting as this link will be on each of your listings for potential buyers to contact you!)": "seller_profile_url",
    "Seller Email Address (gmail preferred)": "seller_email",

    "listing_id": "listing_id",
    "image_file": "image_file",
    "source_image_url": "source_image_url",
    "status": "status",
    "seller_token": "seller_token",
    "updated_at": "updated_at",
    "previous_price": "previous_price",
    "price_updated_at": "price_updated_at",
    "moderation_status": "moderation_status",
    "seller_profile_url": "seller_profile_url",
    "seller_email": "seller_email",

    "processed_at": "processed_at",
    "seller_name": "seller_name",
    "artist_name": "artist_name",
    "artwork_title": "artwork_title",
    "medium": "medium",
    "artwork_category": "artwork_category",
    "artwork_size_inches": "artwork_size_inches",
    "framed_size_inches": "framed_size_inches",
    "price": "price",
    "shipping_included": "shipping_included",
    "certificate_of_authenticity_included": "certificate_of_authenticity_included",
    "seller_notes": "seller_notes",
}

OUTPUT_COLUMNS = [
    "listing_id",
    "seller_name",
    "seller_email",
    "seller_profile_url",
    "artist_name",
    "artwork_title",
    "medium",
    "artwork_size_inches",
    "framed_size_inches",
    "price",
    "shipping_included",
    "certificate_of_authenticity_included",
    "seller_notes",
    "image_file",
    "source_image_url",
    "processed_at",
    "updated_at",
    "previous_price",
    "price_updated_at",
    "status",
    "moderation_status",
]


def clean(value):
    if value is None:
        return ""
    return str(value).strip()


def normalize_bool_text(value):
    value = clean(value)
    if not value:
        return ""

    lower = value.lower()

    if lower in {"yes", "y", "true", "1"}:
        return "TRUE"

    if lower in {"no", "n", "false", "0"}:
        return "FALSE"

    return ""


def normalize_artwork_category(value):
    value = clean(value)
    if not value:
        return ""

    normalized = value.lower().replace(" ", "").replace("-", "").replace("_", "")

    if "limited" in normalized:
        return "Limited Edition"

    if "unique" in normalized or "original" in normalized:
        return "Unique/Original"

    return value


def normalize_price(value):
    value = clean(value)
    if not value:
        return ""

    cleaned = value.replace("$", "").replace(",", "").strip()
    try:
        number = float(cleaned)
    except ValueError:
        return value

    if number.is_integer():
        return str(int(number))
    return f"{number:.2f}"


def normalize_row(row, index):
    converted = {col: "" for col in OUTPUT_COLUMNS}

    for src_col, dest_col in INPUT_TO_OUTPUT.items():
        if src_col in row and clean(row[src_col]):
            converted[dest_col] = clean(row[src_col])

    if not converted["listing_id"]:
        converted["listing_id"] = f"listing_{index:04d}"

    if not converted["image_file"]:
        converted["image_file"] = f"{converted['listing_id']}.jpg"

    if not converted["status"]:
        converted["status"] = "available"

    if not converted["source_image_url"]:
        converted["source_image_url"] = clean(
            row.get("Upload Artwork Image (ONE image per submission)", "")
        )

    converted["shipping_included"] = normalize_bool_text(converted["shipping_included"])
    converted["certificate_of_authenticity_included"] = normalize_bool_text(
        converted["certificate_of_authenticity_included"]
    )
    converted["price"] = normalize_price(converted["price"])
    converted["artwork_category"] = normalize_artwork_category(converted["artwork_category"])

    return converted


def is_public_listing(row):
    moderation_status = clean(row.get("moderation_status")).lower()
    listing_status = clean(row.get("status")).lower()

    if moderation_status != "approved":
        return False

    return listing_status in {"available", "pending"}


def load_csv_rows_from_path(csv_path):
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def load_csv_rows_from_url(url):
    with urllib.request.urlopen(url) as response:
        raw = response.read()

    text = raw.decode("utf-8-sig")
    return list(csv.DictReader(text.splitlines()))


def build_google_sheet_csv_url(sheet_id, gid="0"):
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"


def load_data(source):
    if str(source).startswith(("http://", "https://")):
        rows = load_csv_rows_from_url(source)
    else:
        rows = load_csv_rows_from_path(source)

    normalized_rows = []
    for i, row in enumerate(rows, start=1):
        normalized = normalize_row(row, i)
        normalized["_row_index"] = i - 1
        if is_public_listing(normalized):
            normalized_rows.append(normalized)

    return normalized_rows


def parse_price(value):
    if value in (None, "", "None"):
        return None
    try:
        return float(value)
    except ValueError:
        return None


def format_price(value):
    price = parse_price(value)
    if price is None:
        return "Price on request"
    if price.is_integer():
        return f"${int(price):,}"
    return f"${price:,.2f}"


def is_price_drop(row):
    current_price = parse_price(row.get("price"))
    previous_price = parse_price(row.get("previous_price"))

    if current_price is None or previous_price is None:
        return False

    if previous_price <= current_price:
        return False

    price_updated_at = parse_datetime(row.get("price_updated_at"))
    if price_updated_at is None:
        return True

    if price_updated_at.tzinfo:
        age_days = (datetime.now(price_updated_at.tzinfo) - price_updated_at).days
    else:
        age_days = (datetime.now() - price_updated_at).days

    return age_days <= PRICE_DROP_WINDOW_DAYS


def build_price_html(row):
    current_display = format_price(row.get("price"))

    if not is_price_drop(row):
        return f'<div class="price">{safe_text(current_display)}</div>'

    previous_display = format_price(row.get("previous_price"))

    return f"""
                <div class="price price-drop-price">
                    <span class="price-drop-label">Price Drop</span>
                    <span class="price-stack">
                        <span class="old-price">{safe_text(previous_display)}</span>
                        <span class="new-price">{safe_text(current_display)}</span>
                    </span>
                </div>
    """


def parse_bool(value):
    if value in (True, False):
        return value
    if value is None:
        return None
    s = str(value).strip().lower()
    if s in ("1", "true", "yes"):
        return True
    if s in ("0", "false", "no"):
        return False
    return None


def parse_datetime(value):
    if not value:
        return None

    text = str(value).strip()
    if not text:
        return None

    formats = [
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue

    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def safe_text(value):
    if value is None:
        return ""
    return html.escape(str(value))


def extract_drive_file_id(url):
    if not url:
        return ""

    text = str(url).strip()
    patterns = [
        r"/file/d/([a-zA-Z0-9_-]+)",
        r"[?&]id=([a-zA-Z0-9_-]+)",
        r"/open\?id=([a-zA-Z0-9_-]+)",
        r"^([a-zA-Z0-9_-]{20,})$",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)

    return ""


def drive_thumbnail_url(url, size="w600"):
    file_id = extract_drive_file_id(url)
    if not file_id:
        return clean(url)
    return f"https://drive.google.com/thumbnail?id={file_id}&sz={size}"


def relative_image_src(output_path: Path, source_dir: Path, filename: str) -> str:
    return f"images/{filename}"


def build_image_src(row, output_path: Path, images_path: Path) -> str:
    source_image_url = clean(row.get("source_image_url"))
    if source_image_url:
        return drive_thumbnail_url(source_image_url)

    image_file = clean(row.get("image_file"))
    if image_file:
        return relative_image_src(output_path, images_path, image_file)

    return ""


def build_badges(row):
    badges = []

    shipping = parse_bool(row.get("shipping_included"))
    coa = parse_bool(row.get("certificate_of_authenticity_included"))
    category = (row.get("artwork_category") or "").strip()
    status = (row.get("status") or "").strip()

    if shipping is True:
        badges.append('<span class="badge">Shipping Included</span>')
    elif shipping is False:
        badges.append('<span class="badge badge-muted">Shipping Extra</span>')

    if coa is True:
        badges.append('<span class="badge">COA Included</span>')

    if category:
        badges.append(f'<span class="badge artwork-category-badge">{safe_text(category)}</span>')

    if status:
        status_class = "status-pill"
        status_lower = status.lower()
        if status_lower == "sold":
            status_class += " status-sold"
        elif status_lower == "pending":
            status_class += " status-pending"
        elif status_lower == "available":
            status_class += " status-available"
        badges.append(f'<span class="{status_class}">{safe_text(status)}</span>')

    return "".join(badges)


def build_specs(row):
    specs = []

    medium = (row.get("medium") or "").strip()
    artwork_size = (row.get("artwork_size_inches") or "").strip()
    framed_size = (row.get("framed_size_inches") or "").strip()

    if medium:
        specs.append(
            f'<div class="spec-row"><span class="spec-label">Type</span><span class="spec-value">{safe_text(medium)}</span></div>'
        )

    if artwork_size:
        specs.append(
            f'<div class="spec-row"><span class="spec-label">Artwork Size</span><span class="spec-value">{safe_text(artwork_size)}</span></div>'
        )

    if framed_size:
        specs.append(
            f'<div class="spec-row"><span class="spec-label">Framed Size</span><span class="spec-value">{safe_text(framed_size)}</span></div>'
        )

    return "".join(specs)


def build_notes(row):
    notes = (row.get("seller_notes") or "").strip()
    if not notes:
        return ""
    return f'<p class="notes">{safe_text(notes)}</p>'


def newest_sort_value(row):
    dt = parse_datetime(row.get("processed_at"))
    if dt is not None:
        return dt.timestamp()
    return float(row.get("_row_index", 0))


def get_price_band(price):
    if price is None:
        return "unknown"
    if price < 1000:
        return "under1000"
    if price <= 2499:
        return "1000to2499"
    if price <= 4999:
        return "2500to4999"
    return "5000plus"


def build_card(row, image_src):
    image_html = ""
    if image_src:
        alt_text = safe_text(row.get("artwork_title") or row.get("artist_name") or "Artwork")
        image_html = f"""
        <button class="image-open" type="button" data-fullsrc="{image_src}" data-alt="{alt_text}" aria-label="Open artwork image">
            <img 
                src="{image_src}" 
                data-fullsrc="{drive_thumbnail_url(row.get('source_image_url'), 'w1200')}" 
                class="art-img" 
                alt="{alt_text}" 
                loading="lazy" 
                decoding="async"
            >
        </button>
        """

    artist_name_raw = row.get("artist_name") or "Unknown Artist"
    artwork_title_raw = row.get("artwork_title") or "Untitled"
    medium_raw = row.get("medium") or ""
    artwork_category_raw = row.get("artwork_category") or ""
    seller_name_raw = row.get("seller_name") or ""
    status_raw = row.get("status") or ""
    listing_id_raw = row.get("listing_id") or ""

    artist_name = safe_text(artist_name_raw)
    artwork_title = safe_text(artwork_title_raw)
    seller_name = safe_text(seller_name_raw)

    price_raw = row.get("price")
    price_html = build_price_html(row)
    price_numeric = parse_price(price_raw)
    price_for_filter = price_numeric if price_numeric is not None else -1

    shipping = parse_bool(row.get("shipping_included"))
    coa = parse_bool(row.get("certificate_of_authenticity_included"))

    badges = build_badges(row)
    specs = build_specs(row)
    notes = build_notes(row)

    seller_profile_url = (row.get("seller_profile_url") or "").strip()

    contact_button = ""
    if seller_profile_url:
        safe_url = html.escape(seller_profile_url, quote=True)
        contact_button = f'''
        <a href="{safe_url}" target="_blank" rel="noopener noreferrer" class="contact-seller-button">
            Contact Seller
        </a>
        '''

    seller_html = (
        f"""
        <div class="seller">
            <span class="seller-label">Seller</span>
            <span class="seller-name">{seller_name}</span>
            {contact_button}
        </div>
        """
        if seller_name else ""
    )

    searchable_text = " ".join(
        [
            str(artist_name_raw),
            str(artwork_title_raw),
            str(medium_raw),
            str(artwork_category_raw),
            str(seller_name_raw),
            str(status_raw),
            str(row.get("seller_notes") or ""),
        ]
    ).lower()

    newest_value = newest_sort_value(row)
    listing_id = html.escape(str(listing_id_raw))

    return f"""
    <article class="card"
        data-listing-id="{listing_id}"
        data-artist="{html.escape(str(artist_name_raw).lower())}"
        data-seller="{html.escape(str(seller_name_raw).lower())}"
        data-medium="{html.escape(str(medium_raw).lower())}"
        data-category="{html.escape(str(artwork_category_raw).lower())}"
        data-status="{html.escape(str(status_raw).lower())}"
        data-price="{price_for_filter}"
        data-price-band="{get_price_band(price_numeric)}"
        data-price-drop="{str(is_price_drop(row)).lower()}"
        data-shipping="{'' if shipping is None else str(shipping).lower()}"
        data-coa="{'' if coa is None else str(coa).lower()}"
        data-newest="{newest_value}"
        data-search="{html.escape(searchable_text)}">
        <div class="card-image-wrap">
            {image_html}
        </div>
        <div class="card-body">
            <div class="card-header">
                <div>
                    <h2 class="artist-name">{artist_name}</h2>
                    <div class="artwork-title">{artwork_title}</div>
                </div>
                {price_html}
            </div>

            <div class="badges">{badges}</div>

            <div class="specs">
                {specs}
            </div>

            {seller_html}

            <div class="listing-actions">
                <button class="save-listing-button" type="button" data-listing-id="{listing_id}" aria-label="Save listing">
                    ♡ Save Listing
                </button>
            </div>

            {notes}
        </div>
    </article>
    """


def summary_stats(data):
    available_rows = [r for r in data if (r.get("status") or "").strip().lower() != "sold"]

    listing_count = len(available_rows)

    artist_count = len({
        (r.get("artist_name") or "").strip().lower()
        for r in available_rows
        if (r.get("artist_name") or "").strip()
    })

    seller_count = len({
        (r.get("seller_name") or "").strip().lower()
        for r in available_rows
        if (r.get("seller_name") or "").strip()
    })

    return {
        "listing_count": listing_count,
        "artist_count": artist_count,
        "seller_count": seller_count,
    }


def unique_values(data, key):
    values = sorted({
        (row.get(key) or "").strip()
        for row in data
        if (row.get(key) or "").strip()
    })
    return values


def generate_guidelines_html(output_path: Path, title: str):
    index_src = "index.html"
    logo_src = "assets/logo.png"

    buying_items = "\n".join(f"<li>{safe_text(item)}</li>" for item in BUYING_GUIDELINES)
    shipping_items = "\n".join(f"<li>{safe_text(item)}</li>" for item in SHIPPING_GUIDELINES)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <link rel="icon" href="assets/favicon.ico">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{safe_text(title)} — Buying & Shipping Guidelines</title>
    <style>
        :root {{
            --bg: #f5f1ea;
            --card: rgba(255,255,255,0.86);
            --text: #1f1a17;
            --muted: #6f675e;
            --line: #dbd1c4;
            --shadow-soft: 0 8px 22px rgba(35, 27, 20, 0.05);
        }}

        * {{
            box-sizing: border-box;
        }}

        body {{
            margin: 0;
            color: var(--text);
            background:
                radial-gradient(circle at top left, rgba(255,255,255,0.7), transparent 35%),
                linear-gradient(180deg, #f7f3ed 0%, #f2ece3 100%);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            line-height: 1.6;
        }}

        .page {{
            max-width: 980px;
            margin: 0 auto;
            padding: 32px 20px 80px;
        }}

        .hero {{
            display: grid;
            grid-template-columns: 120px 1fr;
            gap: 24px;
            align-items: center;
            padding-bottom: 24px;
            border-bottom: 1px solid var(--line);
            margin-bottom: 28px;
        }}

        .brand-logo {{
            width: 108px;
            max-width: 100%;
            height: auto;
            display: block;
            filter: drop-shadow(0 8px 18px rgba(0,0,0,0.08));
        }}

        .hero-copy h1 {{
            margin: 0;
            font-family: Georgia, "Times New Roman", serif;
            font-size: clamp(30px, 4vw, 48px);
            line-height: 1.02;
            letter-spacing: -0.03em;
            font-weight: 600;
        }}

        .hero-sub {{
            margin-top: 14px;
            color: var(--muted);
            max-width: 720px;
            font-size: 16px;
        }}

        .hero-links {{
            margin-top: 14px;
        }}

        .hero-link {{
            color: var(--text);
            text-decoration: none;
            font-size: 14px;
            border-bottom: 1px solid rgba(31, 26, 23, 0.25);
        }}

        .hero-link:hover {{
            border-bottom-color: rgba(31, 26, 23, 0.65);
        }}

        .notice {{
            background: var(--card);
            border: 1px solid rgba(219, 209, 196, 0.85);
            border-radius: 18px;
            padding: 18px 20px;
            box-shadow: var(--shadow-soft);
            margin-bottom: 26px;
            color: var(--text);
        }}

        .notice strong {{
            display: block;
            margin-bottom: 6px;
            font-size: 14px;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: var(--muted);
        }}

        .section {{
            background: var(--card);
            border: 1px solid rgba(219, 209, 196, 0.85);
            border-radius: 22px;
            padding: 24px 24px 26px;
            box-shadow: var(--shadow-soft);
            margin-bottom: 20px;
        }}

        .section h2 {{
            margin: 0 0 14px;
            font-family: Georgia, "Times New Roman", serif;
            font-size: 30px;
            line-height: 1.05;
            letter-spacing: -0.03em;
            font-weight: 600;
        }}

        .section ul {{
            margin: 0;
            padding-left: 20px;
        }}

        .section li {{
            margin-bottom: 14px;
        }}

        .footer-link {{
            margin-top: 28px;
            text-align: center;
        }}

        .footer-link a {{
            color: var(--text);
            text-decoration: none;
            border-bottom: 1px solid rgba(31, 26, 23, 0.25);
        }}

        .footer-link a:hover {{
            border-bottom-color: rgba(31, 26, 23, 0.65);
        }}

        @media (max-width: 720px) {{
            .page {{
                padding: 24px 16px 70px;
            }}

            .hero {{
                grid-template-columns: 1fr;
                gap: 14px;
                align-items: start;
            }}

            .brand-logo {{
                width: 78px;
            }}

            .section {{
                padding: 20px 18px 22px;
            }}

            .section h2 {{
                font-size: 26px;
            }}
        }}
    </style>
</head>
<body>
    <div class="page">
        <header class="hero">
            <div>
                <img src="{logo_src}" class="brand-logo" alt="Unique Original Fine Art">
            </div>
            <div class="hero-copy">
                <h1>Buying & Shipping Guidelines</h1>
                <div class="hero-sub">
                    These are general community guidelines. All sales are handled directly between buyer and seller.
                </div>
                <div class="hero-links">
                    <a class="hero-link" href="{index_src}">Back to catalog</a>
                </div>
            </div>
        </header>

        <div class="notice">
            <strong>Please Note</strong>
            Use these guidelines for smoother transactions, safer payments, and better shipping outcomes.
        </div>

        <section class="section">
            <h2>Useful Tips for Buying</h2>
            <ul>
                {buying_items}
            </ul>
        </section>

        <section class="section">
            <h2>Useful Tips for Shipping Art</h2>
            <ul>
                {shipping_items}
            </ul>
        </section>

        <div class="footer-link">
            <a href="{index_src}">Return to the art catalog</a>
        </div>
    </div>
</body>
</html>"""


def generate_html(data, images_path: Path, output_path: Path, title, month_label):
    stats = summary_stats(data)

    def card_html(row):
        image_src = build_image_src(row, output_path, images_path)
        return build_card(row, image_src)

    catalog_cards = "\n".join(card_html(row) for row in data)

    artists = unique_values(data, "artist_name")
    sellers = unique_values(data, "seller_name")
    artist_options = '<option value="">All Artists</option>' + "".join(
        f'<option value="{safe_text(a.lower())}">{safe_text(a)}</option>' for a in artists
    )
    seller_options = '<option value="">All Sellers</option>' + "".join(
        f'<option value="{safe_text(s.lower())}">{safe_text(s)}</option>' for s in sellers
    )
    logo_src = "https://raw.githubusercontent.com/unique-original-fineart/art_catalog/main/assets/logo.png"
    guidelines_src = "guidelines.html"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <link rel="icon" href="assets/favicon.ico">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{safe_text(title)}</title>
    <style>
        :root {{
            --bg: #f5f1ea;
            --card: rgba(255,255,255,0.82);
            --text: #1f1a17;
            --muted: #6f675e;
            --line: #dbd1c4;
            --shadow: 0 18px 40px rgba(35, 27, 20, 0.08);
            --shadow-soft: 0 8px 22px rgba(35, 27, 20, 0.05);
        }}

        * {{
            box-sizing: border-box;
        }}

        html {{
            scroll-behavior: smooth;
        }}

        body {{
            margin: 0;
            color: var(--text);
            background:
                radial-gradient(circle at top left, rgba(255,255,255,0.7), transparent 35%),
                linear-gradient(180deg, #f7f3ed 0%, #f2ece3 100%);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            line-height: 1.45;
        }}

        .page {{
            max-width: 1360px;
            margin: 0 auto;
            padding: 32px 28px 90px;
        }}

        .hero {{
            padding: 4px 0 20px;
            margin-bottom: 20px;
            border-bottom: 1px solid var(--line);
        }}
        .banner-wrap {{
            width: 100%;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 0 0 20px;
        }}

        .banner-logo {{
            max-width: 600px;
            width: 100%;
            height: auto;
            display: block;
        }}

        .centered-link {{
            text-align: center;
            margin-top: 10px;
        }}


        .hero-top {{
            display: grid;
            grid-template-columns: 160px 1fr;
            gap: 28px;
            align-items: center;
        }}

        .brand {{
            display: flex;
            align-items: center;
            justify-content: flex-start;
        }}

        .brand-logo {{
            width: 150px;
            max-width: 100%;
            height: auto;
            display: block;
            filter: drop-shadow(0 8px 18px rgba(0,0,0,0.08));
        }}

        .hero-copy {{
            display: flex;
            flex-direction: column;
            justify-content: center;
            min-width: 0;
            max-width: 760px;
        }}

        h1 {{
            margin: 0;
            font-family: Georgia, "Times New Roman", serif;
            font-size: clamp(28px, 4vw, 48px);
            line-height: 0.96;
            letter-spacing: -0.03em;
            font-weight: 600;
        }}

        .hero-sub {{
            max-width: 640px;
            margin-top: 14px;
            color: var(--muted);
            font-size: 16px;
            line-height: 1.5;
        }}

        .hero-links {{
            margin-top: 14px;
        }}

        .hero-link {{
            color: var(--text);
            text-decoration: none;
            font-size: 14px;
            border-bottom: 1px solid rgba(31, 26, 23, 0.25);
        }}

        .hero-link:hover {{
            border-bottom-color: rgba(31, 26, 23, 0.65);
        }}

        .stats-bar {{
            display: flex;
            align-items: center;
            gap: 0;
            margin-top: 24px;
            padding: 16px 22px;
            background: var(--card);
            border: 1px solid rgba(219, 209, 196, 0.85);
            border-radius: 18px;
            box-shadow: var(--shadow-soft);
            width: fit-content;
            max-width: 100%;
        }}

        .stat-chip {{
            display: flex;
            flex-direction: column;
            gap: 6px;
            padding: 0 18px;
        }}

        .stat-chip:first-child {{
            padding-left: 0;
        }}

        .stat-chip:last-child {{
            padding-right: 0;
        }}

        .stat-chip-label {{
            font-size: 11px;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            color: var(--muted);
            white-space: nowrap;
        }}

        .stat-chip-value {{
            font-family: Georgia, "Times New Roman", serif;
            font-size: 28px;
            line-height: 1;
        }}

        .stat-divider {{
            width: 1px;
            align-self: stretch;
            background: var(--line);
            opacity: 0.9;
        }}

        .section {{
            margin-top: 42px;
        }}

        .section-heading {{
            display: flex;
            justify-content: space-between;
            align-items: end;
            gap: 20px;
            margin-bottom: 18px;
        }}

        .section h3 {{
            margin: 0;
            font-family: Georgia, "Times New Roman", serif;
            font-size: 30px;
            line-height: 1.05;
            letter-spacing: -0.03em;
            font-weight: 600;
        }}

        .section-note {{
            color: var(--muted);
            font-size: 14px;
        }}

        .filters {{
            display: grid;
            grid-template-columns: 2fr repeat(6, 1fr);
            gap: 12px;
            margin: 0 0 20px;
        }}

        .filters input,
        .filters select,
        .download-saved-button {{
            width: 100%;
            padding: 14px 15px;
            border-radius: 14px;
            border: 1px solid var(--line);
            background: rgba(255,255,255,0.92);
            color: var(--text);
            font-size: 14px;
            box-shadow: var(--shadow-soft);
        }}

        
        .download-saved-button {{
            cursor: pointer;
            font-weight: 600;
        }}

        .download-saved-button:disabled {{
            opacity: 0.55;
            cursor: not-allowed;
        }}

        .result-row {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 18px;
            margin-bottom: 18px;
            flex-wrap: wrap;
        }}

        .result-meta {{
            display: flex;
            flex-wrap: wrap;
            gap: 14px;
            align-items: center;
        }}

        .result-count,
        .saved-count {{
            color: var(--muted);
            font-size: 14px;
        }}

        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 28px;
        }}

        .card {{
            background: var(--card);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(219, 209, 196, 0.85);
            border-radius: 26px;
            overflow: hidden;
            box-shadow: var(--shadow);
            display: flex;
            flex-direction: column;
            transition: transform 0.18s ease, box-shadow 0.18s ease;
        }}

        .card:hover {{
            transform: translateY(-3px);
            box-shadow: 0 24px 48px rgba(35, 27, 20, 0.12);
        }}

        .card:hover .art-img {{
            transform: scale(1.03);
        }}

        .card.hidden {{
            display: none;
        }}

        .card-image-wrap {{
            display: flex;
            align-items: center;
            justify-content: center;
            background:
                linear-gradient(180deg, rgba(255,255,255,0.6), rgba(239,232,220,0.9));
            border-bottom: 1px solid var(--line);
            padding: 22px;
            min-height: 340px;
        }}

        .image-open {{
            appearance: none;
            border: none;
            background: transparent;
            padding: 0;
            margin: 0;
            cursor: zoom-in;
            display: flex;
            align-items: center;
            justify-content: center;
            width: 100%;
        }}

        .art-img {{
            max-width: 100%;
            max-height: 380px;
            width: auto;
            height: auto;
            object-fit: contain;
            display: block;
            background: #f3efe8;
            border: 6px solid white;
            border-radius: 8px;
            box-shadow:
                0 2px 6px rgba(0,0,0,0.08),
                0 12px 30px rgba(0,0,0,0.12);
            transition: transform 0.4s ease;
        }}

        .card-body {{
            padding: 22px 22px 24px;
        }}

        .card-header {{
            display: flex;
            justify-content: space-between;
            gap: 16px;
            align-items: start;
        }}

        .artist-name {{
            margin: 0;
            font-family: Georgia, "Times New Roman", serif;
            font-size: 30px;
            line-height: 0.98;
            letter-spacing: -0.035em;
            font-weight: 600;
        }}

        .artwork-title {{
            margin-top: 10px;
            font-size: 16px;
            font-style: italic;
            color: var(--muted);
        }}

        .price {{
            white-space: nowrap;
            font-size: 22px;
            font-weight: 700;
            letter-spacing: -0.02em;
        }}

        .price-drop-price {{
            display: flex;
            flex-direction: column;
            align-items: flex-end;
            gap: 4px;
            line-height: 1.05;
        }}

        .price-drop-label {{
            display: inline-flex;
            align-items: center;
            border-radius: 999px;
            padding: 5px 9px;
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            border: 1px solid var(--line);
            background: #fff4df;
            color: #7a4d00;
        }}

        .price-stack {{
            display: flex;
            flex-direction: column;
            align-items: flex-end;
            gap: 2px;
        }}

        .old-price {{
            color: var(--muted);
            font-size: 15px;
            font-weight: 600;
            text-decoration: line-through;
            text-decoration-thickness: 1.5px;
        }}

        .new-price {{
            color: var(--text);
            font-size: 24px;
            font-weight: 800;
            letter-spacing: -0.03em;
        }}

        .badges {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-top: 16px;
        }}

        .badge,
        .status-pill {{
            display: inline-flex;
            align-items: center;
            border-radius: 999px;
            padding: 7px 11px;
            font-size: 12px;
            font-weight: 600;
            letter-spacing: 0.01em;
            border: 1px solid var(--line);
            background: rgba(255,255,255,0.92);
        }}

        .badge-muted {{
            color: var(--muted);
        }}

        .artwork-category-badge {{
            background: #eef4ff;
            color: #274060;
            border-color: #cbd9ef;
        }}

        .price-drop-badge {{
            background: #fff4df;
            color: #7a4d00;
            border-color: #efd29d;
        }}

        .status-available {{
            background: #edf6ee;
        }}

        .status-pending {{
            background: #fbf3df;
        }}

        .status-sold {{
            background: #f6e5e5;
        }}

        .specs {{
            margin-top: 18px;
            padding-top: 14px;
            border-top: 1px solid var(--line);
        }}

        .spec-row {{
            display: flex;
            justify-content: space-between;
            gap: 18px;
            padding: 7px 0;
        }}

        .spec-label {{
            color: var(--muted);
            font-size: 13px;
            letter-spacing: 0.06em;
            text-transform: uppercase;
        }}

        .spec-value {{
            text-align: right;
            font-size: 14px;
            font-weight: 500;
        }}

        .seller {{
            margin-top: 18px;
            display: flex;
            flex-direction: column;
            gap: 4px;
        }}

        .seller-label {{
            color: var(--muted);
            font-size: 12px;
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }}

        .seller-name {{
            font-size: 18px;
            font-weight: 700;
            line-height: 1.2;
            color: var(--text);
        }}

        .seller-name a {{
            color: var(--text);
            text-decoration: none;
            border-bottom: 1px solid rgba(31, 26, 23, 0.25);
        }}

        .seller-name a:hover {{
            border-bottom-color: rgba(31, 26, 23, 0.65);
        }}

        .seller-contact-note {{
            color: var(--muted);
            font-size: 13px;
            margin-top: 2px;
        }}

        .listing-actions {{
            margin-top: 16px;
        }}

        .save-listing-button,
        .download-listing-button {{
            appearance: none;
            border: 1px solid var(--line);
            background: rgba(255,255,255,0.92);
            color: var(--text);
            padding: 10px 14px;
            border-radius: 999px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.2s ease, transform 0.2s ease, border-color 0.2s ease;
        }}
        .contact-seller-button {{
            display: inline-flex;
            align-items: center;
            width: fit-content;
            margin-top: 8px;
            padding: 10px 14px;
            border-radius: 999px;
            background: #1f1a17;
            color: #ffffff;
            text-decoration: none;
            font-size: 13px;
            font-weight: 600;
            border: 1px solid #1f1a17;
            transition: transform 0.2s ease, opacity 0.2s ease;
        }}

        .contact-seller-button:hover {{
            transform: translateY(-1px);
            opacity: 0.9;
        }}
        .save-listing-button:hover,
        .download-listing-button:hover {{
            transform: translateY(-1px);
        }}

        .save-listing-button.is-saved {{
            background: #1f1a17;
            color: #ffffff;
            border-color: #1f1a17;
        }}

        .notes {{
            margin-top: 12px;
            font-size: 14px;
            color: var(--text);
        }}

        #backToTop {{
            position: fixed;
            bottom: 20px;
            right: 20px;
            width: 46px;
            height: 46px;
            border-radius: 50%;
            border: none;
            background: #1f1a17;
            color: #ffffff;
            font-size: 20px;
            cursor: pointer;
            box-shadow: 0 8px 20px rgba(0,0,0,0.20);
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 1000;
        }}

        #backToTop:hover {{
            opacity: 0.88;
        }}

        .lightbox {{
            position: fixed;
            inset: 0;
            background: rgba(20, 16, 12, 0.92);
            display: none;
            align-items: center;
            justify-content: center;
            padding: 20px;
            z-index: 2000;
        }}

        .lightbox.is-open {{
            display: flex;
        }}

        .lightbox-stage {{
            position: relative;
            width: 100%;
            height: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: auto;
            -webkit-overflow-scrolling: touch;
        }}

        .lightbox-image {{
            max-width: min(92vw, 1400px);
            max-height: 92vh;
            width: auto;
            height: auto;
            object-fit: contain;
            border-radius: 10px;
            background: #ffffff;
            box-shadow: 0 20px 60px rgba(0,0,0,0.35);
            touch-action: pinch-zoom;
        }}

        .lightbox-close {{
            position: absolute;
            top: 18px;
            right: 18px;
            width: 44px;
            height: 44px;
            border-radius: 50%;
            border: none;
            background: rgba(255,255,255,0.14);
            color: #ffffff;
            font-size: 28px;
            line-height: 1;
            cursor: pointer;
            z-index: 2100;
        }}

        .lightbox-close:hover {{
            background: rgba(255,255,255,0.22);
        }}

        .lightbox-hint {{
            position: absolute;
            left: 50%;
            bottom: 18px;
            transform: translateX(-50%);
            color: rgba(255,255,255,0.78);
            font-size: 13px;
            letter-spacing: 0.02em;
            text-align: center;
            z-index: 2100;
        }}

        
        .loading-overlay {{
            position: fixed;
            inset: 0;
            background: rgba(20, 16, 12, 0.50);
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 3000;
            padding: 20px;
        }}

        .loading-overlay.is-open {{
            display: flex;
        }}

        .loading-box {{
            background: rgba(255,255,255,0.96);
            border: 1px solid rgba(219, 209, 196, 0.85);
            border-radius: 20px;
            box-shadow: 0 18px 40px rgba(35, 27, 20, 0.15);
            padding: 22px 24px;
            min-width: 260px;
            text-align: center;
        }}

        .loading-title {{
            font-family: Georgia, "Times New Roman", serif;
            font-size: 24px;
            margin: 0 0 8px;
        }}

        .loading-text {{
            color: var(--muted);
            font-size: 14px;
            margin: 0;
        }}

        @media (max-width: 1200px) {{
            .filters {{
                grid-template-columns: 1fr 1fr 1fr;
            }}
        }}

        @media (max-width: 980px) {{
            .hero-top {{
                grid-template-columns: 90px 1fr;
                gap: 18px;
            }}

            .brand-logo {{
                width: 82px;
            }}

            .stats-bar {{
                width: 100%;
                min-width: 0;
            }}
        }}
        @media (max-width: 720px) {{
            .banner-logo {{
                max-width: 90%;
            }}
        }}
        @media (max-width: 720px) {{
            .page {{
                padding: 24px 16px 70px;
            }}

            .hero {{
                padding: 0 0 12px;
                margin-bottom: 24px;
            }}

            .hero-top {{
                grid-template-columns: 1fr;
                gap: 14px;
                align-items: start;
            }}

            .brand {{
                justify-content: flex-start;
            }}

            .brand-logo {{
                width: 74px;
                max-width: 50%;
            }}

            .hero-copy {{
                max-width: 100%;
            }}

            .hero-sub {{
                margin-top: 10px;
                font-size: 15px;
            }}

            .stats-bar {{
                flex-direction: column;
                align-items: flex-start;
                gap: 12px;
                width: 100%;
                padding: 16px 18px;
            }}

            .stat-chip {{
                padding: 0;
            }}

            .stat-divider {{
                width: 100%;
                height: 1px;
            }}

            .filters {{
                grid-template-columns: 1fr;
                position: static;
                background: transparent;
                backdrop-filter: none;
                padding: 0;
                margin-bottom: 16px;
                gap: 10px;
            }}

            .filters input,
            .filters select,
            .download-saved-button {{
                padding: 12px 14px;
                font-size: 16px;
            }}

            .card-header {{
                flex-direction: column;
            }}

            .price {{
                white-space: normal;
            }}

            .price-drop-price,
            .price-stack {{
                align-items: flex-start;
            }}

            .card-image-wrap {{
                min-height: 280px;
                padding: 18px;
            }}

            .art-img {{
                max-height: 320px;
            }}

            .seller-name {{
                font-size: 17px;
            }}

            #backToTop {{
                bottom: 16px;
                right: 16px;
                width: 48px;
                height: 48px;
            }}

            .lightbox {{
                padding: 12px;
            }}

            .lightbox-close {{
                top: 12px;
                right: 12px;
            }}

            .lightbox-hint {{
                bottom: 12px;
                font-size: 12px;
            }}

            /* === Mobile 2-up grid with rightsized cards ===
               To switch to 3-up (very compact), change `repeat(2, ...)` below to `repeat(3, ...)`
               and you'll likely want to halve the font sizes too. To revert to the original
               1-up layout, change `repeat(2, minmax(0, 1fr))` to `1fr`. */
            .grid {{
                grid-template-columns: repeat(2, minmax(0, 1fr));
                gap: 14px;
            }}

            .card {{
                border-radius: 16px;
            }}

            .card-image-wrap {{
                min-height: 160px;
                padding: 12px;
            }}

            .art-img {{
                max-height: 200px;
                border-width: 3px;
                border-radius: 6px;
            }}

            .card-body {{
                padding: 12px;
            }}

            .card-header {{
                gap: 4px;
            }}

            .artist-name {{
                font-size: 18px;
                line-height: 1.1;
                letter-spacing: -0.025em;
            }}

            .artwork-title {{
                font-size: 12px;
                margin-top: 4px;
            }}

            .price {{
                font-size: 17px;
                margin-top: 6px;
            }}

            .price-drop-label {{
                font-size: 9px;
                padding: 3px 6px;
                letter-spacing: 0.06em;
            }}

            .old-price {{
                font-size: 12px;
            }}

            .new-price {{
                font-size: 17px;
            }}

            .badges {{
                gap: 4px;
                margin-top: 10px;
            }}

            .badge,
            .status-pill {{
                padding: 4px 8px;
                font-size: 10px;
            }}

            .specs {{
                margin-top: 10px;
                padding-top: 8px;
            }}

            .spec-row {{
                gap: 8px;
                padding: 4px 0;
            }}

            .spec-label {{
                font-size: 10px;
            }}

            .spec-value {{
                font-size: 12px;
            }}

            .seller {{
                margin-top: 12px;
            }}

            .seller-label {{
                font-size: 10px;
            }}

            .seller-name {{
                font-size: 14px;
            }}

            .contact-seller-button {{
                font-size: 11px;
                padding: 7px 10px;
                margin-top: 6px;
            }}

            .listing-actions {{
                margin-top: 10px;
            }}

            .save-listing-button {{
                font-size: 12px;
                padding: 7px 10px;
            }}

            .notes {{
                font-size: 12px;
                margin-top: 8px;
                line-height: 1.4;
            }}
        }}
    </style>
</head>
<body>
    <div class="page">
        <header class="hero">
            <div class="banner-wrap">
                <img src="{logo_src}" class="banner-logo" alt="Canvas Circle">
            </div>

            <div class="hero-links centered-link">
                <a class="hero-link" href="{guidelines_src}">Buying/Shipping Guidelines</a>
            </div>

            <div class="stats-bar">
                <div class="stat-chip">
                    <span class="stat-chip-label">Available Listings</span>
                    <span class="stat-chip-value">{stats["listing_count"]}</span>
                </div>

                <div class="stat-divider"></div>

                <div class="stat-chip">
                    <span class="stat-chip-label">Artists</span>
                    <span class="stat-chip-value">{stats["artist_count"]}</span>
                </div>

                <div class="stat-divider"></div>

                <div class="stat-chip">
                    <span class="stat-chip-label">Sellers</span>
                    <span class="stat-chip-value">{stats["seller_count"]}</span>
                </div>
            </div>
        </header>

        <section class="section" id="full-catalog">
            <div class="section-heading">
                <h3>Full Catalog</h3>
                <div class="section-note">Browse by seller, artist, category, price, recency, or saved listings</div>
            </div>

            <div class="filters">
                <input type="text" id="searchInput" placeholder="Search artist, title, seller...">
                <select id="savedFilter">
                    <option value="">All Listings</option>
                    <option value="saved">Saved Only</option>
                    <option value="priceDrops">Price Drops</option>
                </select>
                <select id="sellerFilter">{seller_options}</select>
                <select id="artistFilter">{artist_options}</select>
                <select id="categoryFilter">
                    <option value="">Artwork Category</option>
                    <option value="unique/original">Unique/Original</option>
                    <option value="limited edition">Limited Edition</option>
                </select>
                <select id="priceFilter">
                    <option value="">All Prices</option>
                    <option value="under1000">Under $1,000</option>
                    <option value="1000to2499">$1,000–$2,499</option>
                    <option value="2500to4999">$2,500–$4,999</option>
                    <option value="5000plus">$5,000+</option>
                    <option value="unknown">Price on Request / Unknown</option>
                </select>
                <select id="sortFilter">
                    <option value="newest">Sort: Newest</option>
                    <option value="oldest">Sort: Oldest</option>
                    <option value="priceDesc">Price: High to Low</option>
                    <option value="priceAsc">Price: Low to High</option>
                    <option value="artistAsc">Artist: A to Z</option>
                    <option value="artistDesc">Artist: Z to A</option>
                </select>
            </div>

            <div class="result-row">
                <div class="result-meta">
                    <div class="result-count" id="resultCount"></div>
                    <div class="saved-count" id="savedCount"></div>
                </div>
                
            </div>

            <div class="grid" id="catalogGrid">
                {catalog_cards}
            </div>
        </section>
    </div>

    <button id="backToTop" aria-label="Back to top">↑</button>

    <div class="loading-overlay" id="loadingOverlay" aria-hidden="true">
        <div class="loading-box">
            <h4 class="loading-title" id="loadingTitle">Preparing PDF...</h4>
            <p class="loading-text" id="loadingText">Please wait while your download is generated.</p>
        </div>
    </div>

    <div class="lightbox" id="lightbox" aria-hidden="true">
        <button class="lightbox-close" id="lightboxClose" aria-label="Close image viewer">×</button>
        <div class="lightbox-stage" id="lightboxStage">
            <img class="lightbox-image" id="lightboxImage" src="" alt="">
        </div>
        <div class="lightbox-hint">Tap outside or × to close. Pinch to zoom on mobile.</div>
    </div>


    <script>
        const STORAGE_KEY = "savedListings";

        const searchInput = document.getElementById("searchInput");
        const savedFilter = document.getElementById("savedFilter");
        const sellerFilter = document.getElementById("sellerFilter");
        const artistFilter = document.getElementById("artistFilter");
        const categoryFilter = document.getElementById("categoryFilter");
        const priceFilter = document.getElementById("priceFilter");
        const sortFilter = document.getElementById("sortFilter");
        const grid = document.getElementById("catalogGrid");
        const cards = Array.from(document.querySelectorAll("#catalogGrid .card"));
        const resultCount = document.getElementById("resultCount");
        const savedCount = document.getElementById("savedCount");
        const backToTop = document.getElementById("backToTop");

        const lightbox = document.getElementById("lightbox");
        const lightboxImage = document.getElementById("lightboxImage");
        const lightboxClose = document.getElementById("lightboxClose");
        const lightboxStage = document.getElementById("lightboxStage");
        const imageButtons = Array.from(document.querySelectorAll(".image-open"));
        const saveButtons = Array.from(document.querySelectorAll(".save-listing-button"));


        const loadingOverlay = document.getElementById("loadingOverlay");
        const loadingTitle = document.getElementById("loadingTitle");
        const loadingText = document.getElementById("loadingText");

        function setLoadingState(isOpen, title = "Preparing Image...", text = "Please wait while your download is generated.") {{
            loadingOverlay.classList.toggle("is-open", isOpen);
            loadingOverlay.setAttribute("aria-hidden", isOpen ? "false" : "true");
            loadingTitle.textContent = title;
            loadingText.textContent = text;
            document.body.style.overflow = isOpen ? "hidden" : "";
        }}

        function getSavedListings() {{
            try {{
                const raw = localStorage.getItem(STORAGE_KEY);
                const parsed = raw ? JSON.parse(raw) : [];
                return Array.isArray(parsed) ? parsed : [];
            }} catch (error) {{
                return [];
            }}
        }}

        function setSavedListings(savedIds) {{
            localStorage.setItem(STORAGE_KEY, JSON.stringify(savedIds));
        }}

        function isSaved(listingId) {{
            return getSavedListings().includes(listingId);
        }}

        function updateSavedButtons() {{
            const savedIds = getSavedListings();
            saveButtons.forEach((button) => {{
                const id = button.dataset.listingId;
                const saved = savedIds.includes(id);
                button.classList.toggle("is-saved", saved);
                button.textContent = saved ? "♥ Saved" : "♡ Save Listing";
                button.setAttribute("aria-pressed", saved ? "true" : "false");
            }});
            savedCount.textContent = `${{savedIds.length}} saved`;
        }}

        function toggleSavedListing(listingId) {{
            const savedIds = getSavedListings();
            const index = savedIds.indexOf(listingId);

            if (index >= 0) {{
                savedIds.splice(index, 1);
            }} else {{
                savedIds.push(listingId);
            }}

            setSavedListings(savedIds);
            updateSavedButtons();

            
            if (savedFilter.value === "saved") {{
                applyFilters();
            }}
        }}

        function matchesPriceBand(priceBand, filterBand) {{
            if (!filterBand) return true;
            return priceBand === filterBand;
        }}

        function sortCards(visibleCards) {{
            const mode = sortFilter.value;

            visibleCards.sort((a, b) => {{
                const priceA = Number(a.dataset.price || -1);
                const priceB = Number(b.dataset.price || -1);
                const newestA = Number(a.dataset.newest || 0);
                const newestB = Number(b.dataset.newest || 0);
                const artistA = (a.dataset.artist || "").toLowerCase();
                const artistB = (b.dataset.artist || "").toLowerCase();

                if (mode === "newest") return newestB - newestA;
                if (mode === "oldest") return newestA - newestB;

                if (mode === "priceDesc") {{
                    const safeA = priceA === -1 ? -Infinity : priceA;
                    const safeB = priceB === -1 ? -Infinity : priceB;
                    return safeB - safeA;
                }}

                if (mode === "priceAsc") {{
                    const safeA = priceA === -1 ? Infinity : priceA;
                    const safeB = priceB === -1 ? Infinity : priceB;
                    return safeA - safeB;
                }}

                if (mode === "artistAsc") return artistA.localeCompare(artistB);
                if (mode === "artistDesc") return artistB.localeCompare(artistA);

                return 0;
            }});

            visibleCards.forEach(card => grid.appendChild(card));
        }}

        function applyFilters() {{
            const search = searchInput.value.trim().toLowerCase();
            const savedOnly = savedFilter.value === "saved";
            const priceDropsOnly = savedFilter.value === "priceDrops";
            const seller = sellerFilter.value;
            const artist = artistFilter.value;
            const category = categoryFilter.value;
            const priceBand = priceFilter.value;
            const savedIds = getSavedListings();

            let visibleCards = [];

            cards.forEach(card => {{
                const listingId = card.dataset.listingId || "";
                const sellerValue = card.dataset.seller || "";
                const artistValue = card.dataset.artist || "";
                const categoryValue = card.dataset.category || "";
                const cardPriceBand = card.dataset.priceBand || "";
                const fullText = card.dataset.search || "";
                const isPriceDrop = card.dataset.priceDrop === "true";

                const matchesSearch = !search || fullText.includes(search);
                const matchesSaved = !savedOnly || savedIds.includes(listingId);
                const matchesPriceDrop = !priceDropsOnly || isPriceDrop;
                const matchesSeller = !seller || sellerValue === seller;
                const matchesArtist = !artist || artistValue === artist;
                const matchesCategory = !category || categoryValue === category;
                const matchesPrice = matchesPriceBand(cardPriceBand, priceBand);

                const visible = matchesSearch && matchesSaved && matchesPriceDrop && matchesSeller && matchesArtist && matchesCategory && matchesPrice;
                card.classList.toggle("hidden", !visible);

                if (visible) {{
                    visibleCards.push(card);
                }}
            }});

            sortCards(visibleCards);
            resultCount.textContent = `${{visibleCards.length}} listing${{visibleCards.length === 1 ? "" : "s"}} shown`;
        }}



        


    

        function openLightbox(src, alt) {{
            lightboxImage.src = src;
            lightboxImage.alt = alt || "Artwork";
            lightbox.classList.add("is-open");
            lightbox.setAttribute("aria-hidden", "false");
            document.body.style.overflow = "hidden";
        }}

        function closeLightbox() {{
            lightbox.classList.remove("is-open");
            lightbox.setAttribute("aria-hidden", "true");
            lightboxImage.src = "";
            lightboxImage.alt = "";
            document.body.style.overflow = "";
        }}

        imageButtons.forEach((button) => {{
            button.addEventListener("click", () => {{
                openLightbox(button.dataset.fullsrc, button.dataset.alt);
            }});
        }});

        saveButtons.forEach((button) => {{
            button.addEventListener("click", () => {{
                toggleSavedListing(button.dataset.listingId);
            }});
        }});

       

        

        lightboxClose.addEventListener("click", closeLightbox);

        lightbox.addEventListener("click", (event) => {{
            if (event.target === lightbox || event.target === lightboxStage) {{
                closeLightbox();
            }}
        }});

        document.addEventListener("keydown", (event) => {{
            if (event.key === "Escape" && lightbox.classList.contains("is-open")) {{
                closeLightbox();
            }}
        }});

        window.addEventListener("scroll", () => {{
            if (window.scrollY > 400) {{
                backToTop.style.display = "flex";
            }} else {{
                backToTop.style.display = "none";
            }}
        }});

        backToTop.addEventListener("click", () => {{
            window.scrollTo({{
                top: 0,
                behavior: "smooth"
            }});
        }});

        [searchInput, savedFilter, sellerFilter, artistFilter, categoryFilter, priceFilter, sortFilter].forEach((el) => {{
            el.addEventListener("input", applyFilters);
            el.addEventListener("change", applyFilters);
        }});

        updateSavedButtons();
        applyFilters();
    </script>
</body>
</html>"""


def main():
    import argparse

    parser = argparse.ArgumentParser()
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument("--csv", help="Local CSV file path. Can be raw Google Form export or already-normalized CSV.")
    source_group.add_argument("--sheet-url", help="Public Google Sheets CSV export URL.")
    source_group.add_argument("--sheet-id", help="Google Sheet ID. Use with --gid to fetch the public CSV export directly.")

    parser.add_argument("--gid", default="0", help="Google Sheet tab gid. Defaults to 0.")
    parser.add_argument("--images", default="", help="Optional local images directory fallback. Drive URLs are preferred.")
    parser.add_argument("--output", required=True)
    parser.add_argument("--title", default="Art Catalog")
    parser.add_argument("--month-label", default="Monthly Art Listings")
    args = parser.parse_args()

    if args.sheet_id:
        data_source = build_google_sheet_csv_url(args.sheet_id, args.gid)
    elif args.sheet_url:
        data_source = args.sheet_url
    else:
        data_source = Path(args.csv).expanduser().resolve()

    images_path = Path(args.images).expanduser().resolve() if args.images else Path(".").resolve()
    output_path = Path(args.output).expanduser().resolve()

    data = load_data(data_source)

    html_text = generate_html(
        data=data,
        images_path=images_path,
        output_path=output_path,
        title=args.title,
        month_label=args.month_label,
    )

    guidelines_html = generate_guidelines_html(
        output_path=output_path,
        title=args.title,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html_text, encoding="utf-8")

    guidelines_path = output_path.parent / "guidelines.html"
    guidelines_path.write_text(guidelines_html, encoding="utf-8")

    print(f"Loaded {len(data)} approved public listings.")
    print(f"Catalog generated: {output_path}")
    print(f"Guidelines generated: {guidelines_path}")


if __name__ == "__main__":
    main()