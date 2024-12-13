import streamlit as st
import pandas as pd
import datetime
import os

# Initialize app and session state if necessary
if 'responses' not in st.session_state:
    st.session_state['responses'] = []
if 'final_schedule' not in st.session_state:
    st.session_state['final_schedule'] = None
if 'response_files' not in st.session_state:
    st.session_state['response_files'] = []

st.title("🎉 飲み会日程調整アプリ 🍻")

# 幹事ページ
if 'is_admin' not in st.session_state:
    st.session_state['is_admin'] = True

if st.session_state['is_admin']:
    st.header("幹事ページ")

    # 1. 日程範囲を選択
    date_range = st.date_input(
        "飲み会の日程範囲を選択してください",
        [datetime.date.today(), datetime.date.today() + datetime.timedelta(days=7)],
        min_value=datetime.date.today(),
    )

    # 2. 回答期限を設定
    deadline = st.date_input(
        "回答期限を設定してください", datetime.date.today() + datetime.timedelta(days=3)
    )

    # 3. コメントを入力
    comment = st.text_area("参加者へのコメント")

    # 4. 登録ボタンを押すとリンク生成
    if st.button("リンクを発行"):
        st.session_state['is_admin'] = False
        st.session_state['dates'] = [date_range[0] + datetime.timedelta(days=i) for i in range((date_range[1] - date_range[0]).days + 1)]
        st.success("参加者用リンクが生成されました！下のボタンで切り替えてテストできます。")

    st.markdown("---")
    st.markdown("### 参加者ページを確認するにはボタンを押してください")
    if st.button("参加者ページを見る"):
        st.session_state['is_admin'] = False

    # 確定した日程を表示
    if st.session_state['final_schedule']:
        st.markdown("### 確定した日程")
        st.markdown(f"<h3 style='color: green;'>🌟 最適日程: {st.session_state['final_schedule']['最適日程']} 🌟</h3>", unsafe_allow_html=True)
        st.markdown(f"<p style='color: blue;'>スコア: {st.session_state['final_schedule']['スコア']} 点</p>", unsafe_allow_html=True)
        st.balloons()

        # 案内メールの定型文生成
        st.markdown("### 案内メール定型文")
        default_email = (
            f"件名: 【確定】飲み会日程のお知らせ\n\n"
            f"皆様\n\n"
            f"お忙しい中、飲み会日程調整にご協力いただきありがとうございました。\n"
            f"AIによるスコア計算の結果、以下の日程に決定いたしました！\n\n"
            f"【最適日程】\n"
            f"{st.session_state['final_schedule']['最適日程']}\n\n"
            f"ぜひご参加ください！\n"
            f"引き続きよろしくお願いいたします。\n\n"
            f"幹事より"
        )
        email_text = st.text_area("案内メール文を編集してください", value=default_email, height=200)
        if st.button("メール定型文をコピー"):
            st.write("メール定型文をコピーしました！")

# 参加者ページ
else:
    st.header("参加者ページ")

    # 1. 役職を選択
    role = st.selectbox(
        "あなたの役職を選んでください",
        ["一般", "リーダークラス", "部長クラス", "本部長クラス", "社長クラス"],
    )

    # 2. 日程ごとに希望を回答（チェックシート方式）
    st.write("日程ごとに以下の希望をチェックしてください:")
    options = ["絶対行ける", "たぶん行ける", "未定", "たぶん行けない", "絶対行けない"]

    date_responses = {}
    if 'dates' in st.session_state:
        for date in st.session_state['dates']:
            st.markdown(f"**{date}**")
        
        # ラジオボタンを使用してオプションを選択
            selected_option = st.radio(
                f"{date}",  # ラベル
                options,  # 選択肢のリスト
                key=f"{date}_radio"  # 一意のキー
                )
        
        # 選択されたオプションを保存
            date_responses[str(date)] = selected_option


    # 3. 回答完了ボタン
    if st.button("回答を送信"):
        response = {
            "役職": role,
            **{date: date_responses.get(str(date), "未定") for date in st.session_state['dates']},
        }
        # 保存するCSVファイル名
        filename = f"response_{len(st.session_state['response_files']) + 1}.csv"
        pd.DataFrame([response]).to_csv(filename, index=False)
        st.session_state['response_files'].append(filename)
        st.success("回答が送信されました！")

    st.markdown("---")
    st.markdown("### 幹事ページに戻るにはボタンを押してください")
    if st.button("幹事ページを見る"):
        st.session_state['is_admin'] = True

# 回答期限後にCSVを連結して最適日程を計算
if st.session_state['is_admin'] and st.button("最適日程を計算"):
    # 役職に応じた重み付け
    weights = {
        "一般": 1,
        "リーダークラス": 2,
        "部長クラス": 3,
        "本部長クラス": 4,
        "社長クラス": 5
    }

    # CSVファイルを連結
    all_responses = pd.DataFrame()
    for file in st.session_state['response_files']:
        all_responses = pd.concat([all_responses, pd.read_csv(file)], ignore_index=True)

    # 日程スコア計算
    scores = {date: 0 for date in st.session_state['dates']}

    for _, response in all_responses.iterrows():
        role_weight = weights[response["役職"]]
        for date in st.session_state['dates']:
            if str(date) in response:
                choice = response[str(date)]
                if response["役職"] in ["本部長クラス", "社長クラス"] and choice == "絶対行ける":
                    scores[date] += 2 * role_weight
                elif response["役職"] == "部長クラス" and choice in ["絶対行ける", "たぶん行ける"]:
                    scores[date] += 1 * role_weight
                elif response["役職"] not in ["本部長クラス", "社長クラス", "部長クラス"]:
                    if choice == "絶対行ける":
                        scores[date] += 2 * role_weight
                    elif choice == "たぶん行ける":
                        scores[date] += 1 * role_weight

    # 最適日程の計算
    best_date = max(scores, key=scores.get)
    st.session_state['final_schedule'] = {"最適日程": best_date, "スコア": scores[best_date]}

    st.markdown(f"<h2 style='color: red;'>🎉 最適な飲み会の日程が確定しました！ 🎉</h2>", unsafe_allow_html=True)
    st.markdown(f"<h3 style='color: green;'>🌟 最適日程: {best_date} 🌟</h3>", unsafe_allow_html=True)
    st.markdown(f"<p style='color: blue;'>スコア: {scores[best_date]} 点</p>", unsafe_allow_html=True)
    st.balloons()

    # 案内メールの定型文生成
    st.markdown("### 案内メール定型文")
    default_email = (
        f"件名: 【確定】飲み会日程のお知らせ\n\n"
        f"皆様\n\n"
        f"お忙しい中、飲み会日程調整にご協力いただきありがとうございました。\n"
        f"AIによるスコア計算の結果、以下の日程に決定いたしました！\n\n"
        f"【最適日程】\n"
        f"{best_date}\n\n"
        f"ぜひご参加ください！\n"
        f"引き続きよろしくお願いいたします。\n\n"
        f"幹事より"
    )
    email_text = st.text_area("案内メール文を編集してください", value=default_email, height=200)
    if st.button("メール定型文をコピー"):
        st.write("メール定型文をコピーしました！")
