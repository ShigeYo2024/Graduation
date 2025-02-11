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

# ペルソナと質問ファイルを読み込む
personas = load_personas("persona.json")
interview_questions = load_questions("interview_questions.json")

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

# OpenAIを使ってペルソナが質問を生成
def generate_questions(persona):
    prompt = f"""
    あなたは{persona['job']}の{persona['name']}です。
    以下の目標と話題に基づいて、AIチャットボットに投げかけるべき質問を3つ考えてください。
    
    目標: {persona['goals']}
    話題: {persona['challenges']}
    
    具体的な質問:
    """
    
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "あなたはプロフェッショナルなDX推進コンサルタントです。"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150
        )
        questions = response["choices"][0]["message"]["content"].strip().split("\n")
        return questions
    except Exception as e:
        st.error(f"質問の生成中にエラーが発生しました: {e}")
        return []

# ペルソナからのフィードバック生成
def generate_feedback(persona, chat_history):
    prompt = f"""
    あなたは{persona['job']}の{persona['name']}です。
    以下はあなたがAIチャットボットとやり取りした内容です。この経験を基に、インタビューの質問に答えてください。

    チャット履歴: {chat_history}

    質問:
    1. このDX推進コーチのアドバイスは役に立ちましたか？
    2. どのアドバイスが最も実用的でしたか？
    3. 改善してほしい点はありますか？

    回答:
    """

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "あなたはプロフェッショナルなDX推進コンサルタントです。"},
            {"role": "user", "content": prompt}
        ],
        max_tokens=300
    )
    feedback = response["choices"][0]["message"]["content"].strip()
    return feedback

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

# フィードバック生成ボタン
if st.button(f"{persona['name']}さんからフィードバックを取得"):
    feedback = generate_feedback(persona, st.session_state["messages"])
    st.write(f"📜 {persona['name']}さんのフィードバック:")
    st.write(feedback)

# チャット履歴の表示
if st.session_state["messages"]:
    for message in reversed(st.session_state["messages"][1:]):
        speaker = "🙂" if message["role"] == "user" else "🤖"
        st.write(f"{speaker}: {message['content']}")

# チャット履歴の保存
def save_history():
    file_name = f"chat_history_persona_{persona['id']}.json"
    with open(file_name, "w") as file:
        json.dump(st.session_state["messages"], file)

if st.button("チャット履歴を保存"):
    save_history()
    st.success(f"{persona['name']}さんのチャット履歴を保存しました。")

# ダウンロードボタン
def download_history():
    file_name = f"chat_history_persona_{persona['id']}.json"
    if os.path.exists(file_name):
        with open(file_name, "r") as file:
            chat_data = file.read()
        st.download_button("チャット履歴をダウンロード", data=chat_data, file_name=file_name, mime='application/json')

download_history()
