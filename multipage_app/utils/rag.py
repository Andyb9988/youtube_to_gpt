import regex as re
from pinecone import ServerlessSpec, PodSpec
from pinecone import Pinecone as Pinecone_Client
import openai
from openai import OpenAI
import langchain
import json
import string
import re
from utils.helper import Helper
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_pinecone import PineconeVectorStore
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableParallel, RunnablePassthrough, RunnableLambda
import time
from langchain.prompts import (
    PromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
    ChatPromptTemplate,
)
from langchain.retrievers.multi_query import MultiQueryRetriever
from utils.vector_database import Pinecone
import streamlit as st
import logging

config_path = "config.json"

class YoutubeSearchAssistant:
    def __init__(self):
        self.index_name = 'youtube-transcripts'

    def langchain_embeddings(self, model_name='text-embedding-3-small'):
        embeddings = OpenAIEmbeddings(
            model=model_name,
            dimensions=1536)
        return embeddings

    def langchain_vectorstore(self, index, embeddings):
        vectorstore = PineconeVectorStore(index, embeddings)
        return vectorstore

    def langchain_retriever(self, vectorstore):
        retriever = vectorstore.as_retriever()
        return retriever

    def multi_query_retriever(self, vectorstore, llm):
        vectorstore_retriever = vectorstore.as_retriever(k=10)
        retriever = MultiQueryRetriever.from_llm(
            retriever=vectorstore_retriever, llm=llm
        )
        return retriever

    def prompt_system_human_prompt(self):
        review_system_template_str = """
        You are a highly efficient virtual assistant 
        designed to answers user queries 
        through extract valuable information 
        from video transcripts, using the context provided. 
        Your primary goal is to provide insightful and concise summaries of the content within the transcripts. 
        You excel in identifying key topics, extracting relevant details, and presenting the information in a clear and coherent manner. 
        Your users rely on you to distill complex video content into easily understandable insights. 
        Keep in mind the importance of accuracy, clarity, and brevity in your responses.
        If the question cannot be answered using the information provided say "I don't know".
                
        context:
        {context}
        """

        review_system_prompt = SystemMessagePromptTemplate(
            prompt=PromptTemplate(
                input_variables=["context"], template=review_system_template_str
            )
        )

        review_human_prompt = HumanMessagePromptTemplate(
            prompt=PromptTemplate(
                input_variables=["question"], template="{question}"
            )
        )

        messages = [review_system_prompt, review_human_prompt]
        review_prompt_template = ChatPromptTemplate(
            input_variables=["context", "question"],
            messages=messages,)

        return review_prompt_template

    def langchain_model(self):
        model = ChatOpenAI(temperature=0.2, model="gpt-3.5-turbo-0125")
        return model

    def langchain_chain(self, retriever, prompt, model):
        chain = (
            RunnableParallel({"context": retriever, "question": RunnablePassthrough()})
            | prompt
            | model
            | StrOutputParser())
        return chain

    def langchain_invoke(self, chain):
        query = str(input("What do you want to search on Youtube?"))
        try:
            result = chain.invoke(query)
            print(result)
        except Exception as e:
            print(f"Error: {str(e)}")
    
    def langchain_streamlit_invoke(self, prompt, chain):
        query = prompt
        try:
            result = chain.invoke(query)
            if result is None:
                st.write("No response generated.")  # Handle None by displaying a default message
            else:
                st.write(result)  # Use st.write for string outputs
        except Exception as e:
            st.write(f"Error: {str(e)}")


def main():
    helper = Helper(config_path)
    config = helper.load_config()
    pinecone_api = config["PINECONE_API_KEY"]
    openai_api = config["OPENAI_API_KEY"]
    pinecone_assistant = PineconeAssistant(pinecone_api)
    yt_search = YoutubeSearchAssistant()

    #Pinecone 
    index = pinecone_assistant.create_pinecone_index()

    #Langchain Chain
    embeddings = yt_search.langchain_embeddings()
    vectorstore = yt_search.langchain_vectorstore(index, embeddings)
    model = yt_search.langchain_model()

    retriever = yt_search.multi_query_retriever(vectorstore,model)
    prompt = yt_search.prompt_system_human_prompt()

    chain = yt_search.langchain_chain(retriever, prompt, model)
    yt_search.langchain_invoke(chain)

if __name__ == "__main__":
    main()
