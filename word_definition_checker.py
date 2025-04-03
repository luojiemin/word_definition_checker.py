# Web词典释义比对系统（基于Streamlit）
# 安装依赖： pip install streamlit requests scikit-learn pandas openpyxl

import streamlit as st
import pandas as pd
import requests
import hashlib
import time
import random
import io
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# 有道API配置
def get_youdao_definition(word, appKey, appSecret):
    def truncate(q):
        return q if len(q) <= 20 else q[:10] + str(len(q)) + q[-10:]

    def sign(word, salt, curtime):
        sign_str = appKey + truncate(word) + salt + curtime + appSecret
        return hashlib.sha256(sign_str.encode('utf-8')).hexdigest()

    salt = str(random.randint(1, 65536))
    curtime = str(int(time.time()))
    s = sign(word, salt, curtime)

    url = "https://openapi.youdao.com/api"
    params = {
        "q": word,
        "from": "en",
        "to": "zh-CHS",
        "appKey": appKey,
        "salt": salt,
        "sign": s,
        "signType": "v3",
        "curtime": curtime
    }

    try:
        r = requests.get(url, params=params, timeout=5).json()
        if "basic" in r and "explains" in r["basic"]:
            return "; ".join(r["basic"]["explains"])
        elif "translation" in r:
            return "; ".join(r["translation"])
        else:
            return ""
    except Exception as e:
        st.warning(f"调用有道API时出错：{e}")
        return ""

# 相似度计算函数
def similarity(a, b):
    try:
        v = TfidfVectorizer().fit_transform([str(a), str(b)])
        return cosine_similarity(v[0:1], v[1:2])[0][0]
    except:
        return 0.0

# Web界面开始
st.title("词汇释义比对系统")
st.markdown("输入你的有道 API 密钥，上传包含单词和释义的 Excel 文件，系统将自动比对释义差异。")

appKey = st.text_input("App Key")
appSecret = st.text_input("App Secret", type="password")
uploaded_file = st.file_uploader("上传词库Excel文件（含 单词 和 释义 两列）")

if uploaded_file and appKey and appSecret:
    try:
        df = pd.read_excel(uploaded_file)
        if "单词" in df.columns and "释义" in df.columns:
            with st.spinner("正在比对释义，请稍候..."):
                df["有道释义"] = df["单词"].apply(lambda w: get_youdao_definition(str(w), appKey, appSecret))
                df["相似度"] = df.apply(lambda row: similarity(row["释义"], row["有道释义"]), axis=1)
                df["需人工复查"] = df["相似度"] < 0.6

            st.success("比对完成，以下是结果：")
            st.dataframe(df)

            output = io.BytesIO()
            df.to_excel(output, index=False, engine='openpyxl')
            st.download_button("下载结果为Excel", data=output.getvalue(), file_name="释义比对结果.xlsx")
        else:
            st.error("Excel中必须包含 '单词' 和 '释义' 两列")
    except Exception as e:
        st.error(f"处理过程中出现错误：{e}")
else:
    st.info("请上传文件并填写API信息")
