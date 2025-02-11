import streamlit as st
import openai
import json

# Streamlit Community Cloudの「Secrets」からOpenAI API keyを取得
openai.api_key = st.secrets.OpenAIAPI.openai_api_key

# ペルソナの読み込み
def load_persona(file_path):
    with open(file_path, "r") as file:
        persona = json.load(file)
    return persona

# ペルソナファイルを読み込む
persona = load_persona("tanaka_taro.json")

# ペルソナ情報を表示
st.title(f"AIコーチ: {persona['name']}さんのインタビュー")
st.write(f"**職業:** {persona['job']}")
st.write(f"**目標:** {persona['goals']}")
st.write(f"**課題:** {persona['challenges']}")

# インタビュー質問の読み込み
def load_questions(file_path):
    with open(file_path, "r") as file:
        questions = json.load(file)
    return questions["questions"]

# 質問ファイルを読み込む
interview_questions = load_questions("interview_questions.json")

# st.session_stateを使いメッセージのやりとりを保存
if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {"role": "system", "content": f"あなたは{persona['job']}の{persona['name']}さんです。目標は{persona['goals']}ですが、{persona['challenges']}という課題を抱えています。これを元に対話を進めてください。"}
    ]

if "question_index" not in st.session_state:
    st.session_state["question_index"] = 0

# インタビューの質問を表示
if st.button("インタビューを開始 / 次の質問"):
    if st.session_state["question_index"] < len(interview_questions):
        st.write(f"🤖: {interview_questions[st.session_state['question_index']]}")
        st.session_state["question_index"] += 1
    else:
        st.write("インタビューは終了しました。ご協力ありがとうございました！")

# チャットボットとやりとりする関数
def communicate():
    messages = st.session_state["messages"]

    user_message = {"role": "user", "content": st.session_state["user_input"]}
    messages.append(user_message)

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=messages
        )
        bot_message = response["choices"][0]["message"]
        messages.append(bot_message)
    except Exception as e:
        st.error(f"エラーが発生しました: {e}")

    st.session_state["user_input"] = ""  # 入力欄を消去

# ユーザーインターフェイスの構築
st.write("グレゴリー・ベイトソンの教育モデルに基づいて、ChatGPTによる”メタ認知”を提供するサービスです")

user_input = st.text_input("どんなことを学びたいのか、是非教えてください。", key="user_input", on_change=communicate)

if st.session_state["messages"]:
    messages = st.session_state["messages"]

    for message in reversed(messages[1:]):  # 直近のメッセージを上に
        speaker = "🙂"
        if message["role"] == "assistant":
            speaker = "🤖"
        st.write(speaker + ": " + message["content"])

# 履歴の保存機能
def save_history():
    with open("chat_history.json", "w") as file:
        json.dump(st.session_state["messages"], file)

# 履歴のダウンロードボタン
def download_history():
    chat_history_json = json.dumps(st.session_state["messages"], ensure_ascii=False, indent=4)
    st.download_button(
        label="チャット履歴をダウンロード",
        data=chat_history_json,
        file_name='chat_history.json',
        mime='application/json'
    )

# ボタン操作
download_history()
if st.button("終了して履歴を保存"):
    save_history()
    st.success("履歴を保存しました。")

# 学習レベルの分析関数
def analyze_messages():
    levels = {"zero_learning": 0, "first_learning": 0, "second_learning": 0, "third_learning": 0}
    for msg in st.session_state["messages"]:
        if msg["role"] == "assistant":
            if "基本知識" in msg["content"]:
                levels["zero_learning"] += 1
            elif "新しい方法" in msg["content"]:
                levels["first_learning"] += 1
            elif "考え方やパターン" in msg["content"]:
                levels["second_learning"] += 1
            elif "世界観" in msg["content"]:
                levels["third_learning"] += 1
    return levels

# 分析結果表示
if st.button("対話のサマリーを見る"):
    analysis = analyze_messages()
    st.write("学習レベルごとのやり取り数:", analysis)
