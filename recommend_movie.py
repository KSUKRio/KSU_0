import streamlit as st
import pandas as pd
import numpy as np

# ファイルの読み込み
url = "https://github.com/aimathstats/dataviz1/raw/refs/heads/main/data/movie_rate.xlsx"
real2 = pd.read_excel(url)

# 初期設定
M = 4   # 因子数
k = 0.5
lr = 0.001
E = 20000

# 画面表示
st.title("映画推薦システム")
st.write("10段階で見たことある映画を評価してください")

movie_list = list(real2.columns)
user_input = {}

for movie in movie_list:
    rating = st.slider(f"{movie}", 0, 10, 0)
    user_input[movie] = np.nan if rating == 0 else rating

if st.button("推薦を表示"):
    # 新しい行として追加
    user_series = pd.Series(user_input) #ひとまずスライダー入力をseries形式に保存
    real2_with_user = pd.concat([real2, user_series.to_frame().T], ignore_index=True) #Seriesをdfに変換

    # 初期化
    n, D = real2_with_user.shape
    U = np.random.normal(1, 0.25, (n, M))
    V = np.random.normal(1, 0.25, (D, M))

    # 学習（誤差逆伝播法）
    for _ in range(E):
        error = real2_with_user.values - np.dot(U, V.T)
        error[np.isnan(real2_with_user.values)] = 0
        gradU = 2 * np.dot(error, V) - 2 * k * U
        gradV = 2 * np.dot(error.T, U) - 2 * k * V
        U += lr * gradU
        V += lr * gradV

    pred_matrix = np.dot(U, V.T)
    user_pred = pd.Series(pred_matrix[-1], index=real2_with_user.columns)

    # すでに評価した映画を除外
    rated = ~user_series.isna() # 評価済みをブールで取得（~はブールの否定演算子で、T/Fを反転）
    recs = user_pred[~rated].sort_values(ascending=False).head(3) # 未評価映画のスコアの高い順に並べ替えて、上位３つ取得して格納

    st.subheader("あなたに推薦の映画")
    for i, (movie, score) in enumerate(recs.items(), 1):
        st.write(f"{i}.　{movie} ({score:.2f})")

