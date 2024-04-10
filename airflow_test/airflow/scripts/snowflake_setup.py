import warnings
warnings.filterwarnings("ignore")

from sqlalchemy import Boolean, Column, Integer, String

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from dotenv import load_dotenv
import os
from utility import Utility
import sys

current_directory = os.getcwd()
sys.path.append(current_directory)

load_dotenv('config/.env',override=True)


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

   



    






        

if __name__ == '__main__':
    connectionToSnow(connection_test=False)
    connection = connectionToSnow()
    setup(connection)

    db_prod = os.getenv("SNOWFLAKE_DBT_PROD_DB")
    db_dev = os.getenv("SNOWFLAKE_DBT_DEV_DB")
    topic_table =  os.getenv("SNOWFLAKE_DBT_TOPIC_TABLE")
    content_table = os.getenv("SNOWFLAKE_DBT_CONTENT_TABLE")
    metadata_table = os.getenv("SNOWFLAKE_DBT_META_TABLE")
    urldata_table = os.getenv("SNOWFLAKE_DBT_URLDATA_TABLE")

    # print(metadata_table)
    
    createtables(connection,db_prod, topic_table, content_table, metadata_table, urldata_table)
    createtables(connection,db_dev, topic_table, content_table, metadata_table, urldata_table)
    print("loading data...")
    loadtable_s3(connection, db_dev,urldata_table,metadata_table,content_table,topic_table)
    loadtable_s3(connection, db_prod,urldata_table,metadata_table,content_table,topic_table)







