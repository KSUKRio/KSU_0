import streamlit as st

st.title("こんにちは、吉村ゼミ")

name = st.text_input("名前を入力")
st.write(name)

st.checkbox("同意します")

adress = st.selectbox("次の中から現住所を教えてください",["京都府","大阪府"])
st.write(adress)

st.multiselect("次から複数選択してください",["映画","音楽","散歩"])

camera = st.camera_input("写真を撮影します！")
if camera:
  st.image(camera, caption="写真", use_column_width=True)
  
