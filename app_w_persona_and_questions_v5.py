import streamlit as st
import openai
import json
import os

# StreamlitのSecretsからOpenAI API keyを取得
openai.api_key = st.secrets["OpenAIAPI"]["openai_api_key"]

# ペルソナの読み込み
def load_personas(file_path):
    with open(file_path, "r") as file:
        personas = json.load(file)
    return personas["personas"]

# インタビュー質問の読み込み
def load_questions(file_path):
    with open(file_path, "r") as file:
        questions = json.load(file)
    return questions["questions"]

# persona_questions.jsonの読み込み
def load_persona_questions(file_path):
    with open(file_path, "r") as file:
        persona_questions = json.load(file)
    return persona_questions

# ペルソナと質問ファイルを読み込む
personas = load_personas("persona.json")
interview_questions = load_questions("interview_questions.json")
persona_questions = load_persona_questions("persona_questions.json")

# ペルソナの選択
persona_names = [f"{p['id']}. {p['name']} ({p['job']})" for p in personas]
selected_persona = st.selectbox("インタビューするペルソナを選んでください:", persona_names)

# 選択されたペルソナの情報を取得
persona_id = int(selected_persona.split(".")[0]) - 1
persona = personas[persona_id]

# ペルソナ情報の表示
st.title(f"DX推進コーチ: {persona['name']}さんのインタビュー")
st.write(f"**職業:** {persona['job']}")
st.write(f"**目標:** {persona['goals']}")
st.write(f"**話題:** {persona['challenges']}")

# セッションステートの初期化
if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {"role": "system", "content": f"あなたはDX推進コーチです。{persona['job']}の{persona['name']}さんの話題解決をサポートしてください。"}
    ]

if "feedbacks" not in st.session_state:
    st.session_state["feedbacks"] = []

# OpenAIを使ってペルソナが質問を生成
def generate_questions(persona):
    prompt = f"""
    あなたは{persona['job']}の{persona['name']}です。
    以下の目標と課題に基づいて、AIチャットボットに投げかけるべき質問を10個考えてください。

    目標: {persona['goals']}
    課題: {persona['challenges']}

    参考情報として、DX推進の課題チェックリストも考慮してください:
    {json.dumps(persona_questions, ensure_ascii=False, indent=2)}

    具体的な質問:
    """

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "あなたはプロフェッショナルなDX推進コンサルタントです。"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300
        )
        questions = response["choices"][0]["message"]["content"].strip().split("\n")
        return questions
    except Exception as e:
        st.error(f"質問の生成中にエラーが発生しました: {e}")
        return []

# 自動生成された質問をチャットに送信
if st.button(f"{persona['name']}さんの自動生成質問を開始"):
    auto_questions = generate_questions(persona)
    for question in auto_questions:
        user_message = {"role": "user", "content": question}
        st.session_state["messages"].append(user_message)

        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=st.session_state["messages"]
            )
            bot_message = response["choices"][0]["message"]
            st.session_state["messages"].append(bot_message)
        except Exception as e:
            st.error(f"エラーが発生しました: {e}")

# チャット履歴の表示
if st.session_state["messages"]:
    for message in reversed(st.session_state["messages"][1:]):
        speaker = "🙂" if message["role"] == "user" else "🤖"
        st.write(f"{speaker}: {message['content']}")

# チャット履歴の保存
def save_history():
    file_name = f"chat_history_persona_{persona['id']}.txt"
    with open(file_name, "w", encoding="utf-8") as file:
        for message in st.session_state["messages"]:
            file.write(f"{message['role']}: {message['content']}\n")

if st.button("チャット履歴を保存"):
    save_history()
    st.success(f"{persona['name']}さんのチャット履歴を保存しました。")

# フィードバック履歴の保存
def save_feedback():
    file_name = f"feedback_history_persona_{persona['id']}.txt"
    with open(file_name, "w", encoding="utf-8") as file:
        for feedback in st.session_state["feedbacks"]:
            file.write(f"{feedback}\n\n")

if st.button("フィードバック履歴を保存"):
    save_feedback()
    st.success(f"{persona['name']}さんのフィードバック履歴を保存しました。")

# ダウンロードボタン
def download_file(file_name, label):
    if os.path.exists(file_name):
        with open(file_name, "r", encoding="utf-8") as file:
            data = file.read()
        st.download_button(label, data=data, file_name=file_name, mime='text/plain')

# チャット履歴のダウンロード
download_file(f"chat_history_persona_{persona['id']}.txt", "チャット履歴をダウンロード")

# フィードバック履歴のダウンロード
download_file(f"feedback_history_persona_{persona['id']}.txt", "フィードバック履歴をダウンロード")
