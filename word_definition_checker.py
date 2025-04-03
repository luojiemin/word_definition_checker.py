# Web词典释义比对系统（金山词霸版）
# 安装依赖： pip install streamlit requests scikit-learn pandas openpyxl beautifulsoup4 lxml

import streamlit as st
import pandas as pd
import requests
import time
import io
from bs4 import BeautifulSoup
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# 获取金山词霸中文释义（通过网页结构解析）
def get_iciba_definition(word):
    url = f"https://www.iciba.com/word?w={word}"
    try:
        res = requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(res.text, "lxml")
        # 适配新版结构（2024）
        divs = soup.find_all("div", class_="Mean_part__1RA2V")
        explanations = []
        for div in divs:
            for li in div.find_all("li"):
                explanations.append(li.get_text(strip=True))
        return "; ".join(explanations[:3])
    except Exception as e:
        st.warning(f"金山词霸获取失败：{e}")
        return ""

# 相似度计算
def similarity(a, b):
    try:
        v = TfidfVectorizer().fit_transform([str(a), str(b)])
        return cosine_similarity(v[0:1], v[1:2])[0][0]
    except:
        return 0.0

# 相似度等级划分
def label_similarity(score):
    if score >= 0.8:
        return "高一致"
    elif score >= 0.6:
        return "可接受"
    else:
        return "需核查"

# Streamlit 界面
st.title("词汇释义比对系统（金山词霸版）")
st.markdown("本系统使用金山词霸释义，中文对中文高精度比对，更贴近教材语义。")

uploaded_file = st.file_uploader("上传词库Excel文件（含 单词 和 释义 两列）")

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)
        if "单词" in df.columns and "释义" in df.columns:
            with st.spinner("正在抓取金山释义并比对..."):
                df["金山释义"] = df["单词"].apply(lambda w: get_iciba_definition(str(w)))
                df["相似度"] = df.apply(lambda row: similarity(row["释义"], row["金山释义"]), axis=1)
                df["相似度等级"] = df["相似度"].apply(label_similarity)
                df["需人工复查"] = df["相似度等级"] == "需核查"

            st.success("比对完成，以下是结果：")
            st.dataframe(df)

            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="全部结果")
                df[df["需人工复查"]].to_excel(writer, index=False, sheet_name="需人工复查")
                df[df["相似度等级"] == "高一致"].to_excel(writer, index=False, sheet_name="高一致")
            st.download_button("下载多表Excel报告", data=output.getvalue(), file_name="释义比对报告_金山词霸.xlsx")

        else:
            st.error("Excel中必须包含 '单词' 和 '释义' 两列")
    except Exception as e:
        st.error(f"处理过程中出现错误：{e}")
else:
    st.info("请上传文件")
