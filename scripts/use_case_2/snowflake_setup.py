import warnings
warnings.filterwarnings("ignore")

from sqlalchemy import Boolean, Column, Integer, String

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from dotenv import load_dotenv
import os
import sys
import pandas as pd

current_directory = os.getcwd()
sys.path.append(current_directory)

load_dotenv('config/.env',override=True)


def loadenv():
    user = os.getenv("SNOWFLAKE_USER")
    password = os.getenv("SNOWFLAKE_PASSWORD")
    db = os.getenv("SNOWFLAKE_DATABASE")
    account_identifier = os.getenv("SNOWFLAKE_ACCOUNT")
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
        

def main():
    try:
        connection = connectionToSnow()
        return read_data(connection)
    except Exception as e:
        print("error", e)
    finally:
        connection.close()

if __name__ == '__main__':
    main()








