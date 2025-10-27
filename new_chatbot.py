import streamlit as st
st.set_page_config(page_title='🤖 ChatBot')
import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import google.generativeai as genai
from google.api_core.exceptions import NotFound
from streamlit_lottie import st_lottie
import requests
import json
import random
from io import StringIO


genai.configure(api_key='AIzaSyCh3M8GBfAmbc3p1ySkAAT7jbI5LrBy8NI')

# Preferred model (may not be available on all API versions/accounts). If it's
# not found at runtime, we'll fall back to a broadly supported model.
DEFAULT_MODEL_NAME = 'gemini-1.5-flash'
FALLBACK_MODELS = ['text-bison-001', 'chat-bison-001']

# Instantiate the model object lazily — we'll store the name and create the
# GenerativeModel when first used. This makes it easy to swap to a fallback
# if the chosen model isn't available for generate_content.
def discover_models_info():
    """Return a list of discovered models with a flag whether they *look* like
    they support generation (heuristic).

    Each entry is a dict: {'name': <str>, 'supports_generate': <bool>}.
    """
    infos = []
    try:
        list_fn = getattr(genai, 'list_models', None)
        if callable(list_fn):
            res = list_fn()
        else:
            client = getattr(genai, '_client', None)
            if client is not None and hasattr(client, 'list_models'):
                res = client.list_models()
            else:
                res = None

        if res is None:
            return infos

        # Normalize to iterable of items
        seq = getattr(res, 'models', None) or res
        for item in seq:
            # Try to get a model name
            name = None
            if isinstance(item, str):
                name = item
            else:
                name = getattr(item, 'name', None)
                if name is None and isinstance(item, dict):
                    name = item.get('name')

            if not name:
                # Fallback to str(item)
                try:
                    name = str(item)
                except Exception:
                    continue

            # Heuristically detect whether this model supports generate/generateContent
            supports = False
            try:
                rep = repr(item)
                if 'generate' in rep.lower():
                    supports = True
                # Inspect attributes for hints
                for attr in dir(item):
                    if 'generate' in attr.lower():
                        supports = True
                        break
                    try:
                        v = getattr(item, attr)
                        if isinstance(v, str) and 'generate' in v.lower():
                            supports = True
                            break
                        if isinstance(v, (list, tuple)):
                            for vv in v:
                                if isinstance(vv, str) and 'generate' in vv.lower():
                                    supports = True
                                    break
                    except Exception:
                        continue
            except Exception:
                supports = False

            infos.append({'name': name, 'supports_generate': supports})
    except Exception:
        # Can't discover models for some reason
        return infos
    return infos


# Discover models and prefer those that look like they support generation
model_infos = discover_models_info()
supported_models = [m['name'] for m in model_infos if m.get('supports_generate')]
discovered_names = [m['name'] for m in model_infos]

selected = None
if DEFAULT_MODEL_NAME in supported_models:
    selected = DEFAULT_MODEL_NAME
elif supported_models:
    selected = supported_models[0]
elif DEFAULT_MODEL_NAME in discovered_names:
    selected = DEFAULT_MODEL_NAME
elif discovered_names:
    selected = discovered_names[0]
else:
    # nothing discovered; fall back to our default name (will be tried lazily)
    selected = DEFAULT_MODEL_NAME

model_name = selected

# Try to instantiate now; if it fails we'll handle it in call_generate_content
try:
    model = genai.GenerativeModel(model_name=model_name)
except Exception:
    model = None


def call_generate_content(prompt_text):
    """Generate using the chosen model. If NotFound occurs, try discovered
    supported models first, then the static FALLBACK_MODELS, and finally show
    the list of discovered models to the user before re-raising.
    """
    global model, model_name
    last_exc = None

    # Ensure model object
    if model is None and model_name:
        try:
            model = genai.GenerativeModel(model_name=model_name)
        except Exception as e:
            last_exc = e

    # Try current model
    try:
        return model.generate_content(prompt_text)
    except Exception as e:
        last_exc = e
        want_fallback = isinstance(e, NotFound) or 'not found' in str(e).lower() or 'models/' in str(e).lower()

        if want_fallback:
            # First try any discovered models that looked like they support generate
            for nm in supported_models:
                if nm == model_name:
                    continue
                try:
                    model = genai.GenerativeModel(model_name=nm)
                    model_name = nm
                    return model.generate_content(prompt_text)
                except Exception as e2:
                    last_exc = e2
                    continue

            # Next try the hard-coded fallback list, but only if those names were
            # actually discovered earlier (avoids trying models that the API
            # reports as unavailable for this account/version).
            for nm in FALLBACK_MODELS:
                if nm == model_name:
                    continue
                if discovered_names and nm not in discovered_names:
                    # skip fallback if it's not listed by ListModels
                    continue
                try:
                    model = genai.GenerativeModel(model_name=nm)
                    model_name = nm
                    return model.generate_content(prompt_text)
                except Exception as e2:
                    last_exc = e2
                    continue

        # Nothing worked; surface discovered models to the user if any
        if discovered_names:
            st.error(f"Model '{model_name}' unavailable for generateContent. Discovered models: {', '.join(discovered_names)}")
        else:
            st.error("Model unavailable for generateContent and no models could be discovered via the API.")

        raise last_exc




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
        response = call_generate_content(system_prompt)
        reply = response.text
        # Show which model was used (helps debug account/model mismatches)
        st.info(f"Model used: {model_name}")


        with st.chat_message('assistant').markdown(reply):
            st.session_state.message.append({'role':'assistant','content':reply})
    else:
        st.chat_message('user').markdown(prompt)
        st.session_state.message.append({'role':'user','content':prompt})
        system_prompt = f'''
        Create a random dataset based on: "{prompt}". 
        Return ONLY the CSV data with a header row, no explanations, no code, just pure CSV text.
        '''
        response = call_generate_content(system_prompt)
        reply = response.text
        st.info(f"Model used: {model_name}")
        csv_data = reply.strip()
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
        
        
       