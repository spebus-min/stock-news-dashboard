import json
import time
import urllib.request
import urllib.parse
import urllib.error
import xml.etree.ElementTree as ET

from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo
from urllib.parse import urlparse

from googlenewsdecoder import new_decoderv1


GOOGLE_NEWS_URL = "https://news.google.com/rss/search"

TAIPEI_TZ = ZoneInfo("Asia/Taipei")


# =========================================================
# 可信新聞來源
# =========================================================

TRUSTED_SOURCES = {
    "中央社": {
        "domains": [
            "cna.com.tw"
        ],
        "score": 10
    },

    "經濟日報": {
        "domains": [
            "money.udn.com"
        ],
        "score": 10
    },

    "工商時報": {
        "domains": [
            "ctee.com.tw"
        ],
        "score": 10
    },

    "天下雜誌": {
        "domains": [
            "cw.com.tw"
        ],
        "score": 8
    },

    "商業周刊": {
        "domains": [
            "businessweekly.com.tw"
        ],
        "score": 8
    },

    "MoneyDJ": {
        "domains": [
            "moneydj.com"
        ],
        "score": 7
    },

    "鉅亨網": {
        "domains": [
            "cnyes.com"
        ],
        "score": 7
    },

    "科技新報": {
        "domains": [
            "technews.tw"
        ],
        "score": 7
    }
}


# =========================================================
# 完全排除來源
# =========================================================

BLOCKED_SOURCE_KEYWORDS = [
    "TOP1markets",
    "top1markets",

    "豐雲學堂",
    "sinotrade",
    "sinotrade.com.tw",

    "CMoney",
    "籌碼K線",

    "旺得富",

    "玩股網",
    "WantGoo",

    "股感",
    "StockFeel"
]


# =========================================================
# 重大營運事件
# =========================================================

HIGH_VALUE_KEYWORDS = [
    "營收",
    "財報",
    "獲利",
    "EPS",

    "法說",
    "法說會",
    "財測",
    "展望",

    "接單",
    "訂單",

    "擴產",
    "產能",
    "建廠",
    "新廠",

    "量產",
    "試產",

    "新產品",
    "新品",
    "推出",

    "投資",
    "重大投資",

    "併購",
    "收購",
    "合併",

    "策略合作",
    "合作",
    "結盟",

    "董事會",
    "重大訊息",

    "現金股利",
    "股利",
    "配息",
    "配股",

    "增資",
    "減資",

    "取得資產",
    "處分資產",

    "停工",
    "復工",

    "召回",

    "出口管制",

    "供應鏈",
    "客戶",

    "出貨",
    "需求",

    "資本支出"
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

    "2奈米",
    "3奈米",

    "車用",
    "電動車",

    "市場需求",
    "訂單能見度",

    "海外布局",
    "海外設廠"
]


# =========================================================
# 明顯非重大營運新聞
# =========================================================

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
    "融券",

    "技術面",
    "均線",
    "KD",
    "MACD"
]


# =========================================================
# 整理文、導流文
# =========================================================

SUMMARY_STYLE_KEYWORDS = [
    "一次看",
    "一次搞懂",
    "總整理",
    "懶人包",

    "怎麼選",
    "如何選",

    "值得買嗎",
    "還能買嗎",
    "現在能買嗎",

    "怎麼買",
    "如何買",

    "卡位",

    "ETF怎麼選",
    "ETF如何選",

    "投資攻略",
    "投資教學",

    "新手必看",

    "完整解析",
    "完整分析"
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

            raw_data = response.read()

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


def build_google_news_url(query):

    params = {
        "q": query,
        "hl": "zh-TW",
        "gl": "TW",
        "ceid": "TW:zh-Hant"
    }

    return (
        GOOGLE_NEWS_URL
        + "?"
        + urllib.parse.urlencode(
            params
        )
    )


def build_search_queries(stock):

    queries = []

    stock_name = stock["name"]
    stock_code = stock["code"]

    # 一般搜尋
    queries.append(
        f'"{stock_name}" '
        f'{stock_code} '
        f'when:7d'
    )

    # 對可信媒體逐一搜尋
    for source_info in TRUSTED_SOURCES.values():

        for domain in source_info["domains"]:

            query = (
                f'"{stock_name}" '
                f'site:{domain} '
                f'when:7d'
            )

            queries.append(
                query
            )

    return queries


def parse_date(date_text):

    if not date_text:
        return None

    try:

        date_value = (
            parsedate_to_datetime(
                date_text
            )
        )

        if date_value.tzinfo is None:

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


def contains_any(text, keywords):

    if not text:
        return False

    text_lower = text.lower()

    for keyword in keywords:

        if keyword.lower() in text_lower:
            return True

    return False


def count_keywords(text, keywords):

    if not text:
        return 0

    text_lower = text.lower()

    count = 0

    for keyword in keywords:

        if keyword.lower() in text_lower:
            count += 1

    return count


def clean_title(title, source):

    if not title:
        return ""

    title = title.strip()

    if source:

        suffix = f" - {source}"

        if title.endswith(suffix):

            title = (
                title[
                    :-len(suffix)
                ]
                .strip()
            )

    return title


def is_blocked_source(source, homepage):

    combined = (
        f"{source} {homepage}"
        .lower()
    )

    for blocked in BLOCKED_SOURCE_KEYWORDS:

        if blocked.lower() in combined:
            return True

    return False


def identify_trusted_source(source, homepage):

    combined = (
        f"{source} {homepage}"
        .lower()
    )

    for trusted_name, info in TRUSTED_SOURCES.items():

        if trusted_name.lower() in combined:

            return (
                trusted_name,
                info["score"]
            )

        for domain in info["domains"]:

            if domain.lower() in combined:

                return (
                    trusted_name,
                    info["score"]
                )

    return (
        None,
        0
    )


def calculate_news_score(
    title,
    source_score
):

    score = source_score

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

    summary_count = (
        count_keywords(
            title,
            SUMMARY_STYLE_KEYWORDS
        )
    )

    score += (
        high_count * 4
    )

    score += (
        medium_count * 1
    )

    score -= (
        low_count * 8
    )

    score -= (
        summary_count * 10
    )

    return score


def parse_google_news(
    xml_text,
    stock
):

    if not xml_text:
        return []

    try:

        root = ET.fromstring(
            xml_text
        )

    except ET.ParseError as error:

        print(
            f"{stock['name']} "
            f"RSS解析失敗："
            f"{error}"
        )

        return []

    articles = []

    now = datetime.now(
        TAIPEI_TZ
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

        if source_element is not None:

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

        if published_at is None:
            continue

        if published_at < seven_days_ago:
            continue

        title = (
            clean_title(
                title,
                source
            )
        )

        # 必須提到公司名稱
        if stock["name"] not in title:
            continue

        # 黑名單來源直接排除
        if is_blocked_source(
            source,
            source_homepage
        ):
            continue

        trusted_name, source_score = (
            identify_trusted_source(
                source,
                source_homepage
            )
        )

        # 不在可信來源白名單就排除
        if trusted_name is None:
            continue

        # 技術面、籌碼、喊盤內容排除
        if contains_any(
            title,
            LOW_VALUE_KEYWORDS
        ):
            continue

        # 整理文、導流文排除
        if contains_any(
            title,
            SUMMARY_STYLE_KEYWORDS
        ):
            continue

        has_high_value = (
            contains_any(
                title,
                HIGH_VALUE_KEYWORDS
            )
        )

        has_medium_value = (
            contains_any(
                title,
                MEDIUM_VALUE_KEYWORDS
            )
        )

        if (
            not has_high_value
            and not has_medium_value
        ):
            continue

        score = (
            calculate_news_score(
                title,
                source_score
            )
        )

        age_hours = (
            now
            - published_at
        ).total_seconds() / 3600

        articles.append({
            "title":
                title,

            "source":
                trusted_name,

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


def normalize_title(title):

    return (
        title
        .replace(" ", "")
        .replace("　", "")
        .replace("，", "")
        .replace(",", "")
        .replace("。", "")
        .replace("！", "")
        .replace("!", "")
        .replace("？", "")
        .replace("?", "")
        .replace("／", "")
        .replace("/", "")
        .replace("｜", "")
        .replace("|", "")
        .lower()
    )


def remove_duplicates(articles):

    unique = []
    seen_titles = set()

    for article in articles:

        normalized = (
            normalize_title(
                article["title"]
            )
        )

        if normalized in seen_titles:
            continue

        seen_titles.add(
            normalized
        )

        unique.append(
            article
        )

    return unique


def select_articles(articles):

    articles = (
        remove_duplicates(
            articles
        )
    )

    recent = []
    older = []

    for article in articles:

        if article["age_hours"] <= 72:

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

    # 72小時內優先，最多2篇
    for article in recent:

        if len(selected) >= 2:
            break

        selected.append(
            article
        )

    # 72小時內完全沒有，
    # 才放寬至7天
    if len(selected) == 0:

        for article in older:

            if len(selected) >= 2:
                break

            selected.append(
                article
            )

    return selected


# =========================================================
# 判斷是否為真正外部新聞網址
# =========================================================

def is_external_news_url(url):

    if not url:
        return False

    try:

        parsed = urlparse(
            url
        )

        host = (
            parsed.netloc
            .lower()
        )

        if not host:
            return False

        if (
            "news.google.com"
            in host
        ):
            return False

        if host.endswith(
            "google.com"
        ):
            return False

        return True

    except Exception:

        return False


# =========================================================
# Google News網址解析
# =========================================================

def resolve_original_url(
    discovery_url
):

    if not discovery_url:

        return (
            None,
            False
        )

    # 如果本來就不是Google網址，
    # 直接當成原文網址
    if is_external_news_url(
        discovery_url
    ):

        return (
            discovery_url,
            True
        )

    try:

        result = (
            new_decoderv1(
                discovery_url
            )
        )

        if (
            isinstance(
                result,
                dict
            )
            and result.get(
                "status"
            )
        ):

            decoded_url = (
                result.get(
                    "decoded_url"
                )
            )

            if is_external_news_url(
                decoded_url
            ):

                return (
                    decoded_url,
                    True
                )

    except Exception as error:

        print(
            "  原文網址解析失敗："
            f"{error}"
        )

    return (
        None,
        False
    )


def resolve_selected_articles(
    articles
):

    resolved_articles = []

    for article in articles:

        discovery_url = (
            article.get(
                "discovery_url"
            )
        )

        print(
            "  正在解析原文網址："
            f"{article['source']}｜"
            f"{article['title']}"
        )

        original_url, resolved = (
            resolve_original_url(
                discovery_url
            )
        )

        article[
            "original_url"
        ] = original_url

        article[
            "url_resolved"
        ] = resolved

        resolved_articles.append(
            article
        )

        if resolved:

            print(
                "    ✓ 原文網址解析成功"
            )

        else:

            print(
                "    ⚠ 原文網址解析失敗，"
                "保留Google News備援網址"
            )

        # 避免連續大量解析
        time.sleep(
            1
        )

    return resolved_articles


def main():

    stocks = load_stock_list()

    print(
        f"開始搜尋"
        f"{len(stocks)}檔標的新聞"
    )

    output_stocks = []
    total_articles = 0
    total_resolved_urls = 0

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

        all_articles = []

        search_queries = (
            build_search_queries(
                stock
            )
        )

        for query in search_queries:

            url = (
                build_google_news_url(
                    query
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

            all_articles.extend(
                articles
            )

            # 避免短時間大量RSS請求
            time.sleep(
                0.25
            )

        selected = (
            select_articles(
                all_articles
            )
        )

        # 只解析最後真正選中的新聞
        selected = (
            resolve_selected_articles(
                selected
            )
        )

        total_articles += (
            len(selected)
        )

        total_resolved_urls += sum(
            1
            for article in selected
            if article.get(
                "url_resolved"
            )
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
                "  近期無重大營運事件變動"
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
            "優先72小時；若無結果則最多7天",

        "source_policy":
            "僅保留可信來源白名單",

        "total_watchlist":
            len(stocks),

        "total_articles":
            total_articles,

        "total_resolved_urls":
            total_resolved_urls,

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

    print(
        f"成功解析"
        f"{total_resolved_urls}則原文網址。"
    )


if __name__ == "__main__":
    main()
