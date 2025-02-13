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

# ペルソナと質問ファイルとDX課題チェックリストを読み込む
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
    以下の目標と課題に基づいて、AIチャットボットに投げかけるべき質問を5つ考えてください。
    さらに、それぞれの質問に対するチャットボットの回答を受けて、追加で深掘りする質問も考えてください。

    目標: {persona['goals']}
    課題: {persona['challenges']}

    【重要】以下のDX推進の課題チェックリストを考慮してください。
    もし、ペルソナの質問にDX推進の課題チェックリストの要素が含まれていない場合、AIチャットボットは以下のように対応してください。

    1. まず、質問形式で「この要素を考慮することが重要である」とペルソナに問いかける。
    2. 次に、課題チェックリストの内容に基づいたベストプラクティスを回答として付け加える。

    【DX推進の課題チェックリスト】
    {json.dumps(persona_questions, ensure_ascii=False, indent=2)}

    出力フォーマット:
    1. 初回質問
       - チャットボットの回答（想定）
       - 追加の深掘り質問
       - 追加の深掘り質問に対するチャットボットの回答（想定）
       - もしDX推進の課題チェックリストの要素が不足している場合:
         - AIチャットボットの追加の問いかけ
         - ベストプラクティスの提供

    2. 初回質問
       - チャットボットの回答（想定）
       - 追加の深掘り質問
       - 追加の深掘り質問に対するチャットボットの回答（想定）
       - もしDX推進の課題チェックリストの要素が不足している場合:
         - AIチャットボットの追加の問いかけ
         - ベストプラクティスの提供

    例:
    1. AIチャットボットの導入にあたって、どのようなKPIを設定するのが望ましいですか？
       - AIチャットボット: KPIとして、応答速度、顧客満足度、問い合わせ削減率を設定するのが一般的です。
       - 追加質問: これらのKPIを設定する際の具体的な数値目標の決め方は？
       - 追加回答: 数値目標は、過去のデータと業界のベンチマークをもとに設定するのが良いでしょう。
       - もしDX推進の課題チェックリストの要素が不足している場合:
         - AIチャットボット: 「KPIを設定する際に、業務改善目標とその進捗モニタリングを考慮することが重要ではないでしょうか？」
         - ベストプラクティス: 「定期的なKPIレビューと成果の可視化を行い、現場との適切なコミュニケーションを維持するのが理想的です。」

    5つの質問とそれぞれの深掘り質問を考えてください。
    """
    
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "あなたはプロフェッショナルなDX推進コンサルタントです。"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000
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
            model="gpt-4",
            messages=[
                {"role": "system", "content": "あなたはDX推進リーダーとしてチャットボットを利用し評価する立場の人です。"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=800,
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

