import os
import snowflake.connector
from typing import List
from dotenv import load_dotenv
import csv
import boto3

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

# Example usage:
if __name__ == "__main__":
    utility = Utility()
    utility.setup_snowflake()

    local_path, s3_bucket_name, s3_folder, access_key, secret_key, region = Utility.envForS3()

# Upload only new text files or overwrite existing ones in the specified S3 folder
    Utility.upload_text_files_to_s3_folder(local_path, s3_bucket_name, s3_folder, access_key, secret_key, region)

    # utility.upload_text_files_to_s3_root(data_to_write)
