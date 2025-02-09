import streamlit as st
import openai
import json
from textblob import TextBlob
import matplotlib.pyplot as plt
from llama_index import SimpleDirectoryReader, GPTVectorStoreIndex, StorageContext, load_index_from_storage

# OpenAI APIキーの設定
openai.api_key = st.secrets.OpenAIAPI.openai_api_key

# インデックスの準備
try:
    storage_context = StorageContext.from_defaults(persist_dir="./index")
    index = load_index_from_storage(storage_context)
except:
    documents = SimpleDirectoryReader(input_dir="./documents").load_data()
    index = GPTVectorStoreIndex.from_documents(documents)
    index.storage_context.persist(persist_dir="./index")

# セッション状態の初期化
if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {"role": "system", "content": """あなたはグレゴリー・ベイトソンの教育モデルに基づいた教育コーチです。以下を行います：\n1. 感情状態を分析。\n2. 学習段階に応じた対話を提供。\n3. 内省を促進。"""}
    ]

# 感情分析関数
def analyze_emotion(text):
    blob = TextBlob(text)
    polarity = blob.sentiment.polarity
    if polarity > 0.5:
        return "ポジティブ"
    elif polarity < -0.5:
        return "ネガティブ"
    else:
        return "ニュートラル"

# RAGによる回答生成
def generate_rag_response(user_input):
    query_engine = index.as_query_engine()
    response = query_engine.query(user_input)
    return response.response

# OpenAI APIで追加質問を生成
def generate_openai_questions(rag_response):
    prompt = f"以下の内容に基づいて、ユーザーがさらに深く考えるべき質問を生成してください。\n\n{rag_response}\n\n不足している観点を考慮した質問を3つ作成してください。"
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": "あなたは優秀なAIコーチです。"},
                  {"role": "user", "content": prompt}]
    )
    return response["choices"][0]["message"]["content"]

# 学習段階ごとのメッセージを生成する関数
def generate_stage_message(stage, user_input):
    if stage == "zero_learning":
        return f"あなたの基本知識を確認します: {user_input}"
    elif stage == "first_learning":
        return f"新しい方法について考えてみましょう: {user_input}"
    elif stage == "second_learning":
        return f"あなたの考え方やパターンに焦点を当てます: {user_input}"
    elif stage == "third_learning":
        return f"より大きな視点であなたの世界観を再構築してみましょう: {user_input}"

# 次に考えるべき質問の提案
def propose_next_questions():
    return [
        "この視点をさらに広げるにはどんな質問が有効ですか？",
        "次にどのような行動を取るべきですか？",
        "他者の意見を取り入れるならどうしますか？"
    ]

# チャット履歴を保存する関数
def save_chat_history(messages):
    with open("chat_history.txt", "a", encoding="utf-8") as file:
        for message in messages:
            file.write(f"{message['role']}: {message['content']}\n")

# チャット履歴をインデックス化
def index_chat_history():
    documents = SimpleDirectoryReader("./").load_data()
    index = GPTVectorStoreIndex.from_documents(documents)
    return index

# チャットボットの応答処理
def communicate():
    user_input = st.text_input("今の課題や考えたいことを教えてください。", key="user_input")
    if user_input:
        st.session_state["messages"].append({"role": "user", "content": user_input})

        # 感情分析
        emotion = analyze_emotion(user_input)
        st.session_state["messages"].append({"role": "assistant", "content": f"感情分析結果: {emotion}"})

        # 学習段階の判定 (仮のロジック)
        if "基礎" in user_input:
            stage = "zero_learning"
        elif "方法" in user_input:
            stage = "first_learning"
        elif "パターン" in user_input:
            stage = "second_learning"
        else:
            stage = "third_learning"

        # 学習段階に基づくメッセージ生成
        stage_message = generate_stage_message(stage, user_input)
        st.session_state["messages"].append({"role": "assistant", "content": stage_message})

        # RAGからのアドバイス生成
        rag_response = generate_rag_response(user_input)
        st.session_state["messages"].append({"role": "assistant", "content": f"RAGによるアドバイス: {rag_response}"})

        # OpenAI APIでの補完
        additional_questions = generate_openai_questions(rag_response)
        st.session_state["messages"].append({"role": "assistant", "content": f"さらに考えるべき質問: {additional_questions}"})

        # 次の候補質問を提案
        next_questions = propose_next_questions()
        st.session_state["messages"].append({"role": "assistant", "content": f"次に考えるべき点: {', '.join(next_questions)}"})

# UI構築
st.title("DX & 匠メソッド AIコーチ")
communicate()

# チャット履歴保存ボタン
if st.button("セッションを保存する"):
    save_chat_history(st.session_state["messages"])
    st.success("チャット履歴が保存されました！")

# 履歴の検索
if st.button("過去の履歴から検索する"):
    index = index_chat_history()
    query_engine = index.as_query_engine()
    query = st.text_input("検索クエリを入力してください")
    if query:
        response = query_engine.query(query)
        st.write(f"検索結果: {response}")

# メッセージ表示
if st.session_state["messages"]:
    for message in reversed(st.session_state["messages"]):
        role = "🙂" if message["role"] == "user" else "🤖"
        st.write(f"{role}: {message['content']}")
