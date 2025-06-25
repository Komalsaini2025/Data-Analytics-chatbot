import streamlit as st
st.set_page_config(page_title='🤖 ChatBot')
import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import google.generativeai as genai
from streamlit_lottie import st_lottie
import requests
import json
import random
from io import StringIO


genai.configure(api_key='Use your Api key')
model=genai.GenerativeModel(model_name='gemini-1.5-flash')




def load_lottie(url):
    try:
        r = requests.get(url, timeout=5)  
        if r.status_code == 200:
            return r.json()
        st.warning(f"Animation failed to load (HTTP {r.status_code})")
        return None
    except Exception as e:
        st.error(f"Error loading animation: {str(e)}")
        return None

lottie_welcome = load_lottie("https://assets1.lottiefiles.com/packages/lf20_3rwasyjy.json")
if lottie_welcome:
    st_lottie(lottie_welcome, 
              speed=5, 
              height=200,
              key="welcome")



st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Pacifico&display=swap');

.header {
    font-family: 'Pacifico', cursive;
    font-size: 3.5rem;
    background: linear-gradient(90deg,
        #9D50BB,
        #8E44AD,
        #6C5CE7,
        #2980B9,
        #3498DB
    );
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    text-align: center;
    margin-bottom: 30px;
}
</style>
<h1 class="header">Chat Bot</h1>
""", unsafe_allow_html=True)




upload_file=st.file_uploader("Upload CSV file",type=['csv'])
data=None

if upload_file is not None:
    data=pd.read_csv(upload_file)
    st.success("File uploaded successfully")
    st.info("Here is the preview of the uploaded file")
    st.dataframe(data.head())

    
if 'message' not in st.session_state:
    st.session_state.message =[]

for msg in st.session_state.message:
    with st.chat_message(msg['role']):
        st.markdown(msg['content'])

prompt=st.chat_input('Create a Sample Data or Analyse the uploaded data')

if prompt:
    if data is not None:

        st.chat_message('user').markdown(prompt)
        st.session_state.message.append({'role':'user','content':prompt})
        csv_text=data.to_csv(index=False)



        system_prompt=f'''
    ROLE: You are a senior business intelligence analyst. Your role is to analyze data and provide 
    clear, actionable business insights in plain English without writing code unless explicitly asked.
    
    DATA: Here is the dataset:
    {csv_text}


    
    INSTRUCTIONS:
    1. Never show Python/pandas code unless the user specifically asks "how to calculate this in code"
    2. Focus on business insights, trends, and recommendations
    3. Explain your analysis process in simple terms
    4. Highlight key numbers and percentages that matter
    5. Format for executives (bullet points welcome)
    
    QUESTION TO ANSWER:
    "{prompt}"
    
    RESPONSE STRUCTURE:
    • Direct answer (1-2 sentences)
    • Supporting evidence from data
    • Business implications
    '''
        response=model.generate_content(system_prompt)
        reply=response.text

    

        with st.chat_message('assistant').markdown(reply):
            st.session_state.message.append({'role':'assistant','content':reply})
    else:
        st.chat_message('user').markdown(prompt)
        st.session_state.message.append({'role':'user','content':prompt})
        system_prompt = f'''
        Create a random dataset based on: "{prompt}". 
        Return ONLY the CSV data with a header row, no explanations, no code, just pure CSV text.
        '''
        response=model.generate_content(system_prompt)
        reply=response.text
        csv_data=reply.strip()
        with st.chat_message('assistant'):
            st.markdown("Here's The Generated File:")
            try:
                Generated_file=pd.read_csv(StringIO(csv_data))
                st.dataframe(Generated_file.head())
                st.download_button(label='Download Generated CSV File',
                                   data=Generated_file.to_csv(index=False),
                                   file_name='Generated_File.csv',
                                   mime='text/csv'
                                   )
            except:
                st.error("Sorry, I couldn't generate valid CSV data. Please try again.")
                st.code(reply)


            st.session_state.message.append({'role':'assistant','content':"I've generated sample data for you!"})
        
        
       
