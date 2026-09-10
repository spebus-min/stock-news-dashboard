import json
import urllib.request

TEST_CODES = {
    "2330": "台積電",
    "0050": "元大台灣50"
}

TWSE_URL = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"

def fetch_json(url):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0"
        }
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(
            response.read().decode("utf-8")
        )


def main():

    data = fetch_json(TWSE_URL)

    results = []

    for item in data:

        code = item.get("Code")

        if code not in TEST_CODES:
            continue

        closing_price = item.get("ClosingPrice")
        change = item.get("Change")

        results.append({
            "name": TEST_CODES[code],
            "code": code,
            "closing_price": closing_price,
            "change": change
        })

    output = {
        "stocks": results
    }

    with open(
        "market_data.json",
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            output,
            file,
            ensure_ascii=False,
            indent=2
        )

    print(
        json.dumps(
            output,
            ensure_ascii=False,
            indent=2
        )
    )


if __name__ == "__main__":
    main()
