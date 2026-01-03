from __future__ import annotations

import html
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

BASE_DIR = Path(__file__).resolve().parent
ORDERS_PATH = BASE_DIR / "orders.json"

MENU_PRICING = {
    "Classic Turkey": 8.5,
    "Veggie Delight": 7.0,
    "Spicy Italian": 9.25,
    "BBQ Chicken": 9.5,
    "Breakfast Melt": 8.0,
}

SIZE_MULTIPLIER = {
    "Half": 0.75,
    "Full": 1.0,
    "Footlong": 1.4,
}

EXTRA_PRICING = {
    "Extra Cheese": 1.0,
    "Avocado": 1.5,
    "Bacon": 1.75,
    "Jalapenos": 0.75,
}


@dataclass
class Order:
    order_id: str
    placed_at: str
    customer_name: str
    sandwich: str
    size: str
    extras: list[str]
    payment_method: str
    payment_status: str
    total: float
    special_instructions: str


def load_orders() -> list[Order]:
    if not ORDERS_PATH.exists():
        return []
    try:
        raw_orders = json.loads(ORDERS_PATH.read_text())
    except json.JSONDecodeError:
        return []
    return [Order(**order) for order in raw_orders]


def save_orders(orders: list[Order]) -> None:
    ORDERS_PATH.write_text(json.dumps([asdict(order) for order in orders], indent=2))


def calculate_total(sandwich: str, size: str, extras: list[str]) -> float:
    base_price = MENU_PRICING.get(sandwich, 0)
    size_factor = SIZE_MULTIPLIER.get(size, 1.0)
    extras_total = sum(EXTRA_PRICING.get(extra, 0) for extra in extras)
    total = (base_price * size_factor) + extras_total
    return round(total, 2)


def build_order_cards(orders: list[Order]) -> str:
    if not orders:
        return """
        <div class="order-item">
          <strong>No orders yet.</strong>
          <div>Be the first to send a sandwich into production.</div>
        </div>
        """

    cards = []
    for order in orders[-8:][::-1]:
        extras_count = len(order.extras)
        note = (
            f"<div>Note: {html.escape(order.special_instructions)}</div>"
            if order.special_instructions
            else ""
        )
        cards.append(
            f"""
        <div class="order-item">
          <div>
            <span>#{html.escape(order.order_id)}</span>
            <span class="pill">{html.escape(order.payment_status)}</span>
          </div>
          <div>{html.escape(order.placed_at)} • {html.escape(order.customer_name)}</div>
          <div>{html.escape(order.size)} {html.escape(order.sandwich)} ({extras_count} extras)</div>
          <div>Total: ${order.total:.2f}</div>
          {note}
        </div>
        """
        )
    return "\n".join(cards)


def build_options(options: dict[str, float], format_label: str) -> str:
    rows = []
    for name, price in options.items():
        rows.append(
            f"""
        <option value="{html.escape(name)}">{html.escape(name)} — {format_label.format(price)}</option>
        """
        )
    return "\n".join(rows)


def build_extras(options: dict[str, float]) -> str:
    rows = []
    for name, price in options.items():
        rows.append(
            f"""
        <label>
          <input type="checkbox" name="extras" value="{html.escape(name)}" />
          {html.escape(name)}
          <span class="price-badge">+${price:.2f}</span>
        </label>
        """
        )
    return "\n".join(rows)


def render_page(success: str | None, orders: list[Order]) -> str:
    banner = (
        f"""
        <div class="status-banner">
          Order {html.escape(success)} confirmed! Payment marked as paid.
        </div>
        """
        if success
        else ""
    )

    return f"""
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Stacked & Baked - Sandwich Orders</title>
    <link
      href="https://fonts.googleapis.com/css2?family=Manrope:wght@300;500;700&display=swap"
      rel="stylesheet"
    />
    <style>
      :root {{
        color-scheme: light;
        font-family: "Manrope", sans-serif;
        background: #f5f3ef;
        color: #1e1b16;
      }}

      body {{
        margin: 0;
        padding: 32px;
      }}

      .layout {{
        display: grid;
        gap: 24px;
        grid-template-columns: minmax(0, 1.2fr) minmax(0, 1fr);
      }}

      h1 {{
        margin: 0 0 8px;
        font-size: 2.4rem;
      }}

      h2 {{
        margin: 0 0 12px;
        font-size: 1.6rem;
      }}

      p {{
        margin: 0 0 12px;
        line-height: 1.5;
      }}

      .card {{
        background: #ffffff;
        border-radius: 20px;
        padding: 24px;
        box-shadow: 0 18px 40px rgba(30, 27, 22, 0.12);
      }}

      .status-banner {{
        background: #ffe9cc;
        border-radius: 14px;
        padding: 12px 16px;
        margin-bottom: 16px;
        font-weight: 600;
      }}

      .order-grid {{
        display: grid;
        gap: 16px;
      }}

      form {{
        display: grid;
        gap: 16px;
      }}

      label {{
        font-weight: 600;
        display: block;
        margin-bottom: 6px;
      }}

      input[type="text"],
      select,
      textarea {{
        width: 100%;
        padding: 10px 12px;
        border-radius: 12px;
        border: 1px solid #d7d2c9;
        font-size: 0.95rem;
        background: #faf8f5;
      }}

      textarea {{
        resize: vertical;
        min-height: 80px;
      }}

      .options {{
        display: grid;
        gap: 8px;
      }}

      .options label {{
        display: flex;
        gap: 8px;
        font-weight: 500;
      }}

      .price-badge {{
        font-size: 0.9rem;
        color: #5c5244;
      }}

      button {{
        border: none;
        padding: 12px 18px;
        border-radius: 14px;
        background: #1e1b16;
        color: #ffffff;
        font-size: 1rem;
        font-weight: 600;
        cursor: pointer;
      }}

      .order-item {{
        border-radius: 16px;
        background: #f7f2ea;
        padding: 16px;
        display: grid;
        gap: 6px;
      }}

      .order-item span {{
        font-weight: 600;
      }}

      .pill {{
        display: inline-block;
        padding: 4px 10px;
        border-radius: 999px;
        background: #efe6da;
        font-size: 0.8rem;
        font-weight: 600;
        margin-right: 6px;
      }}

      @media (max-width: 900px) {{
        body {{
          padding: 20px;
        }}

        .layout {{
          grid-template-columns: 1fr;
        }}
      }}
    </style>
  </head>
  <body>
    <div class="layout">
      <section class="card">
        <h1>Stacked &amp; Baked</h1>
        <p>
          Fake sandwich builder with a very real vibe. Build your order, run a
          simulated payment, and the kitchen dashboard logs it instantly.
        </p>
        {banner}
        <form action="/order" method="post">
          <div>
            <label for="customer_name">Name for the order</label>
            <input
              id="customer_name"
              name="customer_name"
              type="text"
              placeholder="Sammy Sandwich"
              required
            />
          </div>
          <div>
            <label for="sandwich">Pick a sandwich</label>
            <select id="sandwich" name="sandwich">
              {build_options(MENU_PRICING, "${:.2f}")}
            </select>
          </div>
          <div>
            <label for="size">Select a size</label>
            <select id="size" name="size">
              {build_options(SIZE_MULTIPLIER, "{:.2f}x")}
            </select>
          </div>
          <div>
            <label>Add extras</label>
            <div class="options">
              {build_extras(EXTRA_PRICING)}
            </div>
          </div>
          <div>
            <label for="payment_method">Fake payment method</label>
            <select id="payment_method" name="payment_method">
              <option value="Tap-to-Pay">Tap-to-Pay</option>
              <option value="Gift Card">Gift Card</option>
              <option value="Promo Wallet">Promo Wallet</option>
              <option value="Sandwich Points">Sandwich Points</option>
            </select>
          </div>
          <div>
            <label for="instructions">Special instructions</label>
            <textarea
              id="instructions"
              name="instructions"
              placeholder="Allergic to pickles, extra toast, cut diagonally..."
            ></textarea>
          </div>
          <button type="submit">Submit order &amp; run fake payment</button>
        </form>
      </section>
      <section class="card">
        <h2>Order activity log</h2>
        <p>Latest incoming orders with simulated payment status.</p>
        <div class="order-grid">
          {build_order_cards(orders)}
        </div>
      </section>
    </div>
  </body>
</html>
"""


class SandwichHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path.startswith("/"):
            parsed = urlparse(self.path)
            if parsed.path != "/":
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            success = parse_qs(parsed.query).get("success", [None])[0]
            orders = load_orders()
            html_body = render_page(success, orders)
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html_body.encode("utf-8"))))
            self.end_headers()
            self.wfile.write(html_body.encode("utf-8"))
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        if self.path != "/order":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        content_length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(content_length).decode("utf-8")
        form = parse_qs(body)

        customer_name = (form.get("customer_name", ["Guest"])[0].strip()) or "Guest"
        sandwich = form.get("sandwich", ["Classic Turkey"])[0]
        size = form.get("size", ["Full"])[0]
        extras = form.get("extras", [])
        payment_method = form.get("payment_method", ["Tap-to-Pay"])[0]
        instructions = form.get("instructions", [""])[0].strip()

        total = calculate_total(sandwich, size, extras)
        order = Order(
            order_id=str(uuid4())[:8],
            placed_at=datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M"),
            customer_name=customer_name,
            sandwich=sandwich,
            size=size,
            extras=extras,
            payment_method=payment_method,
            payment_status="Paid (simulated)",
            total=total,
            special_instructions=instructions,
        )

        orders = load_orders()
        orders.append(order)
        save_orders(orders)

        self.send_response(HTTPStatus.SEE_OTHER)
        self.send_header("Location", f"/?success={order.order_id}")
        self.end_headers()


def run_server(host: str = "0.0.0.0", port: int = 5000) -> None:
    server = HTTPServer((host, port), SandwichHandler)
    print(f"Serving fake sandwich platform on http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run_server()
