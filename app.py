# -*- coding: utf-8 -*-
import os
os.environ["PYTHONIOENCODING"] = "utf-8"

import sys
sys.stdout.reconfigure(encoding='utf-8')

import streamlit as st
from google import genai
import re

# ==========================================
# 1. ページの設定とAIの準備
# ==========================================
st.set_page_config(page_title="冷蔵庫レシピ提案アプリ Pro", page_icon="🍳", layout="wide")

# 🔒【セキュリティ対応】
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception:
    API_KEY = "" # 🚨手元のPCでテストするときはここにキーを入れてください

client = genai.Client(api_key=API_KEY)

# ==========================================
# 2. アプリのタイトルと説明
# ==========================================
st.title("🍳 冷蔵庫の残り物レシピ提案アプリ Pro")
st.write("家にある食材から、AIが5つの異なる絶品レシピを提案します。今日の気分で選びましょう！")

# ✨ 変更箇所：スクショ推奨のお知らせボックスを追加
st.info("💡 **【お知らせ】**\nこのアプリにはお気に入り登録機能がありません。もう一度作りたいお気に入りレシピに出会えた場合は、**スクリーンショットでの保存**をおすすめします！📸")

st.markdown("---")

# ==========================================
# アコーディオンの開閉状態を確実にコントロールする仕組み
# ==========================================
if "menu_expanded" not in st.session_state:
    st.session_state.menu_expanded = True # 最初は開いておく

def close_menu():
    st.session_state.menu_expanded = False # ボタンが押されたら閉じる命令

# ==========================================
# 3. 入力画面（メイン画面のアコーディオン）
# ==========================================
with st.expander("🛒 食材・条件入力（タップで開閉できます）", expanded=st.session_state.menu_expanded):
    ingredients = st.text_area(
        "1. 使い切りたい食材",
        placeholder="例: 豚肉、キャベツ、玉ねぎ",
        height=100
    )

    genre = st.radio(
        "2. 料理のジャンル",
        ["指定なし", "主食", "主菜", "副菜", "スープ・汁物", "デザート"],
        horizontal=True 
    )
    
    st.markdown("---")
    st.subheader("💡 追加条件")

    servings = st.number_input(
        "3. 何人前？（1〜10）",
        min_value=1, max_value=10, value=2, step=1
    )

    cooking_time = st.selectbox(
        "4. 調理時間の目安",
        ["指定なし", "5分以内", "15分以内", "30分以内", "1時間以内"]
    )

    col1, col2, col3 = st.columns(3)
    with col1: difficulty_easy = st.checkbox("かんたん", value=True)
    with col2: difficulty_normal = st.checkbox("ふつう", value=True)
    with col3: difficulty_hard = st.checkbox("がっつり", value=True)

    st.markdown("---")
    exclusion = st.text_input(
        "5. アレルギーや苦手な食材（あれば）",
        placeholder="例: エビ、ピーマン、しいたけ"
    )

    st.markdown("---")
    # ボタンが押された瞬間、AIが動く「前」にclose_menuを実行してアコーディオンを閉じる
    search_button = st.button("レシピを5つ提案してもらう！", type="primary", use_container_width=True, on_click=close_menu)

# ==========================================
# 4. 【ボタンとAI送信処理】
# ==========================================
if search_button:
    
    if ingredients.strip() == "":
        st.warning("食材を何か入力してください！")
        # 何も入力されずに押された場合は、もう一度入力できるようにアコーディオンを開き直す
        st.session_state.menu_expanded = True
        
    else:
        # 難易度の文字まとめ
        selected_diff = []
        if difficulty_easy: selected_diff.append("かんたん")
        if difficulty_normal: selected_diff.append("ふつう")
        if difficulty_hard: selected_diff.append("がっつり")
        diff_str = ", ".join(selected_diff) if selected_diff else "指定なし"

        # 除外食材の文字処理
        exclusion_str = exclusion.strip() if exclusion.strip() else "なし"

        # 【プロンプト】ベースコードそのまま
        prompt = f"""
        【🚨最優先・絶対遵守命令：余計な挨拶の完全禁止】
        あなたは今、過去の会話や直前の提案をすべて忘れて記憶を完全にリセットされました。
        出力する際、「はい、承知いたしました」「過去の記憶をリセットしました」といった前置き、挨拶、確認の言葉、メタ発言は「絶対に」一切出力しないでください。
        最初の文字から、必ず指定された形式（### [絵文字] レシピのタイトル）で、いきなりレシピの本文だけを出力してください。
        
        【🚨最優先・絶対遵守命令：除外食材の徹底排除】
        指定された『除外してほしい食材（アレルギー・苦手）』がある場合、**その食材をメイン具材、隠し味、調味料、出汁（だし）にいたるまで、5つのレシピすべてから「絶対に」一切排除してください。**利用者の健康と安全に関わるため、最も厳重にチェックしてください。
        
        【ユーザーの希望条件】
        - 使える食材: {ingredients}
        - 除外してほしい食材（アレルギー・苦手）: {exclusion_str}
        - 料理のジャンル: {genre}
        - 分量: {servings}人前（全レシピで厳守）
        - 調理時間の目標値: {cooking_time}
        - 難易度: {diff_str}
        
        【🚨 手順に関する最重要命令】
        料理初心者が迷わず1人で失敗なく作れるよう、**【📝 作り方】のステップごとの説明を限界まで詳しく執筆してください。**
        テキストの長さの制限はありません。「中火で約3分、お肉のピンク色が完全に消えるまで炒める」「キャベツの芯は硬いので1mm幅の薄切りにする」「フライパンが温まってから油を入れる」など、以下の要素を具体的に言葉にしてください。
        - 包丁の入れ方やサイズ（例: 3cm幅のザク切り、5mm幅の細切り）
        - 火加減の指示（強火、中火、弱火、とろ火）と、加熱時間の目安（分単位）
        - 次の工程に進んで良い状態の目安（例: 玉ねぎが透き通るまで、焼き色がつくまで、とろみがつくまで）
        
        【出力形式の指定（厳守）】
        5つのレシピを、以下のMarkdown形式で出力してください。
        レシピとレシピの間は、必ず `---RECIPE_SEPARATOR---` という文字だけで区切ってください。

        ### [絵文字] レシピのタイトル
        **「[キャッチコピー]」**
        
        ⏱️ 調理時間と難易度
        - **🔥 リアルな調理時間（{servings}人前分）:** 約 [人数と丁寧な手順を考慮した分数] 分
        - **難易度:** [難易度]
        
        🛒 材料（{servings}人分）
        | 食材・調味料 | 分量 |
        | :--- | :--- |
        | [材料] | [分量] |
        
        📝 作り方
        1. **[ステップ1のタイトル（例: 食材の切り方と下準備）]**
           - [初心者でも絶対に失敗しないレベルの超具体的な説明（長文歓迎）]
        2. **[ステップ2のタイトル（例: 具材の炒め方と火加減）]**
           - [初心者でも絶対に失敗しないレベルの超具体的な説明（長文歓迎）]
        
        💡 プロのワンポイントコツ
        - [美味しくなる裏ワザや、今回の人数（{servings}人前）だからこそ気をつけるべき注意点]
        
        ---RECIPE_SEPARATOR---
        """

        with st.spinner("🧠 Geminiがアレルギーや苦手な食材に配慮した丁寧な5つのレシピを執筆中です...お待ちください..."):
            try:
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt,
                )
                
                recipe_all_text = response.text
                
                st.success("🎉 5つの親切なレシピが完成しました！")
                
                # テキストを分解
                recipe_list = re.split(r'---RECIPE_SEPARATOR---', recipe_all_text)
                recipe_list = [r.strip() for r in recipe_list if len(r.strip()) > 50]
                
                num_recipes = len(recipe_list)
                if num_recipes == 0:
                    st.error("🚨 レシピの生成に失敗しました。もう一度試してください。")
                else:
                    # 各タブのタイトルを取得
                    tab_titles = []
                    for r in recipe_list:
                        first_line = r.split('\n')[0].replace('### ', '')
                        tab_titles.append(first_line)
                    
                    # タブの作成
                    tabs = st.tabs(tab_titles)
                    
                    # 各タブにテキストを表示
                    for i in range(num_recipes):
                        with tabs[i]:
                            st.write(recipe_list[i])
                
            except Exception as e:
                st.error("🚨 エラーが発生しました。時間を置いてもう一度試すか、条件を少し減らしてください。")
                st.write(f"(エラー詳細: {e})")
