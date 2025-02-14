import streamlit as st
import openai
import json
import os
import pandas as pd
import io

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

# ペルソナとインタビュー質問ファイルとDX課題チェックリスト（persona_questions）を読み込む
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
st.write(f"**課題:** {persona['challenges']}")

# セッションステートの初期化
if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {"role": "system", "content": f"あなたはDX推進コーチです。{persona['job']}の{persona['name']}さんの課題解決をサポートしてください。"}
    ]

if "feedbacks" not in st.session_state:
    st.session_state["feedbacks"] = []

def generate_questions(persona):
    prompt = f"""
    あなたは{persona['job']}の{persona['name']}です。
    
    以下の目標と課題とDX推進ステージに基づいて、DX推進がうまくいかない事象を踏まえ、その課題を解決するための質問をしてください。
    
    目標: {persona['goals']}
    課題: {persona['challenges']}
    DX推進ステージ：{persona['DX Stages']}

    以下のDX推進の課題チェックリストの課題を、DX推進ステージに基づき、適宜参照してください。
    【DX推進の課題チェックリスト】
    {json.dumps(persona_questions, ensure_ascii=False, indent=2)}
 
    """
    
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "あなたは自分の所属部署のDX推進リーダーです。"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=600
        )
        questions_and_responses = response["choices"][0]["message"]["content"].strip().split("\n")
        return questions_and_responses
    except Exception as e:
        st.error(f"質問の生成中にエラーが発生しました: {e}")
        return []

# ペルソナからのフィードバック生成
def generate_feedback(persona, chat_history):
    chat_content = "\n".join([msg["content"] for msg in chat_history if msg["role"] in ["user", "assistant"]])
    
    questions_formatted = "\n".join([f"{i+1}. {q}" for i, q in enumerate(interview_questions)])
    
    prompt = f"""
    あなたは{persona['job']}の{persona['name']}です。
    以下はあなたがAIチャットボットとやり取りした内容です。この経験を基に、インタビューの質問に答えてください。

    チャット履歴:
    {chat_content}

    質問:
    {questions_formatted}

    回答:
    """

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "あなたはDX推進リーダーとしてチャットボットを利用し評価する立場の人です。"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=600,
            temperature=0.7
        )
        feedback = response["choices"][0]["message"]["content"].strip()
        st.session_state["feedbacks"].append(feedback)
        return feedback
    except openai.error.OpenAIError as e:
        st.error(f"OpenAI APIでエラーが発生しました: {e}")
        return "フィードバックの生成に失敗しました。"

# 自動生成された質問をチャットに送信
if st.button(f"{persona['name']}さんの自動生成質問を開始"):
    auto_questions = generate_questions(persona)
    for question in auto_questions:
        user_message = {"role": "user", "content": question}
        st.session_state["messages"].append(user_message)
        
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
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

# フィードバック履歴の表示
if st.session_state["feedbacks"]:
    st.write("📄 これまでのフィードバック履歴:")
    for feedback in reversed(st.session_state["feedbacks"]):
        st.write(feedback)

# チャット履歴をExcelに保存
def save_chat_history_to_excel(persona_id, messages):
    if messages:
        df = pd.DataFrame(messages)
        filename = f"chat_history_persona_{persona_id}.xlsx"
        df.to_excel(filename, index=False, encoding="utf-8", engine="openpyxl")
        return filename
    return None

# フィードバック履歴をExcelに保存
def save_feedback_history_to_excel(persona_id, feedbacks):
    if feedbacks:
        df = pd.DataFrame(feedbacks, columns=["フィードバック"])
        filename = f"feedback_history_persona_{persona_id}.xlsx"
        df.to_excel(filename, index=False, encoding="utf-8", engine="openpyxl")
        return filename
    return None

# Excelファイルのダウンロード
def download_excel_file(file_path, label):
    if os.path.exists(file_path):
        with open(file_path, "rb") as file:
            st.download_button(label, data=file, file_name=file_path, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    else:
        st.warning(f"{file_path} が存在しません。先にExcelファイルを保存してください。")

# Excel保存ボタン
if st.button("チャット履歴をExcelで保存"):
    chat_file = save_chat_history_to_excel(persona["id"], st.session_state.get("messages", []))
    if chat_file:
        st.success(f"{persona['name']}さんのチャット履歴をExcelに保存しました。")
    else:
        st.warning("チャット履歴がありません。")

if st.button("フィードバック履歴をExcelで保存"):
    feedback_file = save_feedback_history_to_excel(persona["id"], st.session_state.get("feedbacks", []))
    if feedback_file:
        st.success(f"{persona['name']}さんのフィードバック履歴をExcelに保存しました。")
    else:
        st.warning("フィードバック履歴がありません。")

# ダウンロードボタン
download_excel_file(f"chat_history_persona_{persona['id']}.xlsx", "チャット履歴をダウンロード")
download_excel_file(f"feedback_history_persona_{persona['id']}.xlsx", "フィードバック履歴をダウンロード")

