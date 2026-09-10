import json
import urllib.request
import urllib.error

TEST_CODES = {
    "2330": "台積電",
    "0050": "元大台灣50"
}

TWSE_URL = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"


def fetch_json(url):

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "Chrome/120.0 Safari/537.36"
            ),
            "Accept": "application/json",
            "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8"
        }
    )

    try:

        with urllib.request.urlopen(
            request,
            timeout=30
        ) as response:

            raw_data = response.read()

            print(
                "HTTP status:",
                response.status
            )

            print(
                "Content-Type:",
                response.headers.get(
                    "Content-Type"
                )
            )

            print(
                "Received bytes:",
                len(raw_data)
            )

            text = raw_data.decode(
                "utf-8",
                errors="replace"
            )

            print(
                "Response preview:",
                text[:300]
            )

            if not text.strip():

                raise RuntimeError(
                    "TWSE回傳空白內容"
                )

            try:

                return json.loads(text)

            except json.JSONDecodeError:

                raise RuntimeError(
                    "TWSE回傳的內容不是JSON。"
                    f"前300字：{text[:300]}"
                )

    except urllib.error.HTTPError as error:

        raise RuntimeError(
            f"TWSE HTTP錯誤：{error.code}"
        )

    except urllib.error.URLError as error:

        raise RuntimeError(
            f"無法連線TWSE：{error.reason}"
        )


def main():

    data = fetch_json(TWSE_URL)

    results = []

    for item in data:

        code = item.get("Code")

        if code not in TEST_CODES:
            continue

        results.append({
            "name": TEST_CODES[code],
            "code": code,
            "closing_price": item.get(
                "ClosingPrice"
            ),
            "change": item.get(
                "Change"
            )
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
    
