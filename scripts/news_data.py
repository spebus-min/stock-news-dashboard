import json
import time
import urllib.request
import urllib.parse
import urllib.error
import xml.etree.ElementTree as ET

from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo


GOOGLE_NEWS_URL = (
    "https://news.google.com/rss/search"
)

TAIPEI_TZ = ZoneInfo(
    "Asia/Taipei"
)


# ==============================
# 新聞重要性關鍵字
# ==============================

HIGH_VALUE_KEYWORDS = [
    "營收",
    "財報",
    "法說",
    "法說會",
    "財測",
    "展望",
    "EPS",
    "接單",
    "訂單",
    "擴產",
    "產能",
    "量產",
    "新產品",
    "新品",
    "投資",
    "重大投資",
    "併購",
    "收購",
    "合併",
    "策略合作",
    "結盟",
    "董事會",
    "重大訊息",
    "現金股利",
    "配息",
    "配股",
    "增資",
    "減資",
    "處分資產",
    "取得資產",
    "停工",
    "復工",
    "召回",
    "出口管制"
]


MEDIUM_VALUE_KEYWORDS = [
    "AI",
    "人工智慧",
    "半導體",
    "晶片",
    "伺服器",
    "ASIC",
    "CoWoS",
    "先進封裝",
    "車用",
    "電動車",
    "供應鏈",
    "客戶",
    "市場需求",
    "出貨",
    "訂單能見度",
    "產業展望"
]


# ==============================
# 希望降低排序的新聞
# ==============================

LOW_VALUE_KEYWORDS = [
    "技術分析",
    "籌碼",
    "籌碼面",
    "三大法人",
    "外資買超",
    "外資賣超",
    "投信買超",
    "投信賣超",
    "自營商",
    "盤中",
    "盤勢",
    "今日股價",
    "股價創高",
    "股價創低",
    "飆股",
    "熱門股",
    "強勢股",
    "弱勢股",
    "目標價",
    "法人喊",
    "存股",
    "當沖",
    "融資",
    "融券"
]


# ==============================
# 優先新聞來源
# ==============================

PREFERRED_SOURCES = [
    "中央社",
    "經濟日報",
    "工商時報",
    "天下雜誌",
    "商業周刊",
    "財訊",
    "MoneyDJ",
    "鉅亨網",
    "科技新報"
]


def load_stock_list():

    with open(
        "stocks.json",
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


def fetch_text(url):

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "Chrome/120.0 Safari/537.36"
            ),
            "Accept": (
                "application/rss+xml,"
                "application/xml,"
                "text/xml"
            ),
            "Accept-Language":
                "zh-TW,zh;q=0.9,en;q=0.8"
        }
    )

    try:

        with urllib.request.urlopen(
            request,
            timeout=30
        ) as response:

            raw_data = (
                response.read()
            )

            return raw_data.decode(
                "utf-8",
                errors="replace"
            )

    except urllib.error.HTTPError as error:

        print(
            f"HTTP錯誤："
            f"{error.code}｜{url}"
        )

        return None

    except urllib.error.URLError as error:

        print(
            f"連線失敗："
            f"{error.reason}｜{url}"
        )

        return None

    except Exception as error:

        print(
            f"讀取失敗："
            f"{error}"
        )

        return None


def build_google_news_url(
    stock
):

    query = (
        f'"{stock["name"]}" '
        f'{stock["code"]} '
        f'when:7d'
    )

    params = {
        "q":
            query,

        "hl":
            "zh-TW",

        "gl":
            "TW",

        "ceid":
            "TW:zh-Hant"
    }

    return (
        GOOGLE_NEWS_URL
        + "?"
        + urllib.parse.urlencode(
            params
        )
    )


def parse_date(
    date_text
):

    if not date_text:
        return None

    try:

        date_value = (
            parsedate_to_datetime(
                date_text
            )
        )

        if (
            date_value.tzinfo
            is None
        ):

            date_value = (
                date_value.replace(
                    tzinfo=timezone.utc
                )
            )

        return (
            date_value.astimezone(
                TAIPEI_TZ
            )
        )

    except Exception:

        return None


def contains_any(
    text,
    keywords
):

    text_lower = (
        text.lower()
    )

    for keyword in keywords:

        if (
            keyword.lower()
            in text_lower
        ):
            return True

    return False


def count_keywords(
    text,
    keywords
):

    text_lower = (
        text.lower()
    )

    count = 0

    for keyword in keywords:

        if (
            keyword.lower()
            in text_lower
        ):
            count += 1

    return count


def source_is_preferred(
    source
):

    for preferred in (
        PREFERRED_SOURCES
    ):

        if preferred in source:
            return True

    return False


def calculate_news_score(
    title,
    source
):

    score = 0

    high_count = (
        count_keywords(
            title,
            HIGH_VALUE_KEYWORDS
        )
    )

    medium_count = (
        count_keywords(
            title,
            MEDIUM_VALUE_KEYWORDS
        )
    )

    low_count = (
        count_keywords(
            title,
            LOW_VALUE_KEYWORDS
        )
    )

    score += (
        high_count * 5
    )

    score += (
        medium_count * 2
    )

    score -= (
        low_count * 5
    )

    if source_is_preferred(
        source
    ):
        score += 3

    return score


def clean_title(
    title,
    source
):

    if not title:
        return ""

    title = (
        title.strip()
    )

    if source:

        suffix = (
            f" - {source}"
        )

        if title.endswith(
            suffix
        ):

            title = (
                title[
                    :-len(suffix)
                ]
                .strip()
            )

    return title


def parse_google_news(
    xml_text,
    stock
):

    if not xml_text:
        return []

    try:

        root = (
            ET.fromstring(
                xml_text
            )
        )

    except ET.ParseError as error:

        print(
            f"{stock['name']} "
            f"RSS解析失敗："
            f"{error}"
        )

        return []

    articles = []

    now = (
        datetime.now(
            TAIPEI_TZ
        )
    )

    seven_days_ago = (
        now
        - timedelta(
            days=7
        )
    )

    for item in root.findall(
        ".//item"
    ):

        title = (
            item.findtext(
                "title",
                default=""
            )
        )

        link = (
            item.findtext(
                "link",
                default=""
            )
        )

        pub_date_text = (
            item.findtext(
                "pubDate",
                default=""
            )
        )

        source_element = (
            item.find(
                "source"
            )
        )

        source = ""

        source_homepage = ""

        if (
            source_element
            is not None
        ):

            source = (
                source_element.text
                or ""
            ).strip()

            source_homepage = (
                source_element.attrib.get(
                    "url",
                    ""
                )
            )

        published_at = (
            parse_date(
                pub_date_text
            )
        )

        if (
            published_at
            is None
        ):
            continue

        if (
            published_at
            < seven_days_ago
        ):
            continue

        title = (
            clean_title(
                title,
                source
            )
        )

        # 股票名稱必須出現在標題
        # 降低同代號、同產業誤抓機率
        if (
            stock["name"]
            not in title
        ):
            continue

        score = (
            calculate_news_score(
                title,
                source
            )
        )

        # 完全沒有營運價值，
        # 或明顯屬籌碼、技術分析，
        # 就先排除
        if score < 2:
            continue

        age_hours = (
            now
            - published_at
        ).total_seconds() / 3600

        articles.append({
            "title":
                title,

            "source":
                source,

            "published_at":
                published_at.strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),

            "age_hours":
                round(
                    age_hours,
                    1
                ),

            "score":
                score,

            "discovery_url":
                link,

            "publisher_homepage":
                source_homepage
        })

    return articles


def remove_duplicates(
    articles
):

    unique = []

    seen_titles = set()

    for article in articles:

        normalized = (
            article["title"]
            .replace(" ", "")
            .replace("　", "")
        )

        if (
            normalized
            in seen_titles
        ):
            continue

        seen_titles.add(
            normalized
        )

        unique.append(
            article
        )

    return unique


def select_articles(
    articles
):

    articles = (
        remove_duplicates(
            articles
        )
    )

    recent = []

    older = []

    for article in articles:

        if (
            article["age_hours"]
            <= 72
        ):
            recent.append(
                article
            )

        else:
            older.append(
                article
            )

    recent.sort(
        key=lambda article: (
            article["score"],
            article["published_at"]
        ),
        reverse=True
    )

    older.sort(
        key=lambda article: (
            article["score"],
            article["published_at"]
        ),
        reverse=True
    )

    selected = []

    # 先取72小時內
    for article in recent:

        if (
            len(selected)
            >= 2
        ):
            break

        selected.append(
            article
        )

    # 不足2篇才擴展到7天
    if (
        len(selected)
        < 2
    ):

        for article in older:

            if (
                len(selected)
                >= 2
            ):
                break

            selected.append(
                article
            )

    return selected


def main():

    stocks = (
        load_stock_list()
    )

    print(
        f"開始搜尋"
        f"{len(stocks)}檔標的新聞"
    )

    output_stocks = []

    total_articles = 0

    for index, stock in enumerate(
        stocks,
        start=1
    ):

        print(
            f"[{index}/"
            f"{len(stocks)}] "
            f"{stock['name']}"
            f"（{stock['code']}）"
        )

        url = (
            build_google_news_url(
                stock
            )
        )

        xml_text = (
            fetch_text(
                url
            )
        )

        articles = (
            parse_google_news(
                xml_text,
                stock
            )
        )

        selected = (
            select_articles(
                articles
            )
        )

        total_articles += (
            len(selected)
        )

        output_stocks.append({
            "name":
                stock["name"],

            "code":
                stock["code"],

            "news_count":
                len(selected),

            "articles":
                selected
        })

        if selected:

            for article in selected:

                print(
                    "  ✓ "
                    f"{article['source']}｜"
                    f"{article['title']}"
                )

        else:

            print(
                "  近期無符合條件新聞"
            )

        # 避免短時間大量請求
        time.sleep(
            0.5
        )

    output = {

        "updated_at": (
            datetime.now(
                TAIPEI_TZ
            )
            .strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        ),

        "search_window":
            "優先72小時，最多7天",

        "total_watchlist":
            len(stocks),

        "total_articles":
            total_articles,

        "stocks":
            output_stocks
    }

    with open(
        "news_data.json",
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
        "新聞資料處理完成。"
    )

    print(
        f"共保留"
        f"{total_articles}則新聞。"
    )


if __name__ == "__main__":
    main()
