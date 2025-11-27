import streamlit as st

st.title("こんにちは、吉村ゼミ")

name = st.text_input("名前を入力")
st.write(name)

st.checkbox("同意します")

adress = st.selectbox("次の中から現住所を教えてください",["京都府","大阪府"])
st.write(adress)

hobby = st.multiselect("次から複数選択してください",["映画","音楽","散歩"])
st.write(hobby)

score = st.slider("この映画を10点満点で評価してください",0,10,0)
st.write(score)

st.radio("性別を選択してください",["男性","女性","その他"])

list = [
  {"latitude":35.05,"longitude":135.76},
  {"latitude":35.04,"longitude":135.75},
  ]
st.map(list)

camera = st.camera_input("写真を撮影します！")
if camera:
  st.image(camera, caption="写真", use_column_width=True)
  
