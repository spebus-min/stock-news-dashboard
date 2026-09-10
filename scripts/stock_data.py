import json
import urllib.request
import urllib.error
from datetime import datetime

TWSE_URL = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
TPEX_URL = "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_daily_close_quotes"


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

            text = raw_data.decode(
                "utf-8",
                errors="replace"
            )

            if not text.strip():
                raise RuntimeError(
                    f"API回傳空白內容：{url}"
                )

            try:
                return json.loads(text)

            except json.JSONDecodeError:

                raise RuntimeError(
                    f"API回傳內容不是JSON：{url}"
                )

    except urllib.error.HTTPError as error:

        raise RuntimeError(
            f"HTTP錯誤：{error.code}｜{url}"
        )

    except urllib.error.URLError as error:

        raise RuntimeError(
            f"連線失敗：{error.reason}｜{url}"
        )


def to_float(value):

    if value is None:
        return None

    text = str(value).strip()

    text = (
        text
        .replace(",", "")
        .replace("+", "")
    )

    if text in ["", "--", "---", "N/A"]:
        return None

    try:
        return float(text)

    except ValueError:
        return None


def calculate_change_percent(
    closing_price,
    change
):

    close = to_float(closing_price)
    change_value = to_float(change)

    if close is None or change_value is None:
        return None

    previous_close = close - change_value

    if previous_close == 0:
        return None

    percent = (
        change_value
        / previous_close
        * 100
    )

    return round(percent, 2)


def load_stock_list():

    with open(
        "stocks.json",
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


def build_stock_lookup(stocks):

    return {
        stock["code"]: stock
        for stock in stocks
    }


def process_twse(
    twse_data,
    stock_lookup
):

    results = []

    for item in twse_data:

        code = str(
            item.get("Code", "")
        ).strip()

        if code not in stock_lookup:
            continue

        stock = stock_lookup[code]

        if stock["market"] != "TWSE":
            continue

        closing_price = (
            item.get("ClosingPrice")
        )

        change = (
            item.get("Change")
        )

        change_percent = (
            calculate_change_percent(
                closing_price,
                change
            )
        )

        results.append({
            "name": stock["name"],
            "code": code,
            "market": "TWSE",
            "type": stock["type"],
            "closing_price": closing_price,
            "change": change,
            "change_percent": change_percent
        })

    return results


def find_first(
    item,
    possible_keys
):

    for key in possible_keys:

        if key in item:
            return item[key]

    return None


def process_tpex(
    tpex_data,
    stock_lookup
):

    results = []

    for item in tpex_data:

        code = find_first(
            item,
            [
                "SecuritiesCompanyCode",
                "SecuritiesCompanyCode ",
                "Code",
                "證券代號"
            ]
        )

        if code is None:
            continue

        code = str(code).strip()

        if code not in stock_lookup:
            continue

        stock = stock_lookup[code]

        if stock["market"] != "TPEx":
            continue

        closing_price = find_first(
            item,
            [
                "Close",
                "ClosePrice",
                "ClosingPrice",
                "收盤"
            ]
        )

        change = find_first(
            item,
            [
                "Change",
                "ChangePrice",
                "漲跌"
            ]
        )

        change_percent = (
            calculate_change_percent(
                closing_price,
                change
            )
        )

        results.append({
            "name": stock["name"],
            "code": code,
            "market": "TPEx",
            "type": stock["type"],
            "closing_price": closing_price,
            "change": change,
            "change_percent": change_percent
        })

    return results


def main():

    stocks = load_stock_list()

    stock_lookup = (
        build_stock_lookup(stocks)
    )

    print(
        f"自選股共{len(stocks)}檔"
    )

    print("取得TWSE資料……")

    twse_data = fetch_json(
        TWSE_URL
    )

    print(
        f"TWSE API共回傳"
        f"{len(twse_data)}筆資料"
    )

    print("取得TPEx資料……")

    tpex_data = fetch_json(
        TPEX_URL
    )

    print(
        f"TPEx API共回傳"
        f"{len(tpex_data)}筆資料"
    )

    results = []

    results.extend(
        process_twse(
            twse_data,
            stock_lookup
        )
    )

    results.extend(
        process_tpex(
            tpex_data,
            stock_lookup
        )
    )

    found_codes = {
        item["code"]
        for item in results
    }

    missing = []

    for stock in stocks:

        if stock["code"] not in found_codes:

            missing.append({
                "name": stock["name"],
                "code": stock["code"],
                "market": stock["market"]
            })

    output = {

        "updated_at": (
            datetime.now()
            .strftime("%Y-%m-%d %H:%M:%S")
        ),

        "total_watchlist":
            len(stocks),

        "total_found":
            len(results),

        "stocks":
            results,

        "missing":
            missing
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
        f"成功取得"
        f"{len(results)}檔資料"
    )

    if missing:

        print(
            "尚未取得："
        )

        for item in missing:

            print(
                item["name"],
                item["code"],
                item["market"]
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

