import json
import os
import random
import time

from google import genai
from google.genai import types


MODEL_NAME = "gemini-3.7-flash"

NO_NEWS_TEXT = "近期無重大營運事件變動"
AI_ERROR_TEXT = "AI摘要暫時無法產生"

MAX_RETRIES = 3


def load_news_data():
    with open(
        "news_data.json",
        "r",
        encoding="utf-8"
    ) as file:
        return json.load(file)


def save_news_data(data):
    with open(
        "news_data.json",
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2
        )


def build_prompt(stock):
    articles = stock.get(
        "articles",
        []
    )

    news_text_list = []

    for index, article in enumerate(
        articles,
        start=1
    ):
        news_text_list.append(
            f"""
新聞{index}
標題：{article.get("title", "")}
來源：{article.get("source", "")}
日期：{article.get("published_at", "")}
""".strip()
        )

    news_text = "\n\n".join(
        news_text_list
    )

    prompt = f"""
你正在整理台灣上市櫃公司的近期營運資訊。

公司：
{stock["name"]}（{stock["code"]}）

以下是系統已篩選過的近期新聞資料：

{news_text}

請只根據上面提供的新聞標題、來源與日期，
撰寫一段繁體中文摘要。

規則：
1.只能使用提供的新聞資訊，不可自行補充新聞中沒有出現的事實、數字、公司展望或推測。
2.摘要以營收、法說、產品、產能、接單、投資、重大決策、供應鏈、需求等營運事件為主。
3.若兩篇新聞描述相同或高度相關事件，請合併整理，不要重複敘述。
4.不要提供投資建議。
5.不要使用「看好」、「利多」、「利空」、「值得投資」、「建議買進」等判斷性語句。
6.不要加入新聞來源名稱。
7.不要加入股票代號。
8.不要使用條列式。
9.摘要長度控制在20～100個中文字左右。
10.直接輸出摘要正文，不要加「摘要：」、「營運與重大發展：」等標題。
11.使用客觀、簡潔的繁體中文。
"""

    return prompt.strip()


def clean_summary(text):
    if not text:
        return None

    text = text.strip()

    prefixes = [
        "摘要：",
        "摘要:",
        "營運與重大發展：",
        "營運與重大發展:"
    ]

    for prefix in prefixes:
        if text.startswith(prefix):
            text = text[
                len(prefix):
            ].strip()

    text = (
        text
        .replace("\n", "")
        .replace("\r", "")
    )

    if not text:
        return None

    return text


def is_temporary_error(error):
    error_text = str(
        error
    ).lower()

    temporary_keywords = [
        "503",
        "unavailable",
        "high demand",
        "server disconnected",
        "connection",
        "timeout",
        "timed out",
        "temporarily",
        "internal"
    ]

    return any(
        keyword in error_text
        for keyword in temporary_keywords
    )


def generate_summary(
    client,
    stock
):
    articles = stock.get(
        "articles",
        []
    )

    if not articles:
        return (
            NO_NEWS_TEXT,
            "no_news"
        )

    prompt = build_prompt(
        stock
    )

    for attempt in range(
        1,
        MAX_RETRIES + 1
    ):
        try:
            print(
                f"  Gemini摘要嘗試"
                f"{attempt}/{MAX_RETRIES}"
            )

            response = (
                client.models.generate_content(
                    model=MODEL_NAME,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        max_output_tokens=500,
                        thinking_config=types.ThinkingConfig(
                            thinking_level="low"
                        )
                    )
                )
            )

            summary = clean_summary(
                response.text
            )

            if summary:
                return (
                    summary,
                    "success"
                )

            print(
                "  ⚠ Gemini沒有回傳有效摘要"
            )

        except Exception as error:
            print(
                f"  ⚠ Gemini摘要失敗："
                f"{error}"
            )

            if (
                not is_temporary_error(
                    error
                )
            ):
                print(
                    "  此錯誤不是暫時性錯誤，"
                    "停止重試。"
                )

                return (
                    AI_ERROR_TEXT,
                    "error"
                )

        if attempt < MAX_RETRIES:
            wait_seconds = (
                3 * attempt
                + random.uniform(
                    0,
                    1
                )
            )

            print(
                f"  等待約"
                f"{wait_seconds:.1f}秒後重試..."
            )

            time.sleep(
                wait_seconds
            )

    print(
        "  ⚠ 已達最大重試次數"
    )

    return (
        AI_ERROR_TEXT,
        "error"
    )


def main():
    api_key = os.getenv(
        "GEMINI_API_KEY"
    )

    if not api_key:
        raise RuntimeError(
            "找不到GEMINI_API_KEY。"
        )

    client = genai.Client(
        api_key=api_key
    )

    data = load_news_data()

    stocks = data.get(
        "stocks",
        []
    )

    print(
        f"開始產生"
        f"{len(stocks)}檔標的AI摘要"
    )

    success_count = 0
    no_news_count = 0
    error_count = 0

    for index, stock in enumerate(
        stocks,
        start=1
    ):
        print(
            f"[{index}/{len(stocks)}] "
            f"{stock['name']}"
            f"（{stock['code']}）"
        )

        articles = stock.get(
            "articles",
            []
        )

        if not articles:
            stock[
                "ai_summary"
            ] = NO_NEWS_TEXT

            stock[
                "ai_summary_status"
            ] = "no_news"

            no_news_count += 1

            print(
                f"  ✓ {NO_NEWS_TEXT}"
            )

            continue

        summary, status = (
            generate_summary(
                client,
                stock
            )
        )

        stock[
            "ai_summary"
        ] = summary

        stock[
            "ai_summary_status"
        ] = status

        if status == "success":
            success_count += 1

            print(
                f"  ✓ {summary}"
            )

        elif status == "no_news":
            no_news_count += 1

            print(
                f"  ✓ {NO_NEWS_TEXT}"
            )

        else:
            error_count += 1

            print(
                f"  ⚠ {AI_ERROR_TEXT}"
            )

        # 成功或失敗後都稍微錯開下一次API請求
        time.sleep(
            1
        )

    data[
        "ai_summary_model"
    ] = MODEL_NAME

    data[
        "ai_summary_success_count"
    ] = success_count

    data[
        "ai_summary_no_news_count"
    ] = no_news_count

    data[
        "ai_summary_error_count"
    ] = error_count

    save_news_data(
        data
    )

    print(
        "AI摘要處理完成。"
    )

    print(
        f"成功摘要："
        f"{success_count}檔"
    )

    print(
        f"近期無重大新聞："
        f"{no_news_count}檔"
    )

    print(
        f"AI摘要失敗："
        f"{error_count}檔"
    )


if __name__ == "__main__":
    main()
