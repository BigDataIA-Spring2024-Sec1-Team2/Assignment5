import os
from airflow.models import DAG
from airflow.operators.bash_operator import BashOperator
from airflow.operators.python_operator import PythonOperator
from airflow.decorators import task
from airflow.utils.dates import days_ago
from datetime import timedelta
from typing import List, Tuple
##### TryS
import PyPDF2
from dotenv import load_dotenv
import warnings
warnings.filterwarnings("ignore")
import time

from sqlalchemy import Boolean, Column, Integer, String

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
import sys
import pandas as pd

import csv
from openai import OpenAI
import re

from pinecone import Pinecone, PodSpec
import numpy as np

from scipy.spatial import distance

import snowflake.connector
from snowflake.connector import DictCursor
import openai

from tqdm import tqdm 

# from pinecone.grpc import PineconeGRPC

openai.api_key = os.getenv("OPENAI_API_KEY")

current_directory = os.getcwd()
sys.path.append(current_directory)

load_dotenv('./config/.env',override=True)

def parse_pdf(folder_path=os.getenv("DIR_CFA_WEB")):
    # Check if the output directory exists, if not create it
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    # List all files in the input directory
    files = os.listdir(folder_path)

    for file_name in files:
        if file_name.endswith('.pdf'):
            input_file_path = os.path.join(folder_path, file_name)
            output_file_path = os.path.join(folder_path, os.path.splitext(file_name)[0] + '.txt')

            # Open the PDF file
            with open(input_file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                text = ''

                # Extract text from each page
                for page_num in range(len(reader.pages)):
                    page = reader.pages[page_num]
                    text += page.extract_text()

            # Write the extracted text to a text file
            with open(output_file_path, 'w', encoding='utf-8') as f:
                f.write(text)

            print(f"Text extracted from '{file_name}' and saved to '{output_file_path}'.")


def loadenv():
    user = os.getenv("SNOWFLAKE_USER")
    password = os.getenv("SNOWFLAKE_PASSWORD")
    db = os.getenv("SNOWFLAKE_DATABASE")
    account_identifier = os.getenv("SNOWFLAKE_ACCOUNT")
    wh = os.getenv("SNOWFLAKE_WAREHOUSE")
    return user,password ,db ,account_identifier,wh

def connectionToSnow(path='./config/.env',connection_test=False):
    load_dotenv(path,override=True)
    user, password, _, account_identifier,_ = loadenv()
    engine = create_engine(
        'snowflake://{user}:{password}@{account_identifier}/'.format(
            user=user,
            password=password,
            account_identifier=account_identifier,
        )
    )
    try:
        connection = engine.connect()
        results = connection.execute('select current_version()').fetchone()
        print(results[0])
        if connection_test:
            connection.close()
        else:
            return connection
    finally:
        engine.dispose()


def read_data(connection):
    query = "SELECT INTRODUCTION, learningoutcome, summary FROM SCRAPING_DEV.WEB_DATA.URLDATA WHERE TopicName IN ('Residual Income Valuation', 'Equity Valuation: Applications and Processes', 'Free Cash Flow Valuation');"
    res = connection.execute(query).fetchall()
    results = []
    for r in res:
        row = []
        for col in r:
            row.append(col)
        results.append(row)
    print(results)
    return results

def connect_snowflake():
    try:
        connection = connectionToSnow()
        return read_data(connection)
    except Exception as e:
        print("error", e)
    finally:
        connection.close()

def upsert_retry(pine_index,vectors,namespace,retry=15):
    print('................................in upsert retry')
    retry = 15
    retryIndicator = True
    while retry > 0 and retryIndicator :
        try :
            pine_index.upsert(vectors=vectors, namespace=namespace)
            retryIndicator = False
        except Exception as e: 
            print( 'error in upsert retry for '+namespace + "   ---> " + str(e) )
            time.sleep(5)
            retry -=1
            print('error in' +  str(retry))

def read_text_files_in_folder(folder_path):
    text_files = ''
    # Ensure the folder path is valid
    if os.path.exists(folder_path):
        # Iterate through all files in the folder
        for filename in os.listdir(folder_path):
            # Check if the file is a text file
            if filename.endswith('.txt'):
                file_path = os.path.join(folder_path, filename)
                # Read the content of the text file
                with open(file_path, 'r') as file:
                    text = file.read()
                    text_files += text
                    break
    else:
        print("Folder path does not exist.")
    return text_files

def get_knowledge_base(file_path):
    data = []
    with open(file_path, 'r') as file:
        csv_reader = csv.DictReader(file)
        for row in csv_reader:
            data.append(dict(row))
    return data

def generate_set_a(openai_api_key, topic, context):
    qna_set = []
    knowledge = "\n\nIntroduction: " + topic[0] + "\n\nLearning Outcomes: " + topic[1] + "\n\nSummary:" + topic[2]
    prompt = """Please generate 10 multiple-choice questions and their detailed answer explanations based on the given knowledge base and sample question set.

    Instructions for generating questions:
    1. Ensure that each question covers all different topics or concepts within the provided knowledge base.
    2. Frame questions in a clear and concise manner, avoiding ambiguity.
    3. Provide three options (A, B, C) for each question, ensuring that one option is correct and the other two are plausible distractors.
    4. Include both conceptual questions and those requiring calculation or application of concepts to real-world scenarios.
    5. Each question should be a practical scenario that a financial analyst faces in his job.
    6. Each question should have an explanatory answer that includes the correct option along with a very detailed explanation or rationale behind it.
    7. Consider incorporating real-world scenarios or examples to enhance the relevance of the questions.
    8. Review each question and answer for accuracy, relevance, and adherence to the provided knowledge base.
    9. The final set of questions should provide a comprehensive assessment of candidates' understanding of the CFA Level I curriculum topics.
    10. Please provide minimum 10 question and answers.
    11. Make sure there are NO duplicate questions.
    12. All the answers should be detailed explaining the concepts used to answer the question.
    
    Please analyze the provided knowledge base and sample questions to generate new question and answers that closely resemble those found in the 
    CFA exam. Pay attention to the format, difficulty level, and content coverage of the sample questions to ensure that the 
    generated questions meet the desired criteria.

    Knowledge base:
    """
    query = prompt + knowledge + "\n\nSample Set:" + context
    conv = {}
    history = [
            {"role": "system", "content": "You are A financial analyst with an MBA interested in learning more about the Learning Outcome Statement"},
            {"role": "user", "content": query}
        ]
    
    response = generate_25_qna(openai_api_key, history)
    print(response)
    qna_set.extend(parse_response(response))
    conv['role'] = "assistant"
    conv['content'] = response
    history.append(conv)

    conv['role'] = "user"
    conv['content'] = "Generate another set of 10 question and their detailed answers. Make sure that there are no duplicates and these questions are different than the previously generated questions. Also, number these questions starting from 11."
    history.append(conv)

    response = generate_25_qna(openai_api_key, history)
    print(response)
    qna_set.extend(parse_response(response))

    conv['role'] = "user"
    conv['content'] = "Generate another set of 10 question and their detailed answers. Make sure that there are no duplicates and these questions are different than the previously generated questions. Also, number these questions starting from 11."
    history.append(conv)

    response = generate_25_qna(openai_api_key, history)
    print(response)
    qna_set.extend(parse_response(response))

    conv['role'] = "user"
    conv['content'] = "Generate another set of 10 question and their detailed answers. Make sure that there are no duplicates and these questions are different than the previously generated questions. Also, number these questions starting from 11."
    history.append(conv)

    response = generate_25_qna(openai_api_key, history)
    print(response)
    qna_set.extend(parse_response(response))

    conv['role'] = "user"
    conv['content'] = "Generate another set of 10 question and their detailed answers. Make sure that there are no duplicates and these questions are different than the previously generated questions. Also, number these questions starting from 11."
    history.append(conv)

    response = generate_25_qna(openai_api_key, history)
    print(response)
    qna_set.extend(parse_response(response))


    return qna_set


def generate_25_qna(client, history):
    # initialize openai API key
    

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=history
    )
    return (response.choices[0].message.content)

def parse_response(response):
    try:
        # questions = response.split("Answer:")
        questions = response.split("Answer:")
        res = []
        ques = {}
        ques["question"] = questions[0].strip()
        # next_ques = re.split(r"(?:\d+\.|Question(?:\s+\d+)?:)", questions[1])
        next_ques = re.split(r"(?:\d+\.|Ques(?:\s+\d+)?:)", questions[1])
        ques["answer"] = next_ques[0].strip()
        res.append(ques)
        print("\n")
        print(ques)
        for i in range(2,len(questions)):
            try:
                ques = {}
                ques["question"] = next_ques[1].strip()
                # next_ques = re.split(r"(?:\d+\.|Question(?:\s+\d+)?:)", questions[i])
                next_ques = re.split(r"(?:\d+\.|Ques(?:\s+\d+)?:)", questions[i])
                ques["answer"] = next_ques[0].strip()
                res.append(ques)
                print("\n")
                print(ques)
            except Exception as e:
                print("## The error while parsing response is: ", e ,"##")
        print("Parsed ", len(res) ) 
        return res
    except Exception as e:
        print("## The error while parsing response is: ", e ,"##")
        return []

def save_to_csv_qna(data, file_path):
    print("saving to csv")
    with open(file_path, 'w', newline='', encoding='utf-8') as file:
        fieldnames = ['id', 'question', 'answer']  # Added 'id' to the fieldnames
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for idx, item in enumerate(data, start=1):  # Enumerate data to generate ids starting from 1
            writer.writerow({'id': idx, 'question': item['question'], 'answer': item['answer']})
        print("Saved the csv to path ", file_path)


def qna_main_block():


    knowledge_base = connect_snowflake();

    folder_path = os.getenv("DIR_CFA_WEB")
    openai_api_key = os.getenv("OPENAI_API_KEY")
    context = read_text_files_in_folder(folder_path)
    client = OpenAI(api_key=openai_api_key,)
    
    print(len(context), len(knowledge_base))
    ques_ans_set_a = []
    for topic in knowledge_base:
        print("Processing Set A")
        ques_ans_set_a.extend(generate_set_a(client, topic, context))
        print(len(ques_ans_set_a))
    save_to_csv_qna(ques_ans_set_a, folder_path+"set_a.csv")

    ques_ans_set_b = []
    for topic in knowledge_base:
        print("Processing Set B")
        ques_ans_set_b.extend(generate_set_a(client, topic, context))
        print(len(ques_ans_set_b))
    save_to_csv_qna(ques_ans_set_b, folder_path+"set_b.csv")


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
    vector_id = []
    with open(csv_file, 'r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            vector_id.append(row['id'])
            questions.append(row['question'])
            answers.append(row['answer'])
    return vector_id, questions, answers



def save_to_pinecone_main_block():
    folder_name = os.getenv("DIR_CFA_WEB")
    csv_file = folder_name + 'set_a.csv'
    index_name = os.getenv("PINECONE_INDEX_NAME")
    embed_model = os.getenv("EMBEDDING_MODEL")
    openai_api_key = os.getenv("OPENAI_API_KEY")
    pinecone_api_key = os.getenv("PINECONE_API_KEY")

    # Get question and answers as list from csv
    vector_id, questions, answers = process_csv(csv_file)

    # Generate embeddings for questions and answers
    question_embeddings = generate_embeddings(questions, embed_model, openai_api_key)
    answer_embeddings = generate_embeddings(answers, embed_model, openai_api_key)
    print(len(question_embeddings), len(answer_embeddings), len(answer_embeddings[0]))

    # Create pinecone index
    retry = 15
    retryIndicator = True
    while retry>0 and retryIndicator :
        try :
            pine_index = create_pine_index(pinecone_api_key, index_name, len(answer_embeddings[0]))
            
            retryIndicator = False
        except Exception as e: 
            print( 'error in create pine index retry for '+namespace + "   ---> " + str(e) )
            time.sleep(1)
            retry -=1
            print('error in' +  str(retry))
    # Upsert question vectors in questions namespace 
    print("Uploading vectors to questions namespace..")
    print(vector_id)
    vectors=list(zip(vector_id, question_embeddings))
    namespace='questions'
    upsert_retry(pine_index,vectors,namespace,retry=15)

    # Upsert answer vectors in answers namespace 
    print("Uploading vectors to answers namespace..")

    vectors=list(zip(vector_id, answer_embeddings))
    namespace='answers'
    upsert_retry(pine_index,vectors,namespace,retry=15)


    print("Embeddings stored successfully.")

def get_question_bank(file_path):
    data = []
    with open(file_path, 'r') as file:
        csv_reader = csv.DictReader(file)
        for row in csv_reader:
            data.append(dict(row))
    df = pd.DataFrame(data)
    return df

def query_article(ques, ques_mapped, answer_mapped, namespace, client,index, top_k=3):
    
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL")

    # Create vector embeddings based on the title column
    embedded_query = client.embeddings.create(input=ques,model=EMBEDDING_MODEL,).data[0].embedding

    # Query namespace passed as parameter using title vector
    query_result = index.query(vector=embedded_query, 
                                      namespace=namespace, 
                                      top_k=top_k)
    if not query_result.matches:
        print('no query result')
    
    matches = query_result.matches
    ids = [res.id for res in matches]
    scores = [res.score for res in matches]
    df = pd.DataFrame({'id':ids, 
                       'score':scores,
                       'question': [ques_mapped[_id] for _id in ids],
                       'answer': [answer_mapped[_id] for _id in ids],
                       })
    return df

def get_answer(openai_client, question, context):
    query = "Answer the question based on the context below and also provide an explaination for the answer. \n\nContext:\n" + context + "\nQuestion:\n" + question
    # print(query)
    history = [
            {"role": "system", "content": "You are A financial analyst with an MBA interested in learning more about the Learning Outcome Statement"},
            {"role": "user", "content": query}
        ]
    response = openai_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=history
    )
    return (response.choices[0].message.content)

def strings_ranked_by_relatedness(
    query1: str,
    query2: str,
    embedding_model,
    relatedness_fn=lambda x, y: 1 - distance.cosine(x, y)
) -> Tuple[List[str], List[float]]:
    """Returns a list of strings and relatednesses, sorted from most related to least."""
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"),)
    query1_embedding_response = client.embeddings.create(
        model=embedding_model,
        input=query1,
    )
    query1_embedding = query1_embedding_response.data[0].embedding
    
    query2_embedding_response = client.embeddings.create(
        model=embedding_model,
        input=query2,
    )
    query2_embedding = query2_embedding_response.data[0].embedding
    
    relatedness = relatedness_fn(query1_embedding, query2_embedding)
    
    return query1, query2, relatedness

def save_to_csv_report(data, file_path):
    print("saving to csv")
    with open(file_path, 'w', newline='', encoding='utf-8') as file:
        fieldnames = ['id', 'question', 'true_ans', 'generated_ans', 'relativity']  # Added 'id' to the fieldnames
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for idx, item in enumerate(data, start=1):  # Enumerate data to generate ids starting from 1
            writer.writerow({'id': idx, 'question': item['question'], 'true_ans': item['true_ans']
                             , 'generated_ans': item['generated_ans'], 'relativity': item['relativity']})
        print("Saved the csv to path ", file_path)


def use_case_3_main_block(part, file_name):
    folder_path = os.getenv("DIR_CFA_WEB")
    file_path_b = folder_path + 'set_b.csv'
    file_path_a = folder_path + 'set_a.csv'
    file_path_summary = folder_path + 'los_summary.csv'
    openai_api_key = os.getenv("OPENAI_API_KEY")
    
    # 1. get set b questions
    set_a = get_question_bank(file_path_a)
    set_b = get_question_bank(file_path_b)
    summary = get_question_bank(file_path_summary)
    
    openai_client = OpenAI(api_key=openai_api_key,)

    # Get pinecone index
    if part == 'set_a':
        api_key = os.getenv("PINECONE_API_KEY")
        index_name = os.getenv("PINECONE_INDEX_NAME")
        namespace = 'questions'

        # First we'll create dictionaries mapping vector IDs to their outputs so we can retrieve the text for our search results
        ques_mapped = dict(zip(set_a.id,set_a.question))
        answer_mapped = dict(zip(set_a.id,set_a.answer))
        print(len(ques_mapped), len(answer_mapped))

    else:
        api_key = os.getenv("PINECONE_API_KEY_2")
        index_name = os.getenv("PINECONE_INDEX_NAME_2")
        namespace = 'los'

        # First we'll create dictionaries mapping vector IDs to their outputs so we can retrieve the text for our search results
        ques_mapped = dict(zip(summary.id,summary.summary))
        answer_mapped = dict(zip(summary.id,summary.summary))
        print(len(ques_mapped), len(answer_mapped))
    
    print("Pinecone index = ", index_name)
    pinecone = Pinecone(api_key=api_key)
    pine_index = pinecone.Index(name=index_name)
    final_df = []

    # 2. find 3 questions in Set A that are most similar
    for idx, row in set_b.iterrows():
        print("Processing question ", idx)
        df = query_article(row['question'], ques_mapped, answer_mapped, namespace, openai_client, pine_index)

        # 3. pass the answers of these 3 questions to GPT-4 along with the question
        context = ''.join(df.answer.values)
        response = get_answer(openai_client,row['question'], context)
       
        # 4. Compare the answer to the answer it correctly determined in step 3
        true_ans = row['answer']
        query1, query2, relatedness = strings_ranked_by_relatedness(response, true_ans, 'text-embedding-3-small') 
        obj = {
            "question" : row['question'],
            "true_ans" : true_ans,
            "generated_ans" : response,
            "relativity" : relatedness
        }
        final_df.append(obj)
    save_to_csv_report(final_df, folder_path + file_name +'.csv')

def use_case_3_final_block():
    use_case_3_main_block("set_a", "report_part_3")
    use_case_3_main_block("summary", "report_part_4")


def fetch_LO_data(topic_names):
    conn = snowflake.connector.connect(
        user=os.getenv('SNOWFLAKE_USER'),
        password=os.getenv('SNOWFLAKE_PASSWORD'),
        account=os.getenv('SNOWFLAKE_ACCOUNT'),
        warehouse=os.getenv('SNOWFLAKE_WAREHOUSE'),
        database=os.getenv('SNOWFLAKE_DATABASE'),
        schema=os.getenv('SNOWFLAKE_SCHEMA')
    )
    
    try:
        # Create cursor
        # cur = conn.cursor(snowflake.connector.DictCursor)
        cur = conn.cursor()
        
        # Set warehouse
        print("###########################", os.getenv("SNOWFLAKE_WAREHOUSE"))
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
        cur.close()
        conn.close()
        return rows
    
    finally:
        # Close cursor and connection
        cur.close()
        conn.close()


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
    # los_statements1 = los_collection['LEARNINGOUTCOME']
    los_statements1 = los_collection[0]
    los_statements = los_statements1.split(';')
    summaries = []
    markdown_LOsummaries = []
    for los in tqdm(los_statements[:]):
        
        if los.strip():  # Ensure the LOS is not just whitespace
            summary = summarize_los(los.strip())
            if summary:
                summaries.append(summary)
                markdown_LOsummaries.append(f" **LOS**: {los} \n \n **Summary**: {summary}  \n\n _________ \n")
    
    return "".join(markdown_LOsummaries),markdown_LOsummaries

def save_markdown_document(consolidated_markdown, filename):
    with open(filename, 'w') as file:
        file.write(consolidated_markdown)

def save_to_csv_los(data, file_path):
    print("saving to csv")
    with open(file_path, 'w', newline='', encoding='utf-8') as file:
        fieldnames = ['id', 'summary']
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for idx, item in enumerate(data, start=1):  # Enumerate data to generate ids starting from 1
            writer.writerow({'id': idx, 'summary': item})
        print("Saved the csv to path ", file_path)

def create_los_embeddings_pinecone_main_block():

    openai.api_key = os.getenv("OPENAI_API_KEY")
    topic_names = [
        'Residual Income Valuation', 
        'Equity Valuation: Applications and Processes', 
        'Free Cash Flow Valuation'
    ]
    
    los_data = fetch_LO_data(topic_names)
    # print(los_data)
    all_summaries = []
    for idx,los in enumerate(los_data):
        print(los)
        print("\n", type(los))
        markdown_los_summaries, markdown_summaries_list = process_los_collection(los)
        print(len(markdown_summaries_list))
        all_summaries.extend(markdown_summaries_list)
        save_markdown_document(markdown_los_summaries, "./scripts/data/" + str(topic_names[idx] )+ 'LOS_Summary.md')

    embed_model = os.getenv('EMBEDDING_MODEL')
    print(len(all_summaries))
    save_to_csv_los(all_summaries, "./scripts/data/los_summary.csv")
    los_embeddings = generate_embeddings(all_summaries, embed_model, openai.api_key)

    vector_id = [str(i) for i in range(1, len(all_summaries)+1)]
    print( len(los_embeddings), len(los_embeddings[0]))

    pinecone_api_key = os.getenv("PINECONE_API_KEY_2")
    index_name = os.getenv("PINECONE_INDEX_NAME_2")
    # Create pinecone index

    retry = 15
    retryIndicator = True
    while retry>0 and retryIndicator :
        try :
            pine_index = create_pine_index(pinecone_api_key, index_name, len(los_embeddings[0]))
            retryIndicator = False
        except Exception as e: 
            print( 'error in create pine index retry for '+namespace + "   ---> " + str(e) )
            time.sleep(1)
            retry -=1
            print('error in' +  str(retry))

    # print(pine_index.describe_index_stats())
          
    # Upsert question vectors in los namespace 
    print("Uploading vectors to los namespace..")
    print(pinecone_api_key, index_name)


    vectors=list(zip(vector_id, los_embeddings))
    print(los_embeddings,)
    print(vector_id)
    namespace='los'
    upsert_retry(pine_index,vectors,namespace,retry=15)
    # print(pine_index.describe_index_stats())


    print("Embeddings stored successfully.")

#### Main Task End

##### TryE


dag = DAG(
    dag_id="sandbox",
    schedule="0 0 * * *",   # https://crontab.guru/
    start_date=days_ago(0),
    catchup=False,
    dagrun_timeout=timedelta(minutes=60),
    tags=["labs", "damg7245"],
)
    

with dag:
    start = BashOperator(
        task_id="start",
        bash_command='echo "Triggering airflow pipeline!!"'
    )

    create_los_embeddings_pinecone_main_block = PythonOperator(
        task_id='create_los_embeddings_pinecone_main_block',
        python_callable=create_los_embeddings_pinecone_main_block,
        provide_context=True,
        dag=dag,
    )
    
    parse_pdf = PythonOperator(
        task_id='parse_pdf',
        python_callable=parse_pdf,
        provide_context=True,
        dag=dag,
    )
    
    qna_main_block = PythonOperator(
        task_id='qna_main_block',
        python_callable=qna_main_block,
        provide_context=True,
        dag=dag,
    )
    
    save_to_pinecone_main_block = PythonOperator(
        task_id='save_to_pinecone_main_block',
        python_callable=save_to_pinecone_main_block,
        provide_context=True,
        dag=dag,
    )

    use_case_3_final_block = PythonOperator(
        task_id='use_case_3_final_block',
        python_callable=use_case_3_final_block,
        provide_context=True,
        dag=dag,
    )


# hello_world >> grobid_extraction >> push_extracted_files_to_s3 >> create_snowflake_schema
# hello_world >> create_los_embeddings_pinecone_main_block >> parse_pdf >> qna_main_block >> save_to_pinecone_main_block >> use_case_3_final_block
start >> create_los_embeddings_pinecone_main_block >> parse_pdf >> qna_main_block >> save_to_pinecone_main_block >> use_case_3_final_block
# start >> parse_pdf >> qna_main_block >> save_to_pinecone_main_block >> use_case_3_final_block
