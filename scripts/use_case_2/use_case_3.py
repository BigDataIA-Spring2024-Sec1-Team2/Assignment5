import os
from dotenv import load_dotenv
import csv
import pandas as pd
from openai import OpenAI
from pinecone import Pinecone
from scipy.spatial import distance
import numpy as np

load_dotenv("./config/.env", override=True)

def get_question_bank(file_path):
    data = []
    with open(file_path, 'r') as file:
        csv_reader = csv.DictReader(file)
        for row in csv_reader:
            data.append(dict(row))
    df = pd.DataFrame(data)
    return df

def query_article(ques, ques_mapped, answer_mapped, namespace, client,index, top_k=3):
    '''Queries an article using its title in the specified
     namespace and prints results.'''
    
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL")

    # Create vector embeddings based on the title column
    embedded_query = client.embeddings.create(input=ques,model=EMBEDDING_MODEL,).data[0].embedding

    # Query namespace passed as parameter using title vector
    query_result = index.query(vector=embedded_query, 
                                      namespace=namespace, 
                                      top_k=top_k)

    # Print query results 
    # print(f'\nMost similar results to {ques} in "{namespace}" namespace:\n')
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
    
    counter = 0
    # for k,v in df.iterrows():
    #     counter += 1
    #     print(f'(score = {v.score}) \nquestion={v.question}\n answer={v.answer} ')
    
    # print('\n')

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
) -> tuple[list[str], list[float]]:
    """Returns a list of strings and relatednesses, sorted from most related to least."""
    client = OpenAI(api_key='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',)
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

def save_to_csv(data, file_path):
    print("saving to csv")
    with open(file_path, 'w', newline='', encoding='utf-8') as file:
        fieldnames = ['id', 'question', 'true_ans', 'generated_ans', 'relativity']  # Added 'id' to the fieldnames
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for idx, item in enumerate(data, start=1):  # Enumerate data to generate ids starting from 1
            writer.writerow({'id': idx, 'question': item['question'], 'true_ans': item['true_ans']
                             , 'generated_ans': item['generated_ans'], 'relativity': item['relativity']})
        print("Saved the csv to path ", file_path)


def main():
    folder_path = os.getenv("DIR_CFA_WEB")
    file_path = folder_path + 'set_b.csv'
    openai_api_key = os.getenv("OPENAI_API_KEY")
    api_key = os.getenv("PINECONE_API_KEY")
    index_name = os.getenv("PINECONE_INDEX_NAME")
    
    # 1. get set b questions
    set_b = get_question_bank(file_path)

    # First we'll create dictionaries mapping vector IDs to their outputs so we can retrieve the text for our search results
    ques_mapped = dict(zip(set_b.id,set_b.question))
    answer_mapped = dict(zip(set_b.id,set_b.answer))
    print(len(ques_mapped), len(answer_mapped))

    
    openai_client = OpenAI(api_key=openai_api_key,)

    # Get pinecone index
    pinecone = Pinecone(api_key=api_key)
    pine_index = pinecone.Index(name=index_name)
    namespace = 'questions'
    final_df = []

    # 2. find 3 questions in Set A that are most similar
    for idx, row in set_b.iterrows():
        print("Processing question ", idx)
        # print("question = ", row['question'])
        df = query_article(row['question'], ques_mapped, answer_mapped, namespace, openai_client, pine_index)

        # 3. pass the answers of these 3 questions to GPT-4 along with the question
        context = ''.join(df.answer.values)
        # print("context = ", context)
        response = get_answer(openai_client,row['question'], context)
        # print("response = ", response)

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
        # print(query1, query2, relatedness)
        # break
    save_to_csv(final_df, folder_path + 'report.csv')


if __name__ == "__main__":
    main()

