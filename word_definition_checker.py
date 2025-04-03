# Web词典释义比对系统（稳定版：英英释义 + 有道翻译）
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

# 有道翻译 API（替代 LibreTranslate）
appKey = "720d00d3f9ba68fd"
appSecret = "2G4KewXAmgLFO8GUx4mmWhKcg8okTJT4"

def translate_to_chinese(text):
    def truncate(q):
        return q if len(q) <= 20 else q[:10] + str(len(q)) + q[-10:]

    def sign(word, salt, curtime):
        sign_str = appKey + truncate(word) + salt + curtime + appSecret
        return hashlib.sha256(sign_str.encode('utf-8')).hexdigest()

    salt = str(random.randint(1, 65536))
    curtime = str(int(time.time()))
    s = sign(text, salt, curtime)

    url = "https://openapi.youdao.com/api"
    params = {
        "q": text,
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
        if "translation" in data:
            return "; ".join(data["translation"])
        return ""
    except Exception as e:
        st.warning(f"翻译出错：{e}")
        return ""

# Free Dictionary API - 获取英英释义
def get_english_definition(word):
    url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
    try:
        res = requests.get(url, timeout=5)
        data = res.json()
        if isinstance(data, list) and "meanings" in data[0]:
            definitions = []
            for meaning in data[0]["meanings"]:
                for d in meaning.get("definitions", []):
                    definitions.append(d.get("definition", ""))
            return "; ".join(definitions[:2])
        else:
            return ""
    except Exception as e:
        st.warning(f"词典接口出错：{e}")
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
st.title("词汇释义比对系统（稳定版）")
st.markdown("系统使用英英释义 + 有道翻译 + 相似度分级，生成准确可视化报告。")

uploaded_file = st.file_uploader("上传词库Excel文件（含 单词 和 释义 两列）")

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)
        if "单词" in df.columns and "释义" in df.columns:
            with st.spinner("正在处理词汇，请稍候..."):
                df["英英释义"] = df["单词"].apply(lambda w: get_english_definition(str(w)))
                df["英英释义翻译"] = df["英英释义"].apply(lambda e: translate_to_chinese(e))
                df["相似度"] = df.apply(lambda row: similarity(row["释义"], row["英英释义翻译"]), axis=1)
                df["相似度等级"] = df["相似度"].apply(label_similarity)
                df["需人工复查"] = df["相似度等级"] == "需核查"

            st.success("比对完成，以下是结果：")
            st.dataframe(df)

            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="全部结果")
                df[df["需人工复查"]].to_excel(writer, index=False, sheet_name="需人工复查")
                df[df["相似度等级"] == "高一致"].to_excel(writer, index=False, sheet_name="高一致")
            st.download_button("下载多表Excel报告", data=output.getvalue(), file_name="释义比对报告_有道翻译.xlsx")

        else:
            st.error("Excel中必须包含 '单词' 和 '释义' 两列")
    except Exception as e:
        st.error(f"处理过程中出现错误：{e}")
else:
    st.info("请上传文件")
