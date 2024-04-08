import os
from dotenv import load_dotenv
import snowflake.connector
from snowflake.connector import DictCursor

# Load environment variables from .env file
load_dotenv("config/part1.env")

# Function to fetch summary data based on topic names
def fetch_summary_data(topic_names):
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
                SELECT Summary
                FROM {os.getenv('SNOWFLAKE_DATABASE')}.{os.getenv('SNOWFLAKE_SCHEMA')}.URLDATA
                WHERE TopicName IN ({formatted_topics});
            """
            
            # Execute the query
            cur.execute(query)
            
            # Fetch all rows
            rows = cur.fetchall()
            
            return rows

# Example usage
if __name__ == "__main__":
    topic_names = [
        'Residual Income Valuation', 
        'Equity Valuation: Applications and Processes', 
        'Free Cash Flow Valuation'
    ]
    
    summaries = fetch_summary_data(topic_names)
    for summary in summaries:
        print(summary)
