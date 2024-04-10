import os
import sys
from dotenv import load_dotenv
from grobid_client_python.grobid_client.grobid_client import GrobidClient
from bs4 import BeautifulSoup
from pydantic import TypeAdapter, ValidationError
import boto3

## config
print("PYTHONPATH = ",sys.path)
print("Current working directory = ",os.getcwd())
print("Adding current working directory to PYTHONPATH")
sys.path.append(os.getcwd())


from models.content_pdf import ContenPDF
from models.topic_pdf import TopicPDF
from models.metadata import MetadataPDF
from utility import Utility



def load_parsing_env():
    load_dotenv('./config/.env',override=True)

    output_dir = os.getenv("OUTPUT_DIR_PATH") # Store the extracted txt files
    s3_bucket_name = os.getenv("S3_BUCKET_NAME")
    access_key = os.getenv("S3_ACCESS_KEY")
    secret_key = os.getenv("S3_SECRET_KEY")
    region = os.getenv("S3_REGION")
    
    return output_dir, s3_bucket_name, access_key, secret_key, region

# Function to extract grobid xml using grobid client
def extract_grobid(output_dir):
    print("Changing current working directory to:")
    os.chdir("grobid_client_python")
    print(os.getcwd())
    output_path = f'../{output_dir}/grobid'
    try:
        client = GrobidClient(config_path="./config.json")
        client.process("processFulltextDocument", "../data",
                    output=output_path, consolidate_citations=True, tei_coordinates=True, force=True)
        print("Done extracting xml files from GROBID")
        
    except Exception as e:
        print("Failed to extract pdf using grobid with error:")
        print(str(e))
    finally:
        os.chdir("../")
        print("Changing current working directory back to:")
        print(os.getcwd())


# function to parse individual grobid xml and create ContentPDF and TopicPDF objects
def parse_xml_content(level, xml_file_path):

    content_list = []
    topic_list =[]
    cont = None

    title_topic = "Quantitative Methods"
    if level[-1] == 3 : title_topic = "Economics"
    levell = 'Level I' if "1" in level else 'Level II' if "2" in level else 'Level III'
    
    topic = TopicPDF(level=levell,topic=title_topic )
    topic_model = TypeAdapter(TopicPDF).validate_python(topic)
    topic_list.append(topic_model)

    with open(xml_file_path, 'r') as tei:
        soup = BeautifulSoup(tei, 'xml')
        # print(soup)
    if not soup:
        print("Some error occurred")
        return
    # Calculate the length of the content excluding tags
    content_length = len(soup.get_text())

    # Find all 'div' elements
    divs = soup.find_all('div', {'xmlns': 'http://www.tei-c.org/ns/1.0'})

    
    # Iterate through each 'div' element
    for div in divs:
        if div.head is None:
            # append it to previous content
            if cont:
                cont.content += div.text
            else:
                print("Skipping this content : ")
                print(div.text)
            continue 
        # Extract the heading from 'head' element
        heading = div.head.text
        if heading == "LEARNING OUTCOMES":
            #skip as there is no content
            continue
        
        # Extract content from 'p' elements
        content = ' '.join(p.text for p in div.find_all('p'))
        try:
            if not content:
                # if there no content, then it is a topic
                topic = TopicPDF(level=levell, topic=heading)

                topic_model = TypeAdapter(TopicPDF).validate_python(topic)
                topic_list.append(topic_model)
                continue
            # add heading and content to the list
            cont = ContenPDF(topic_id=topic.id, heading=heading, content=content)
            # validating the dataclass 
            content_model = TypeAdapter(ContenPDF).validate_python(cont)
            content_list.append(content_model)
        except ValidationError as e:
            print("VALIDATION ERROR OCCURRED")
            print(e)
            print("Skipping this content : ")
            print(div.text)
            continue
    
    return topic_list, content_list, content_length

# function to parse all xml files in the local directory and create MetadataPDF class
def parse_all_xml(s3_paths, output_dir):
    # Iterate through all PDF files in the directory
    grobid_output_dir = "../"+output_dir+"grobid/"
    topic_list,content_list = [], []
    metadata_list = []
    for filename in os.listdir(grobid_output_dir):
        if filename.endswith(".xml"):
            xml_file_path = os.path.join(grobid_output_dir, filename)
            print("Parsing xml file ",filename, " saved at path ", xml_file_path)
            
            year = filename.split("-")[0]
            level = filename.split("-")[1]

            topics, contents, content_length = parse_xml_content(level, xml_file_path)
            # metadata
            # 2024-l1-topics-combined-2.grobid.tei.xml
            name = filename.split(".")[0]
            levell = 'Level I' if "1" in level else 'Level II' if "2" in level else 'Level III'
            total_topics = len(topics)
            total_sub_topics = len(contents)
            
            topic_names = [top.topic for top in topics]
            sub_topics_names = [st.heading for st in contents]
            s3_path = [p for p in s3_paths if level in p]

            metadata = MetadataPDF(name=name, level=levell, year=year, total_topics=total_topics,
                                   topics=topic_names, total_sub_topics=total_sub_topics, 
                                   sub_topics=sub_topics_names,
                                   content_length=content_length, s3_filepath=s3_path[0])
            
            metadata_model = TypeAdapter(MetadataPDF).validate_python(metadata)            
            metadata_list.append(metadata_model)
            topic_list.append(topics)
            content_list.append(contents)

    return metadata_list, topic_list, content_list

def download_files_from_s3(local_folder, s3_folder, access_key, secret_key, region, s3_bucket_name):
    s3 = boto3.client('s3', aws_access_key_id=access_key, aws_secret_access_key=secret_key, region_name = region)

    # List objects in the specified S3 folder
    response = s3.list_objects_v2(Bucket=s3_bucket_name, Prefix=s3_folder)
    # print(response)
    file_paths = []

    # Download each file to the local directory
    for obj in response.get('Contents')[1:]:
        key = obj['Key']
        local_file_path = os.path.join(local_folder, os.path.basename(key))

        s3.download_file(s3_bucket_name, key, local_file_path)
        print(f"Downloaded: {key} to {local_file_path}")
        path = f"https://{s3_bucket_name}.s3.amazonaws.com/{key}"
        file_paths.append(path)

    print(file_paths)
    return file_paths


# driver function
def perform_grobid_extraction(): 

    # load env
    output_dir, s3_bucket_name, access_key, secret_key, region = load_parsing_env() 

    if not os.path.exists("output_data/"):
        print("Creating directory to store output data")
        os.makedirs("output_data/")
    
    if not os.path.exists("data/"):
        print("Creating directory to store raw pdfs")
        os.makedirs("data/")

    # download the pdf files from s3
    s3_paths = download_files_from_s3("data/", "raw_pdfs", access_key, secret_key, region, s3_bucket_name)

    # extract grobid xml from PDF
    extract_grobid(output_dir)

    # parse the xmls and validate objs using pydantic
    metadata_list,topic_list,content_list = parse_all_xml(s3_paths, output_dir)

    # store the objects to csv
    csv_output_dir = f'{output_dir}cleaned_csv/'
    Utility.store_to_csv(metadata_list, csv_output_dir, "MetadataPDF.csv")

    # flatten the lists before storing it to csv
    topic_flattened = [topic for row in topic_list for topic in row]
    Utility.store_to_csv(topic_flattened, csv_output_dir, "TopicPDF.csv")

    content_flattened = [content for row in content_list for content in row]
    Utility.store_to_csv(content_flattened, csv_output_dir, "ContentPDF.csv")




    










