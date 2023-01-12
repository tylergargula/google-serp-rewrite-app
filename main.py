import pandas as pd
import requests
import streamlit as st
from bs4 import BeautifulSoup
from datetime import date
from fuzzywuzzy import fuzz
from seo_data import SoupData, SerpData
import os

API_KEY = os.environ['SERP_KEY']
QUERY_URL = os.environ['SERP_QUERY_URL']


st.markdown("""
<style>
.big-font {
    font-size:50px !important;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<p class="big-font">Google SERP Rewrite App</p>
<b>Directions: </b></ br><ul>
<li>Export URL list from GSC, GA, or any other analytics tool.</li>
<li>Select device type.</li>
<li>Import file to app.</li>
<li>View output results or download file as csv.</li>
</ul>
<b>Considerations: </b></ br><ul>
<li>Upload file can be Excel or CSV.</li>
<li>URLs must be in first column.</li>
<li>Metadata is scraped from the source HTML document.</li>
<li>On-page metadata may not be retrieved if site is JavaScript heavy.</li>
<li>Analyzes first 50 URLs.</li>
</ul>
""", unsafe_allow_html=True)

today = date.today()
device_type = st.multiselect('Device Type:', options=['mobile', 'desktop'], default='desktop')
url_file = st.file_uploader('Upload file containing URLs', type=['xlsx', 'csv'])


def request_url(input_url, headers):
    response = requests.get(input_url, headers=headers)
    return response


urls_list = []
output_list = []
counter = 0
row = 2
app_run = False

if url_file is not None:
    app_run = True
    if url_file.type == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet':
        data = pd.read_excel(url_file)
        urls_list = [url for url in data[data.columns[0]]]
    elif url_file.type == 'text/csv':
        data = pd.read_csv(url_file)
        col_1 = list(data.columns)[0]
        urls_list = data[col_1].to_list()


def get_soup(input_url, headers):
    response = requests.get(input_url, headers=headers)
    analyzed_url = response.text
    try:
        b_soup = BeautifulSoup(analyzed_url, 'html.parser')
        soup_title = b_soup.title.text
        soup_description = b_soup.find(name='meta', attrs={'name': 'description'})['content']
    except TypeError:
        soup_title = "Error, title cannot be retrieved"
        soup_description = "Error, meta description cannot be retrieved"
    soup_data = SoupData(
        title=soup_title,
        description=soup_description
    )

    return soup_data


def get_serp(input_url):
    params = {
        'api_key': API_KEY,
        'q': f'site:{input_url}',
        'device': device_type
    }

    response = requests.get(
        QUERY_URL,
        params=params
    )

    try:
        serp_title = response.json()["organic_results"][0]["title"]
        serp_description = response.json()["organic_results"][0]["snippet"]
    except KeyError:
        print(f"{url} experience an error and may not be indexed in Google")
        serp_description = "Error, URL may not be indexed in Google."
        serp_title = "Error, URL may not be indexed in Google."
    serp_data = SerpData(
        title=serp_title,
        description=serp_description
    )
    return serp_data


while app_run:
    p = st.empty()
    for index, url in enumerate(urls_list[:3]):
        p.write(f'Analyzing ::  {url} :: {index + 1} of {len(urls_list)}')

        request_headers = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 12; SM-S906N Build/QP1A.190711.020; wv) AppleWebKit/537.36 (KHTML, '
                          'like Gecko) Version/4.0 Chrome/80.0.3987.119 Mobile Safari/537.36'}
        r = requests.get(url, headers=request_headers)
        status_code = r.status_code
        if status_code == 200:
            soup_content = get_soup(url, request_headers)
            serp_content = get_serp(url)
            title_compare = fuzz.ratio(soup_content.title, serp_content.title)
            desc_compare = fuzz.ratio(soup_content.description, serp_content.description)
            output_list.append(
                {'URL': url,
                 'Status Code': status_code,
                 'Title': soup_content.title[0],
                 'SERP Title': serp_content.title[0],
                 'Title Match': title_compare,
                 'Meta Description': soup_content.description,
                 'SERP Description': serp_content.description,
                 'Description Match': desc_compare,
                 'Device Type': device_type[0]
                 }

            )

        else:
            st.markdown(f"""<br></br>
                                            <h5 style="color: #E32636">The URL you entered returned a {status_code} Status Code and cannot be analyzed, try another URL.</b></h5> 
                                            """, unsafe_allow_html=True)

    app_run = False
    df = pd.DataFrame(output_list)

    column_colors = {
        "a": {
            "positive_cell": "color:red;",
            "negative_cell": "color:green;"
        },
        "b": {
            "positive_cell": "color:green;",
            "negative_cell": "color:red;"
        }
    }

    def highlight_score(value):
        if value < 60:
            color = '#fbd5d5'
        elif 60 <= value < 90:
            color = '#faeebd'
        else:
            color = '#cafabd'
        return 'background-color: %s' % color

    st.dataframe(df.style.applymap(highlight_score, subset=['Title Match', 'Description Match']))


    @st.cache
    def convert_df(df_csv):
        return df_csv.to_csv(index=False).encode('utf-8')


    csv = convert_df(df)

    st.download_button('Download SERP Rewrites', data=csv, file_name=f'SERP_rewrites_{today}.csv', mime='text/csv')

st.write('Author: [Tyler Gargula](https://www.tylergargula.dev) | Technical SEO & Software Developer')
