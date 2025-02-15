import streamlit as st
import openai
import json
import os
import pandas as pd
import io
import random  # ← これを追加

# StreamlitのSecretsからOpenAI API keyを取得
openai.api_key = st.secrets["OpenAIAPI"]["openai_api_key"]


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
interview_questions = load_questions("interview_questions.json")
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
                max_tokens=600
            )
            questions_by_category[category] = response["choices"][0]["message"]["content"].strip().split("\n")
        except Exception as e:
            st.error(f"質問の生成中にエラーが発生しました: {e}")
            questions_by_category[category] = []

    return questions_by_category

# **質問に対するAIの回答生成**
def chat_with_ai(persona, question):
    prompt = f"""
    あなたはDX推進のプロフェッショナルコーチです。
    {persona['job']}の{persona['name']}が以下の質問をしました。
    
    質問:
    {question}

    これに対して、DX推進に関する知識を活用し、600字以内の具体的で実践的なアドバイスを行ってください。
    重要なポイントを3つにまとめてください。
    """

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "あなたはDX推進のプロフェッショナルコーチです。"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=600
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
            # 質問をユーザーの発言として保存
            user_message = {"role": "user", "content": question}
            st.session_state["messages"].append(user_message)

            # AIの回答を生成
            ai_response = chat_with_ai(persona, question)

            # AIの回答を保存
            ai_message = {"role": "assistant", "content": ai_response}
            st.session_state["messages"].append(ai_message)

            # **質問と回答の表示**
            st.write(f"🙂 **質問:** {question}")
            st.write(f"🤖 **AIの回答:** {ai_response}")

# ペルソナからのフィードバック生成
def generate_feedback(persona, chat_history):
    """
    チャットボットの体験に基づき、ペルソナからの具体的なフィードバックを生成
    """

    # チャット履歴を整形
    chat_content = "\n".join([msg["content"] for msg in chat_history if msg["role"] in ["user", "assistant"]])

    # インタビューの質問リストを整形
    questions_formatted = "\n".join([f"{i+1}. {q}" for i, q in enumerate(interview_questions)])

    prompt = f"""
    あなたは{persona['job']}の{persona['name']}です。
    以下はあなたがAIチャットボットとやり取りした内容です。この経験を基に、以下の3つの観点でフィードバックを行ってください。

    1. **特に役立ったチャットのやり取り**  
       - どの質問に対するAIの回答が特に役立ちましたか？  
       - それはなぜ役立ったのか、具体的な理由を述べてください。

    2. **期待と異なっていた点**  
       - どの質問に対する回答が期待と違いましたか？  
       - どの部分が足りなかったか、どのような情報が不足していたかを説明してください。

    3. **今後の改善点と具体的な提案**  
       - チャットボットがより有益な回答をするために、どのような改善が必要ですか？  
       - 具体的にどのような情報を追加すると良いと思いますか？

    **チャット履歴:**
    {chat_content}

    **インタビューの質問リスト:**
    {questions_formatted}

    **フィードバック:**
    """

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "あなたはDX推進リーダーとしてチャットボットを利用し評価する立場の人です。"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=800,
            temperature=0.6  # 具体性を持たせるために少し低めに調整
        )
        feedback = response["choices"][0]["message"]["content"].strip()
        st.session_state["feedbacks"].append(feedback)
        return feedback
    except openai.error.OpenAIError as e:
        st.error(f"OpenAI APIでエラーが発生しました: {e}")
        return "フィードバックの生成に失敗しました。"

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

