import streamlit as st
import openai
import json
import os
import pandas as pd
import io
import random  # ← これを追加

# StreamlitのSecretsからOpenAI API keyを取得
openai.api_key = st.secrets["OpenAIAPI"]["openai_api_key"]

# DX推進チェックリストを読み込む関数
def load_dx_checklist():
    with open("dx_checklist.txt", "r", encoding="utf-8") as file:
        checklist = file.readlines()
    return [item.strip() for item in checklist]  # 改行を削除してリスト化

# 回答に関連するチェックリストの要点を取得
def extract_relevant_checklist(question, checklist):
    relevant_items = [item for item in checklist if any(keyword in item for keyword in question.split())]
    return relevant_items if relevant_items else ["関連する情報が見つかりませんでした。"]


# DX推進ステージの選択肢
dx_stages = ["導入前", "導入初期", "導入推進中", "定着期"]

# ペルソナの読み込み
def load_personas(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        personas_data = json.load(file)

        # "DX Stages" が "RANDOM" の場合、ランダムなステージを代入
        for persona in personas_data["personas"]:
            if persona["DX Stages"] == "RANDOM":
                persona["DX Stages"] = random.choice(dx_stages)

    return personas_data["personas"]  # 修正: withブロックの外でreturn

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
interview_questions = load_questions("interview_questions_v3.json")
persona_questions = load_persona_questions("persona_questions.json")

# ペルソナの選択
persona_names = [f"{p['id']}. {p['name']} ({p['job']})" for p in personas]
selected_persona = st.selectbox("インタビューするペルソナを選んでください:", persona_names)

# 選択されたペルソナの情報を取得
persona_id = int(selected_persona.split(".")[0]) - 1
persona = personas[persona_id]

# ペルソナ情報の表示
st.title(f"DX推進リーダー: {persona['name']}さんのインタビュー")
st.write(f"**職業:** {persona['job']}")
st.write(f"**目標:** {persona['goals']}")
st.write(f"**課題:** {persona['challenges']}")
st.write(f"**DX推進ステージ:** {persona['DX Stages']}")

# 質問時のDX推進ステージをセッションに保存（質問が生成されるタイミングで保存）
st.session_state["dx_stage"] = persona["DX Stages"]

# **質問カテゴリ（DXステージを考慮）**
question_categories = {
    "組織課題": f"{persona['DX Stages']}における組織の壁やマネジメントの課題について質問を考えてください。",
    "技術課題": f"{persona['DX Stages']}におけるデジタル技術導入に関する質問を考えてください。",
    "導入後の評価": f"{persona['DX Stages']}におけるDX導入後の成果測定、PDCAの最適化に関する質問を考えてください。",
    "KPI設定": f"{persona['DX Stages']}におけるDXプロジェクトのKPI設定、データ分析の活用に関する質問を考えてください。",
    "現場対応": f"{persona['DX Stages']}における現場従業員の教育、業務変革に関する質問を考えてください。",
}

# セッションステートの初期化
if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {"role": "system", "content": f"あなたはDX推進コーチです。{persona['job']}の{persona['name']}さんの課題解決をサポートしてください。"}
    ]

if "feedbacks" not in st.session_state:
    st.session_state["feedbacks"] = []

# **質問生成**
def generate_questions(persona):
    questions_by_category = {}

    for category, instruction in question_categories.items():
        prompt = f"""
        あなたは{persona['job']}の{persona['name']}です。
        以下の目標と課題、DX推進ステージを踏まえ、{category}に関する質問を1つ考えてください。

        **目標:** {persona['goals']}
        **課題:** {persona['challenges']}
        **DX推進ステージ:** {persona['DX Stages']}

        **質問の指示:** {instruction}

        **質問:** 
        """

        try:
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "あなたはDX推進のリーダーです。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800
            )
            questions_by_category[category] = response["choices"][0]["message"]["content"].strip().split("\n")
        except Exception as e:
            st.error(f"質問の生成中にエラーが発生しました: {e}")
            questions_by_category[category] = []

    return questions_by_category

# **質問に対するAIの回答生成**
def chat_with_ai(persona, question):
    
     # DX推進チェックリストをロード
    checklist = load_dx_checklist()
    
    # 質問に関連するチェックリストの要点を取得
    relevant_points = extract_relevant_checklist(question, checklist)
    relevant_text = "\n".join([f"- {item}" for item in relevant_points])
    
    
    prompt = f"""
    あなたはDX推進のプロフェッショナルコーチです。
    {persona['job']}の{persona['name']}が以下の質問をしました。
    
    質問:
    {question}

    以下のDX推進の重要ポイントを＊＊＊＊必ず**参考にする
     {relevant_text}
    
    
    
    DX推進の知識を活かし、回答では、3つの重要なポイントを挙げてください。
    **各ポイントは300字以内** で書き、**合計900字以内** に収めてください。
    具体的かつ簡潔に、実践的なアドバイスを提供してください。




    【出力フォーマット】

    1. （ここに300字以内のアドバイス）
    2. （ここに300字以内のアドバイス）
    3. （ここに300字以内のアドバイス）

    """

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "あなたはDX推進のプロフェッショナルコーチです。"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.7,  # 創造性を少し抑える
            top_p=0.9  # 確率的に高い回答を優先
        )
        return response["choices"][0]["message"]["content"].strip()
    except Exception as e:
        st.error(f"AIの回答生成中にエラーが発生しました: {e}")
        return "回答を生成できませんでした。"

# **質問とAIの回答の表示**
if st.button(f"{persona['name']}の質問を開始", key="start_questions"):
    auto_questions = generate_questions(persona)

    for category, questions in auto_questions.items():
        st.subheader(f"📌 {category} の質問 ({persona['DX Stages']})")

        for question in questions:  
            # 質問が既に保存されていないかチェック
            if not any(msg["content"] == question for msg in st.session_state["messages"]):
                user_message = {"role": "user", "content": question}
                st.session_state["messages"].append(user_message)

            # AIの回答を生成
            ai_response = chat_with_ai(persona, question)

            # AIの回答が既に保存されていないかチェック
            if not any(msg["content"] == ai_response for msg in st.session_state["messages"]):
                ai_message = {"role": "assistant", "content": ai_response}
                st.session_state["messages"].append(ai_message)

            # **質問と回答の表示**
            st.markdown(f"🙂 **質問:**\n\n{question}")  # 質問の後に改行を追加
            st.markdown(f"🤖 **AIの回答:**\n\n{ai_response}")  # AIの回答の後に改行を追加


# ペルソナからのフィードバック生成
def generate_feedback(persona, chat_history):
    #　セッションに保存された DX ステージを取得（なければ現在のものを使用）
    dx_stage = st.session_state.get("dx_stage", persona["DX Stages"])
    
    chat_content = "\n".join([msg["content"] for msg in chat_history if msg["role"] in ["user", "assistant"]])
    
    questions_formatted = "\n".join([f"{i+1}. {q}" for i, q in enumerate(interview_questions)])
    
    prompt = f"""
    あなたは{persona['job']}の{persona['name']}です。
    あなたのDX推進ステージは「{dx_stage}」です。
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
            max_tokens=1200,
            temperature=0.6  # 具体性を持たせるために少し低めに調整
        )
        feedback = response["choices"][0]["message"]["content"].strip()
        st.session_state["feedbacks"].append(feedback)
        return feedback
    except openai.error.OpenAIError as e:
        st.error(f"OpenAI APIでエラーが発生しました: {e}")
        return "フィードバックの生成に失敗しました。"

# **フィードバックボタンを最後に配置**
if st.button(f"{persona['name']}さんからフィードバックを取得"):
    feedback = generate_feedback(persona, st.session_state["messages"])
    st.markdown(f"📜 **{persona['name']}さんのフィードバック:**\n\n{feedback}")

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

