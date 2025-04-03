# Web词典释义比对系统（使用有道网页版中文释义）
# 安装依赖： pip install streamlit requests scikit-learn pandas openpyxl beautifulsoup4 lxml

import streamlit as st
import pandas as pd
import requests
import time
import io
from bs4 import BeautifulSoup
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# 获取有道词典网页释义（中文解释）
def get_youdao_web_definition(word):
    url = f"https://dict.youdao.com/w/{word}"
    try:
        res = requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(res.text, "lxml")
        # 抓取中文释义区域（basic explanations）
        trans_container = soup.find("div", id="phrsListTab")
        if not trans_container:
            return ""
        lis = trans_container.find_all("li")
        explanations = [li.get_text(strip=True) for li in lis if li.get_text(strip=True)]
        return "; ".join(explanations[:3])
    except Exception as e:
        st.warning(f"有道网页释义获取失败：{e}")
        return ""

# 相似度计算
def similarity(a, b):
    try:
        v = TfidfVectorizer().fit_transform([str(a), str(b)])
        return cosine_similarity(v[0:1], v[1:2])[0][0]
    except:
        return 0.0

# 相似度等级
def label_similarity(score):
    if score >= 0.8:
        return "高一致"
    elif score >= 0.6:
        return "可接受"
    else:
        return "需核查"

# Streamlit 页面
st.title("词汇释义比对系统（有道网页释义版）")
st.markdown("本系统使用有道词典网页版中文释义，直接对比用户释义，稳定精确。")

uploaded_file = st.file_uploader("上传词库Excel文件（含 单词 和 释义 两列）")

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)
        if "单词" in df.columns and "释义" in df.columns:
            with st.spinner("正在抓取有道释义并比对..."):
                df["有道释义"] = df["单词"].apply(lambda w: get_youdao_web_definition(str(w)))
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
            st.download_button("下载多表Excel报告", data=output.getvalue(), file_name="释义比对报告_有道网页版.xlsx")

        else:
            st.error("Excel中必须包含 '单词' 和 '释义' 两列")
    except Exception as e:
        st.error(f"处理过程中出现错误：{e}")
else:
    st.info("请上传文件")
