import os
import csv
from openai import OpenAI
from dotenv import load_dotenv
import re
import sys
import snowflake_setup 

load_dotenv('config/.env',override=True)

current_directory = os.getcwd()
sys.path.append(current_directory)

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
    questions = response.split("Answer:")
    res = []
    ques = {}
    ques["question"] = questions[0].strip()
    next_ques = re.split(r"(?:\d+\.|Question(?:\s+\d+)?:)", questions[1])
    ques["answer"] = next_ques[0].strip()
    res.append(ques)
    print("\n")
    print(ques)
    for i in range(2,len(questions)):
        ques = {}
        ques["question"] = next_ques[1].strip()
        next_ques = re.split(r"(?:\d+\.|Question(?:\s+\d+)?:)", questions[i])
        ques["answer"] = next_ques[0].strip()
        res.append(ques)
        print("\n")
        print(ques)
    print("Parsed ", len(res) ) 
    return res

import csv

def save_to_csv(data, file_path):
    print("saving to csv")
    with open(file_path, 'w', newline='', encoding='utf-8') as file:
        fieldnames = ['id', 'question', 'answer']  # Added 'id' to the fieldnames
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for idx, item in enumerate(data, start=1):  # Enumerate data to generate ids starting from 1
            writer.writerow({'id': idx, 'question': item['question'], 'answer': item['answer']})
        print("Saved the csv to path ", file_path)


def main(knowledge_base):

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
    save_to_csv(ques_ans_set_a, folder_path+"set_a.csv")

    ques_ans_set_b = []
    for topic in knowledge_base:
        print("Processing Set B")
        ques_ans_set_b.extend(generate_set_a(client, topic, context))
        print(len(ques_ans_set_b))
    save_to_csv(ques_ans_set_b, folder_path+"set_b.csv")
  

if __name__ == "__main__":
    knowledge_base = snowflake_setup.main()
    main(knowledge_base)
