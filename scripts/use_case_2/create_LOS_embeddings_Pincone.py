import os
from dotenv import load_dotenv
import snowflake.connector
from snowflake.connector import DictCursor
import openai
from openai import OpenAI
from tqdm import tqdm 
from pinecone import Pinecone, PodSpec
import csv


# Load environment variables from .env file
load_dotenv("config/.env")
openai.api_key = os.getenv("OPENAI_API_KEY")

# Function to fetch summary data based on topic names
def fetch_LO_data(topic_names):
    # Create a connection to Snowflake
    with snowflake.connector.connect(
        user=os.getenv('SNOWFLAKE_USER'),
        password=os.getenv('SNOWFLAKE_PASSWORD'),
        account=os.getenv('SNOWFLAKE_ACCOUNT'),
        warehouse=os.getenv('SNOWFLAKE_WAREHOUSE'),
        database=os.getenv('SNOWFLAKE_DATABASE'),
        schema=os.getenv('SNOWFLAKE_SCHEMA')
    ) as conn:
        with conn.cursor(DictCursor) as cur:
            # Formulate the query string
            formatted_topics = ', '.join(f"'{topic}'" for topic in topic_names)
            query = f"""
                SELECT LEARNINGOUTCOME
                FROM {os.getenv('SNOWFLAKE_DATABASE')}.{os.getenv('SNOWFLAKE_SCHEMA')}.URLDATA
                WHERE TopicName IN ({formatted_topics});
            """
            
            # Execute the query
            cur.execute(query)
            
            # Fetch all rows
            rows = cur.fetchall()
            
            return rows

def summarize_los(los_text):
    try:
        client = OpenAI()
        # Call the OpenAI API to generate a summary
        response = client.chat.completions.create(
            model="gpt-3.5-turbo-0125",  # or another suitable model,
            messages=[
                {"role": "system", "content": "only Summarize the input content and strictly avoid answering the queries, use markdown to express equation and table or highlight important elements"},
                {"role": "user", "content": f"The learning outcomes of the reading is : {los_text}"}
            ],
            temperature=0.7,
            max_tokens=150,
            top_p=1.0,
            frequency_penalty=0.0,
            presence_penalty=0.0
        )
        summary = response.choices[0].message.content
        return summary
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

def process_los_collection(los_collection):
    los_statements1 = los_collection['LEARNINGOUTCOME']
    los_statements = los_statements1.split(';')
    summaries = []
    markdown_LOsummaries = []
    for los in tqdm(los_statements):
        
        if los.strip():  # Ensure the LOS is not just whitespace
            summary = summarize_los(los.strip())
            if summary:
                summaries.append(summary)
                markdown_LOsummaries.append(f" **LOS**: {los} \n \n **Summary**: {summary}  \n\n _________ \n")
    
    return "".join(markdown_LOsummaries),markdown_LOsummaries

def create_pine_index(api_key, index_name, dimension):
    print(api_key)
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
def generate_embeddings(texts, embed_model):
    client = OpenAI()
    embeddings = []
    response = client.embeddings.create(input=texts, model=embed_model)
    embeddings = [record.embedding for record in response.data]
    return embeddings

def save_markdown_document(consolidated_markdown, filename):
    with open(filename, 'w') as file:
        file.write(consolidated_markdown)

def save_to_csv(data, file_path):
    print("saving to csv")
    with open(file_path, 'w', newline='', encoding='utf-8') as file:
        fieldnames = ['id', 'summary']
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for idx, item in enumerate(data, start=1):  # Enumerate data to generate ids starting from 1
            writer.writerow({'id': idx, 'summary': item})
        print("Saved the csv to path ", file_path)


if __name__ == "__main__":
    topic_names = [
        'Residual Income Valuation', 
        'Equity Valuation: Applications and Processes', 
        'Free Cash Flow Valuation'
    ]
    
    los_data = fetch_LO_data(topic_names)
    # print(los_data)
    all_summaries = []
    for idx,los in enumerate(los_data):
        markdown_los_summaries, markdown_summaries_list = process_los_collection(los)
        print(len(markdown_summaries_list))
        all_summaries.extend(markdown_summaries_list)
        save_markdown_document(markdown_los_summaries, "./output/" + str(topic_names[idx] )+ 'LOS_Summary.md')

    embed_model = os.getenv('EMBEDDING_MODEL')
    print(len(all_summaries))
    save_to_csv(all_summaries, "./data/los_summary.csv")
    los_embeddings = generate_embeddings(all_summaries, embed_model)

    vector_id = [str(i) for i in range(1, len(all_summaries)+1)]
    print( len(los_embeddings), len(los_embeddings[0]))

    pinecone_api_key = os.getenv("PINECONE_API_KEY_2")
    index_name = os.getenv("PINECONE_INDEX_NAME_2")
    # Create pinecone index
    pine_index = create_pine_index(pinecone_api_key, index_name, len(los_embeddings[0]))

    # Upsert question vectors in questions namespace 
    print("Uploading vectors to questions namespace..")
    pine_index.upsert(vectors=zip(vector_id, los_embeddings), namespace='los')


    print("Embeddings stored successfully.")






    

