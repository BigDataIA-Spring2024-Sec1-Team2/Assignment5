import csv
from pinecone import Pinecone, PodSpec
import numpy as np
from dotenv import load_dotenv
import os
from openai import OpenAI
import sys


current_directory = os.getcwd()
sys.path.append(current_directory)

load_dotenv('./config/.env',override=True)

def create_pine_index(api_key, index_name, dimension):
    pinecone = Pinecone(api_key=api_key)
    # Check whether the index with the same name already exists - if so, delete it
    if index_name in pinecone.list_indexes().names():
        pinecone.delete_index(index_name)
        
    pinecone.create_index(name=index_name, dimension=dimension, spec=PodSpec(environment="gcp-starter"))
    index = pinecone.Index(name=index_name)

    # Confirm our index was created
    print(pinecone.list_indexes())
    return index


# Define function to generate embeddings using OpenAI
def generate_embeddings(texts, embed_model, openai_api_key):
    client = OpenAI(api_key=openai_api_key,)
    embeddings = []
    response = client.embeddings.create(input=texts, model=embed_model)
    embeddings = [record.embedding for record in response.data]
    return embeddings

def process_csv(csv_file):
    questions = []
    answers = []
    with open(csv_file, 'r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            questions.append(row['question'])
            answers.append(row['answer'])
    return questions, answers



def main():
    folder_name = os.getenv("DIR_CFA_WEB")
    csv_file = folder_name + 'output.csv'
    index_name = os.getenv("PINECONE_INDEX_NAME")
    embed_model = os.getenv("EMBEDDING_MODEL")
    openai_api_key = os.getenv("OPENAI_API_KEY")
    pinecone_api_key = os.getenv("PINECONE_API_KEY")

    # Get question and answers as list from csv
    questions, answers = process_csv(csv_file)

    # Generate embeddings for questions and answers
    question_embeddings = generate_embeddings(questions, embed_model, openai_api_key)
    answer_embeddings = generate_embeddings(answers, embed_model, openai_api_key)
    vector_id = [str(i) for i in range(len(question_embeddings))]
    print(len(question_embeddings), len(answer_embeddings), len(answer_embeddings[0]))

    # Create pinecone index
    pine_index = create_pine_index(pinecone_api_key, index_name, len(answer_embeddings[0]))

    # Upsert question vectors in questions namespace 
    print("Uploading vectors to questions namespace..")
    pine_index.upsert(vectors=zip(vector_id, question_embeddings), namespace='questions')

    # Upsert answer vectors in answers namespace 
    print("Uploading vectors to answers namespace..")
    pine_index.upsert(vectors=zip(vector_id, answer_embeddings), namespace='answers')

    print("Embeddings stored successfully.")

if __name__ == "__main__":
    main()
