from bs4 import BeautifulSoup
from dotenv import load_dotenv
from grobid_client_python.grobid_client.grobid_client import GrobidClient
import boto3
import csv
import os
from pydantic import TypeAdapter, ValidationError
from typing import List
import sys
current_directory = os.getcwd()
sys.path.append(current_directory)
sys.path.append('../')
from utility import Utility
sys.path.append(current_directory)
from itertools import count
from pydantic.dataclasses import dataclass
from pydantic import Field, validator, HttpUrl
import snowflake.connector
import warnings
warnings.filterwarnings("ignore")
from sqlalchemy import create_engine
current_directory = os.getcwd()
sys.path.append(current_directory)

@dataclass
class ContenPDF:
    # id_generator: itertools.count(1) = itertools.count(1)
    id: int = Field(default_factory=count(1).__next__)
    topic_id: int = Field(gt=0)
    heading: str = ""
    content: str = ""


@dataclass
class MetadataPDF:
    pdf_id: int = Field(default_factory=count(1).__next__)
    name: str = Field(min_length=1)
    level: str = Field(min_length=7)
    year: int = Field(min=1900, max=2099)
    total_topics: int = Field(ge=0)
    topics: list = Field(List[str])
    total_sub_topics: int = Field(ge=0)
    sub_topics: list = Field(List[str])
    content_length: int = Field(ge=1)
    s3_filepath: HttpUrl = ""# Validates that the link is a proper URL

    # Validation for the 'level' field to ensure it's one of the predefined levels
    @validator('level')
    def level_must_be_valid(cls, value):
        valid_levels = ['Level I', 'Level II', 'Level III']
        if value not in valid_levels:
            raise ValueError(f"Invalid level. Valid levels are: {', '.join(valid_levels)}")
        return value


@dataclass
class TopicPDF:
    id: int = Field(default_factory=count(1).__next__)
    level: str = Field(min_length=7)
    topic: str = Field(min_length=1)


def loadenv():
    user = os.getenv("SNOWFLAKE_USER")
    password = os.getenv("SNOWFLAKE_PASSWORD")
    db = os.getenv("SNOWFLAKE_DATABASE")
    account_identifier = os.getenv("SNOWFLAKE_ACCOUNT_IDENTIFIER")
    wh = os.getenv("SNOWFLAKE_WAREHOUSE")
    return user,password ,db ,account_identifier,wh

def connectionToSnow(path='../config/.env',connection_test=False):
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

def execute(connection,query):
    try:
        results = connection.execute(query)
    except Exception as e:
        print("error-->",e)
    finally:
        print("Done")
def setup(connection):
    print('.........................SETTING UP DATABASES, WAREHOUSE, SCHEMAS')
    query = "CREATE OR REPLACE WAREHOUSE {};".format(os.getenv("SNOWFLAKE_USER"))
    execute(connection,query)

    query ="CREATE OR REPLACE DATABASE {};".format(os.getenv("SNOWFLAKE_DBT_DEV_DB"))
    execute(connection,query)
    
    query = "CREATE OR REPLACE DATABASE {};".format(os.getenv("SNOWFLAKE_DBT_PROD_DB"))
    execute(connection,query)

    query = "CREATE OR REPLACE SCHEMA  {}.{};".format(os.getenv("SNOWFLAKE_DBT_DEV_DB"), os.getenv("SNOWFLAKE_DBT_SCHEMA"))
    execute(connection,query)

    query = "CREATE OR REPLACE SCHEMA {}.{};".format(os.getenv("SNOWFLAKE_DBT_PROD_DB"), os.getenv("SNOWFLAKE_DBT_SCHEMA"))
    execute(connection,query)


def createtables(connection,db,topic,content,metadata,urldata):
    schema = os.getenv("SNOWFLAKE_DBT_SCHEMA")

    print("................CREATING DATATABLE IN SNOWFLAKE ")
    topicTable = """
    create or replace TABLE {}.{}.{} 
    (ID NUMBER(38,0),
    LEVEL VARCHAR(16777216),
    TOPIC VARCHAR(16777216));""".format(db,schema,topic)


    execute(connection,topicTable)

    contentTable = """
    create or replace TABLE {}.{}.{} (
	ID NUMBER(38,0),
    TOPIC_ID NUMBER(38,0),
    HEADING VARCHAR(16777216),
	CONTENT VARCHAR(16777216)
	
    );""".format(db,schema,content)

    execute(connection,contentTable)
    metadataTable = """
    create or replace TABLE {}.{}.{} (
	PDF_ID NUMBER(38,0),
	NAME VARCHAR(16777216),
	LEVEL VARCHAR(16777216),
	YEAR NUMBER(38,0),
	TOTAL_TOPICS NUMBER(38,0),
	TOPICS VARCHAR(16777216),
	TOTAL_SUB_TOPICS NUMBER(38,0),
	SUB_TOPICS VARCHAR(16777216),
	CONTENT_LENGTH NUMBER(38,0),
	S3_FILEPATH VARCHAR(16777216)
    );""".format(db,schema,metadata)

    execute(connection,metadataTable)
    
    urldata = """create or replace TABLE {}.{}.{} (
	PDFLINK VARCHAR(16777216),
	PARENTTOPIC VARCHAR(16777216),
	YEAR NUMBER(38,0),
	LEVEL VARCHAR(16777216),
	INTRODUCTION VARCHAR(16777216),
	LEARNINGOUTCOME VARCHAR(16777216),
	SUMMARY VARCHAR(16777216),
	CATEGORIES VARCHAR(16777216),
	TOPICNAME VARCHAR(16777216),
	URL VARCHAR(16777216)
    );""".format(db,schema,urldata)
    
    execute(connection,urldata)



def loadtable_s3(connection, db,urldata,metadata,content,topic):
    print("................LOADING DATA FROM SNOWFLAKE TO S3")
    schema = os.getenv("SNOWFLAKE_DBT_SCHEMA")
    aws_access = os.getenv("S3_ACCESS_KEY")
    aws_secret = os.getenv("S3_SECRET_KEY")
    
    urldataload = """copy into {}.{}.{}
    from 's3://cfa-pdfs/clean_csv_data/FinanceHub.csv'
    CREDENTIALS = (
        AWS_KEY_ID = '{}',
        AWS_SECRET_KEY ='{}'
    )
    file_format = (
        type = 'CSV'
        field_delimiter = ','
        skip_header = 1,
        FIELD_OPTIONALLY_ENCLOSED_BY='"'
        )
    ON_ERROR = continue; """.format(db,schema,urldata,aws_access,aws_secret)

    # print(urldataload)
    execute(connection,urldataload)

    metadataload = """copy into {}.{}.{}
    from 's3://cfa-pdfs/clean_csv_data/MetadataPDF.csv'
    CREDENTIALS = (
        AWS_KEY_ID = '{}',
        AWS_SECRET_KEY = '{}'
    )
    file_format = (
        type = 'CSV'
        field_delimiter = ','
        skip_header = 1,
        FIELD_OPTIONALLY_ENCLOSED_BY='"'
        )
    ON_ERROR = continue; """.format(db,schema,metadata,aws_access,aws_secret)
    # print(metadataload)
    execute(connection,metadataload)
   
    contentload = """
    copy into {}.{}.{}
    from 's3://cfa-pdfs/clean_csv_data/ContentPDF.csv'
    CREDENTIALS = (
        AWS_KEY_ID = '{}',
        AWS_SECRET_KEY = '{}'
    )
    file_format = (
        type = 'CSV'
        field_delimiter = ','
        skip_header = 1,
        FIELD_OPTIONALLY_ENCLOSED_BY='"'
        )
    ON_ERROR = continue; """.format(db,schema,content,aws_access,aws_secret)
    # print(contentload)
    execute(connection,contentload)

    topicsload = """copy into {}.{}.{}
    from 's3://cfa-pdfs/clean_csv_data/TopicPDF.csv'
    CREDENTIALS = (
        AWS_KEY_ID = '{}',
        AWS_SECRET_KEY = '{}'
        )
    file_format = (
        type = 'CSV'
        field_delimiter = ','
        skip_header = 1,
        FIELD_OPTIONALLY_ENCLOSED_BY='"'
        )
    ON_ERROR = continue;""".format(db,schema,topic,aws_access,aws_secret)
    # print(topicsload)
    execute(connection,topicsload)


class Utility:

    def __init__(self) -> None:
        # read env file and set all variables
        # Example: Assuming you have environment variables in a file named '.env'
        # You can use python-dotenv to load them.
        load_dotenv()

        self.snowflake_account = os.getenv('SNOWFLAKE_ACCOUNT')
        self.snowflake_user = os.getenv('SNOWFLAKE_USER')
        self.snowflake_password = os.getenv('SNOWFLAKE_PASSWORD')
        self.snowflake_database = os.getenv('SNOWFLAKE_DATABASE')
        self.snowflake_schema = os.getenv('SNOWFLAKE_SCHEMA')
    
    def setup_snowflake(self):
        # create snowflake data warehouse
        connection = snowflake.connector.connect(
            user=self.snowflake_user,
            password=self.snowflake_password,
            account=self.snowflake_account,
            warehouse='YOUR_WAREHOUSE',
            database=self.snowflake_database,
            schema=self.snowflake_schema
        )

        try:
            cursor = connection.cursor()

            # create topic table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS topic (
                    topicId INT AUTOINCREMENT PRIMARY KEY,
                    topicName STRING,
                    pdfId INT
                )
            """)

            # create content table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS content (
                    contentId INT AUTOINCREMENT PRIMARY KEY,
                    heading STRING,
                    topicId INT,
                    content STRING
                )
            """)

            # create metadata table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS metadata (
                    pdfId INT AUTOINCREMENT PRIMARY KEY,
                    author STRING,
                    lang STRING,
                    s3FilePath STRING,
                    fileSize INT
                )
            """)

            # create URL table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS url (
                    pdfLink STRING,
                    parentTopic STRING,
                    year INT,
                    level INT,
                    introduction STRING,
                    learningOutcome STRING,
                    summary STRING,
                    categories STRING,
                    topicName STRING,
                    url STRING
                )
            """)
        finally:
            connection.close()
    @staticmethod
    def upload_text_files_to_s3_root(local_path):
    # Create an S3 client
        def loadenv():
            s3_bucket_name = os.getenv("s3_bucket_name")
            s3_pypdf = os.getenv("s3_pypdf")
            s3_grobid = os.getenv("s3_grobid")
            access_key = os.getenv("access_key")
            secret_key = os.getenv("secret_key")
            region = os.getenv("region")
            return "s3://"+ s3_bucket_name, s3_pypdf, s3_grobid, access_key, secret_key, region
        s3_bucket_name, s3_pypdf, s3_grobid, access_key, secret_key, region = loadenv()
        s3 = boto3.client('s3', aws_access_key_id=access_key, aws_secret_access_key=secret_key, region_name = region)

        # List all files in the local path
        local_files = os.listdir(local_path)

        for file_name in local_files:
            if file_name == '224_links.txt':  # Upload only text files, adjust the condition based on your file types
                local_file_path = os.path.join(local_path, file_name)

                # Specify the S3 key (file path within the bucket)
                s3_key = file_name  # This will upload directly to the root of the S3 bucket

                # Upload the file to S3
                try:
                    s3.upload_file(local_file_path, s3_bucket_name, s3_key)
                    print(f"Successfully uploaded {file_name} to S3 bucket {s3_bucket_name}")
                except Exception as e:
                    print(f"Error uploading {file_name} to S3: {e}")
            elif str(file_name).endswith('.csv'):  # Upload only text files, adjust the condition based on your file types
                print(file_name)
                local_file_path = os.path.join(local_path, file_name)

                # Specify the S3 key (file path within the bucket)
                s3_key = file_name  # This will upload directly to the root of the S3 bucket

                # Upload the file to S3
                try:
                    s3.upload_file(local_file_path, s3_bucket_name, s3_key)
                    print(f"Successfully uploaded {file_name} to S3 bucket {s3_bucket_name}")
                except Exception as e:
                    print(f"Error uploading {file_name} to S3: {e}")
    @staticmethod
    def store_to_csv(object_list, file_dir, file_name):
    # Ensure the list is not empty
        if object_list:
            # Get attribute names from the first object
            fieldnames = list(vars(object_list[0]).keys())
            # fieldnames = [field.name for field in fields(Person)]

            # Check if the directory exists, create it if not
            if not os.path.exists(file_dir):
                print("Creating directory to store csv")
                os.makedirs(file_dir)

            csv_file_path = os.path.join(file_dir, file_name)

            with open(csv_file_path, mode='w', newline='',encoding="utf-8") as csv_file:
                writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
                writer.writeheader()

                for object in object_list:
                    if object:
                        writer.writerow({field: getattr(object, field) for field in fieldnames})

            print(f'Data has been written to {csv_file_path}.')
        else:
            print("List is empty, nothing to write to CSV.")

    def s3_read(self):
        # Implementation to read from S3
        pass

    def snowflake_write(self, data: List[dict]):
        connection = snowflake.connector.connect(
            user=self.snowflake_user,
            password=self.snowflake_password,
            account=self.snowflake_account,
            warehouse='YOUR_WAREHOUSE',
            database=self.snowflake_database,
            schema=self.snowflake_schema
        )

        try:
            cursor = connection.cursor()

            # Example: Inserting data into the 'metadata' table
            for row in data:
                cursor.execute("""
                    INSERT INTO metadata (author, lang, s3FilePath, fileSize)
                    VALUES (%s, %s, %s, %s)
                """, (row['author'], row['lang'], row['s3FilePath'], row['fileSize']))

            connection.commit()

        finally:
            connection.close()

   
    @staticmethod
    def envForS3():
        load_dotenv('../config/.env',override=True)
        local_path = os.getenv("LOCAL_PATH")
        s3_bucket_name = os.getenv("S3_BUCKET_NAME")
        s3_folder = os.getenv("S3_FOLDER_NAME")
        access_key = os.getenv("S3_ACCESS_KEY")
        secret_key = os.getenv("S3_SECRET_KEY")
        region = os.getenv("S3_REGION")
        return local_path,s3_bucket_name,s3_folder,access_key,secret_key,region
    
    @staticmethod
    def upload_text_files_to_s3_folder(local_path, bucket_name, s3_folder, access_key, secret_key, region):
        # Create an S3 client
        s3 = boto3.client('s3', aws_access_key_id=access_key, aws_secret_access_key=secret_key, region_name = region)

        # Iterate through all files in the local directory
        for filename in os.listdir(local_path):
            if filename.endswith(".csv"):
                local_file_path = os.path.join(local_path, filename)
                s3_object_key = f"{s3_folder}/{filename}"

                # Check if the file already exists in S3
                try:
                    s3.head_object(Bucket=bucket_name, Key=s3_object_key)
                    print(f"File {filename} already exists in S3. Overwriting...")
                except Exception as e:
                    # If the file doesn't exist, upload it
                    try:
                        s3.upload_file(local_file_path, bucket_name, s3_object_key)
                        print(f"File {filename} uploaded successfully to S3: s3://{bucket_name}/{s3_object_key}")
                    except Exception as upload_error:
                        print(f"Error uploading file {filename} to S3: {upload_error}")
            elif filename == "metadata_output.csv":
                local_file_path = os.path.join(local_path, filename)
                s3_object_key = f"{s3_folder}/{filename}"

                # Check if the file already exists in S3
                try:
                    s3.head_object(Bucket=bucket_name, Key=s3_object_key)
                    print(f"File {filename} already exists in S3. Overwriting...")
                except Exception as e:
                    # If the file doesn't exist, upload it
                    try:
                        s3.upload_file(local_file_path, bucket_name, s3_object_key)
                        print(f"File {filename} uploaded successfully to S3: s3://{bucket_name}/{s3_object_key}")
                    except Exception as upload_error:
                        print(f"Error uploading file {filename} to S3: {upload_error}")

#########################################################################################
# Utility Functions Start
#########################################################################################


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

#########################################################################################
# Utility Functions End
#########################################################################################




def main():

    
    ## GROBID
    print("--------------------------- PART 2: GROBID EXTRACTION ---------------------------")

    def grobid_extraction():

        load_dotenv('./config/.env',override=True)
        output_dir = os.getenv("OUTPUT_DIR_PATH") # Store the extracted txt files
        s3_bucket_name = os.getenv("S3_BUCKET_NAME")
        access_key = os.getenv("S3_ACCESS_KEY")
        secret_key = os.getenv("S3_SECRET_KEY")
        region = os.getenv("S3_REGION")

        if not os.path.exists("output_data/"):
            print("Creating directory to store output data")
            os.makedirs("output_data/")
        
        if not os.path.exists("data/"):
            print("Creating directory to store raw pdfs")
            os.makedirs("data/")

        # download the pdf files from s3
        s3_paths = download_files_from_s3("data/", "raw_pdfs", access_key, secret_key, region, s3_bucket_name)

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

        metadata_list,topic_list,content_list = parse_all_xml(s3_paths, output_dir)

        # store the objects to csv
        csv_output_dir = f'{output_dir}cleaned_csv/'
        Utility.store_to_csv(metadata_list, csv_output_dir, "MetadataPDF.csv")

        # flatten the lists before storing it to csv
        topic_flattened = [topic for row in topic_list for topic in row]
        Utility.store_to_csv(topic_flattened, csv_output_dir, "TopicPDF.csv")

        content_flattened = [content for row in content_list for content in row]
        Utility.store_to_csv(content_flattened, csv_output_dir, "ContentPDF.csv")

    
    print("--------------------------- PART 3: PUSHING CLEANED CSV FILES TO S3 ---------------------------")
    def push_extracted_files_to_s3():
        utility = Utility()
        utility.setup_snowflake()
        local_path, s3_bucket_name, s3_folder, access_key, secret_key, region = Utility.envForS3()
        print(local_path, s3_bucket_name, s3_folder, access_key, secret_key, region)

        # Upload only new text files or overwrite existing ones in the specified S3 folder
        Utility.upload_text_files_to_s3_folder(local_path, s3_bucket_name, s3_folder, access_key, secret_key, region)


    print("--------------------------- PART 4: CREATING SNOWFLAKE SCHEMA ---------------------------")
    print("\n")
    print("........................... Testing Snnowflake connection -------------------------------")
    def create_snowflake_schema():

        connectionToSnow(connection_test=False)

        print(".............Starting Snnowflake connection -------------------------------------------")
        connection = connectionToSnow()
        setup(connection)

        db_prod = os.getenv("SNOWFLAKE_DBT_PROD_DB")
        db_dev = os.getenv("SNOWFLAKE_DBT_DEV_DB")
        topic_table =  os.getenv("SNOWFLAKE_DBT_TOPIC_TABLE")
        content_table = os.getenv("SNOWFLAKE_DBT_CONTENT_TABLE")
        metadata_table = os.getenv("SNOWFLAKE_DBT_META_TABLE")
        urldata_table = os.getenv("SNOWFLAKE_DBT_URLDATA_TABLE")


        print(".............Creating Snnowflake Tables ---------------------------------------------------")

        createtables(connection,db_prod, topic_table, content_table, metadata_table, urldata_table)
        createtables(connection,db_dev, topic_table, content_table, metadata_table, urldata_table)

        loadtable_s3(connection, db_dev,urldata_table,metadata_table,content_table,topic_table)
        loadtable_s3(connection, db_prod,urldata_table,metadata_table,content_table,topic_table)


        connection.close()
        sys.exit(0)