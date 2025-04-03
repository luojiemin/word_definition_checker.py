# Web词典释义比对系统（使用有道词典原始中文释义）
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

# 有道词典 API 设置（获取真实中文释义）
appKey = "720d00d3f9ba68fd"
appSecret = "2G4KewXAmgLFO8GUx4mmWhKcg8okTJT4"

def get_youdao_definition(word):
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
        res = requests.get(url, params=params, timeout=5)
        data = res.json()
        if "basic" in data and "explains" in data["basic"]:
            return "; ".join(data["basic"]["explains"])
        elif "translation" in data:
            return "; ".join(data["translation"])
        return ""
    except Exception as e:
        st.warning(f"有道API请求失败：{e}")
        return ""

# 相似度计算
def similarity(a, b):
    try:
        v = TfidfVectorizer().fit_transform([str(a), str(b)])
        return cosine_similarity(v[0:1], v[1:2])[0][0]
    except:
        return 0.0

# 相似度标签
def label_similarity(score):
    if score >= 0.8:
        return "高一致"
    elif score >= 0.6:
        return "可接受"
    else:
        return "需核查"

# Streamlit 界面
st.title("词汇释义比对系统（使用有道原始释义）")
st.markdown("本系统从有道词典获取原始中文解释，与词表释义直接比对，更准确更稳定。")

uploaded_file = st.file_uploader("上传词库Excel文件（含 单词 和 释义 两列）")

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)
        if "单词" in df.columns and "释义" in df.columns:
            with st.spinner("正在查询词典并比对释义..."):
                df["有道释义"] = df["单词"].apply(lambda w: get_youdao_definition(str(w)))
                df["相似度"] = df.apply(lambda row: similarity(row["释义"], row["有道释义"]), axis=1)
                df["相似度等级"] = df["相似度"].apply(label_similarity)
                df["需人工复查"] = df["相似度等级"] == "需核查"

            st.success("比对完成，以下是结果：")
            st.dataframe(df)

            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="全部结果")
                df[df["需人工复查"]].to_excel(writer, index=False, sheet_name="需人工复查")
                df[df["相似度等级"] == "高一致"].to_excel(writer, index=False, sheet_name="高一致")
            st.download_button("下载多表Excel报告", data=output.getvalue(), file_name="释义比对_有道原始释义.xlsx")

        else:
            st.error("Excel中必须包含 '单词' 和 '释义' 两列")
    except Exception as e:
        st.error(f"处理过程中出现错误：{e}")
else:
    st.info("请上传文件")
