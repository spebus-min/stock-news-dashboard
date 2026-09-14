import os

from google import genai
from google.genai import types


API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise RuntimeError("找不到GEMINI_API_KEY")


client = genai.Client(
    api_key=API_KEY
)


prompt = """
公司：台積電

近期新聞：
1.台積電CoWoS產能擴產仍無法跟上AI需求，訂單外溢非台積電陣營。
2.台積電先進製程大擴產，明年計畫曝光，營收將續寫新高。

請只根據以上新聞內容，
產生20～100字繁體中文「營運與重大發展」摘要。

規則：
1.不得補充新聞中沒有提供的資訊。
2.不得提供投資建議。
3.使用客觀、簡潔的繁體中文。
4.直接輸出摘要，不要加標題。
"""


models_to_test = [
    "gemini-3.1-flash-lite",
    "gemini-2.5-flash-lite"
]


for model_name in models_to_test:

    print("=" * 60)
    print(f"開始測試模型：{model_name}")

    try:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                max_output_tokens=300
            )
        )

        print("✓ 測試成功")
        print("AI摘要：")
        print(response.text)

        print("=" * 60)

        # 第一個成功就停止，不需要繼續消耗API
        break

    except Exception as error:

        print("✗ 測試失敗")
        print(f"錯誤內容：{error}")

else:

    raise RuntimeError(
        "所有Gemini測試模型皆失敗"
    )
