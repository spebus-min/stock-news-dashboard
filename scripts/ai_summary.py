import json
import os
import time

from google import genai
from google.genai import types


MODEL_NAME = "gemini-3.7-flash"

NO_NEWS_TEXT = "近期無重大營運事件變動"


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

請只根據上面提供的新聞標題、來源與日期，撰寫一段繁體中文摘要。

規則：
1.只能使用提供的新聞資訊，不可自行補充新聞中沒有出現的事實、數字、公司展望或推測。
2.摘要內容以營收、法說、產品、產能、接單、投資、重大決策、供應鏈、需求等營運事件為主。
3.若有兩篇新聞描述同一事件，請整合成一句，不要重複敘述。
4.不要提供投資建議。
5.不要使用「看好」、「利多」、「利空」、「值得投資」、「建議買進」等判斷性語句。
6.不要加入新聞來源名稱。
7.不要加入股票代號。
8.不要使用條列式。
9.控制在20～100個中文字左右。
10.直接輸出摘要正文，不要加「摘要：」、「營運與重大發展：」等標題。
11.使用客觀、簡潔的繁體中文。
"""

    return prompt.strip()


def clean_summary(text):
    if not text:
        return NO_NEWS_TEXT

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
        return NO_NEWS_TEXT

    return text


def generate_summary(
    client,
    stock
):
    articles = stock.get(
        "articles",
        []
    )

    if not articles:
        return NO_NEWS_TEXT

    prompt = build_prompt(
        stock
    )

    try:
        response = (
            client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.2,
                    max_output_tokens=180
                )
            )
        )

        return clean_summary(
            response.text
        )

    except Exception as error:
        print(
            f"  ⚠ Gemini摘要失敗："
            f"{error}"
        )

        return NO_NEWS_TEXT


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

    for index, stock in enumerate(
        stocks,
        start=1
    ):
        print(
            f"[{index}/{len(stocks)}] "
            f"{stock['name']}"
            f"（{stock['code']}）"
        )

        if (
            stock.get(
                "news_count",
                0
            )
            == 0
        ):
            stock[
                "ai_summary"
            ] = NO_NEWS_TEXT

            print(
                f"  {NO_NEWS_TEXT}"
            )

            continue

        summary = generate_summary(
            client,
            stock
        )

        stock[
            "ai_summary"
        ] = summary

        if summary != NO_NEWS_TEXT:
            success_count += 1

        print(
            f"  ✓ {summary}"
        )

        # 避免過快連續呼叫API
        time.sleep(
            1
        )

    data[
        "ai_summary_model"
    ] = MODEL_NAME

    data[
        "ai_summary_success_count"
    ] = success_count

    save_news_data(
        data
    )

    print(
        "AI摘要處理完成。"
    )

    print(
        f"成功產生"
        f"{success_count}檔摘要。"
    )


if __name__ == "__main__":
    main()
