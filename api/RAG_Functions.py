from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

def Consolidated_Embedder(Base_url, log_container=None, progress_bar=None):
    import requests
    from bs4 import BeautifulSoup
    from urllib.parse import urljoin
    import pandas as pd
    import streamlit as st # Optional, for types or if used directly

    class DummyContainer:
        def write(self, *args, **kwargs): pass
    class DummyProgressBar:
        def progress(self, *args, **kwargs): pass
    
    if log_container is None:
        log_container = DummyContainer()
    
    if progress_bar is None:
        progress_bar = DummyProgressBar()

    
    splitter = RecursiveCharacterTextSplitter(separators=['.','!','\n','\n\n'], chunk_size=500, chunk_overlap=100)
    embedding_function = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    vectorDB = Chroma(embedding_function=embedding_function, persist_directory='./ChromaDB')
    base_url = Base_url
    to_visit_queue = [base_url]
    visited_urls = []
    pages_visited = 0
    total_estimated_pages = 1
    progress_text = 'Initializing Operation....'
    if progress_bar:
        progress_bar.progress(0, text=progress_text)

    visited_pages = pd.DataFrame(({'Category':[], 'Base URL':[], 'Current URL':[], "Content Length":[],"Chunks":[],}) ) 

    while to_visit_queue:
        url = to_visit_queue.pop(0)

        log_container.write(f"{pages_visited + 1} - Visiting URL: {url}")
        if url in visited_urls:
            log_container.write(f"URL: {url} has been already visited...")
            continue

        try:
            response = requests.get(url)
            if response.status_code==200:
                log_container.write("Succesful Retrieval of Website!!!")

            soup = BeautifulSoup(response.content, "html.parser")

            tags = soup.find_all(['h1','li','td','h2','h3','h4'])
            seen_text = set()
            content = ''
            
            for text in tags:
                t = text.get_text(strip=True)
                if len(t) > 10:
                    if t not in seen_text:
                        content += t + '\n'
                        seen_text.add(t)

            if len(content) < 100:
                log_container.write("Insufficient Data")
                visited_urls.append(url)
                log_container.write(f"Content in URL: {url} very short...")
                pages_visited+=1
                continue
            
            log_container.write(f"Content from URL: {url} extracted...")

            h1_tag = soup.find('h1')
            if h1_tag:
                category = h1_tag.get_text(strip=True)
            else:
                category = url.split('/')[-1].replace('-',' ').title()

            if pages_visited==0:
                links = soup.find_all('a', href = True)

                for link in links:
                    link_text = link.get_text(strip=True)
                    link_url = link.get('href')

                    if link_url.startswith('/'):
                        full_link = urljoin(url,link_url)
                        if full_link not in visited_urls and full_link not in to_visit_queue:
                            to_visit_queue.append(full_link)
                log_container.write(f"Total sub-links discovered {len(to_visit_queue)} ...")
                total_estimated_pages = len(to_visit_queue) 
                
            
            doc = Document(
                page_content=content,
                metadata={"url":url, "category":category}
            ) 

            chunks = splitter.split_documents([doc])
            log_container.write(f"Total chunks from {url} : {len(chunks)}")
            vectorDB.add_documents(chunks)


            visited_urls.append(url)
            pages_visited+=1

            log_container.write(f"Success in embedding {url} to Vector-DB")

            new_row = pd.DataFrame(({'Category':[category],'Base URL':[base_url], 'Current URL':[url], "Content Length":[len(content)],"Chunks":[len(chunks)]}))
            visited_pages = pd.concat([visited_pages,new_row], ignore_index=True)

            progress_text = f'Scrapped {pages_visited} out of {total_estimated_pages} URLs...'
            progress_percent = pages_visited/total_estimated_pages
            if progress_percent >=1.0: progress_percent = 1.0
            progress_bar.progress(progress_percent,text=progress_text)
        
        except Exception as e:
            log_container.write(f'Error: {e}')
        
    st.dataframe(visited_pages)   

    return vectorDB


def query_answer_generation(query,lang,my_key):
    key=my_key
    
    db = Chroma(persist_directory='./ChromaDB',
                embedding_function=HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2"))
    similar = db.similarity_search(query, k=3)

    context = ""

    for doc in similar:
        context += doc.page_content + '\n\n'

    if not context:
        return "I couldn't find any info."

    llm = ChatGroq(model_name = "llama-3.3-70b-versatile", temperature=0 , api_key=key)

    messages = [
        SystemMessage(content= "you are Nagrik AI , You are a helpful assistant that is friendly and optimistic civic engagement bot. All your responses should focus on encouraging public participation and providing accurate, non-partisan information about local government services.."),
        SystemMessage(content= "You are an expert in assesing the tone of the user(Positive /Negative/Neutral) and accordingly respond to the user in a very friendly manner that will comfort the user and make them feel heard and understood"),
        SystemMessage(content= "You will answer in stepwise manner to ensure clarity and thoroughness in your responses."),
        SystemMessage(content= "You are going to help in the Indian context only not any other country other than India"),
        SystemMessage(content= "You have to answer dynamically(length of the reply) based on the user prompt but strictly mention everything required for it like documents, advice etc, no need for greetings or endings"),
        SystemMessage(content= "You will not hallucinate any information and will strictly provide verified and accurate information only, if you don't know the answer you will politely say that you don't have the informatio"),
        SystemMessage(content= f"Reply in {lang} script"),
        SystemMessage(content=f"Context information you willanswer based on this information:\n{context}"),
        HumanMessage(content = f"The user needs help on {query}.")
    ]

    response = llm.invoke(messages)

    return response.content
