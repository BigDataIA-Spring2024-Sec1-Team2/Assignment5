from selenium import webdriver
from bs4 import BeautifulSoup
from dotenv import load_dotenv

import concurrent.futures
from tqdm import tqdm 

import requests
import time
import csv
import os
import re

from typing import List

import sys
current_directory = os.getcwd()
sys.path.append(current_directory)


from utility import Utility
from models.urlClass import UrlClass


def scrape_coveo_links(url):
    # Set up the WebDriver with the command line flag for Edge
    edge_options = webdriver.EdgeOptions()
    edge_options.add_argument('--enable-chrome-browser-cloud-management')

    driver = webdriver.Edge(options=edge_options)
    urlList = []

    try:
        # Make a request using Selenium
        driver.get(url)

        # Wait for the dynamic content to load (you may need to adjust the sleep duration)
        time.sleep(5)

        # Get the page source after dynamic content has loaded
        page_source = driver.page_source

        # Parse the HTML content of the page
        soup = BeautifulSoup(page_source, 'html.parser')

        # Find all the links with class 'coveo'
        coveo_links = soup.find_all('a', class_='CoveoResultLink')
        
        # Extract and write the href attribute of each coveo link to a file
        for link in coveo_links:
            href = link.get('href')
            if href:
                urlList.append(href)


        # Print the total number of coveo links
        print(f"Total number of Coveo class links: {len(coveo_links)}")
        print("Coveo class links saved to '224_links.txt'")

    finally:
        # Close the WebDriver in a 'finally' block to ensure it is closed even if an exception occurs

        driver.quit()
    return urlList

# Function to clean up text by removing extra spaces, tabs, and newlines
def clean_text(text):
    # Remove extra spaces, tabs, and newlines using regular expressions
    cleaned_text = re.sub(r'\s+', ' ', text)
    return cleaned_text.strip()

# Function to find and print section based on its title
def print_section(soup,title):
    # Find the section by its title
    section = soup.find('h2', text=title)
    try:
        if section:
            content = []
            next_node = section.find_next_sibling()
            while next_node and next_node.name != 'h2':
                text = next_node.get_text(" ", strip=True)
                cleaned_text = clean_text(text)
                if cleaned_text:  # Only add non-empty strings
                    content.append(cleaned_text)
                next_node = next_node.find_next_sibling()
            return "\n".join(content)
        else:
            return f"{title} section is missing."
    except:
        return f"{title} section is missing."

    
# URL of the webpage to scrape
def getContent(soup):
    # Parse the content of the page with BeautifulSoup\
    # Titles of the sections to extract
    try:
        text_final = []
        titles = ['Introduction', 'Learning Outcomes', 'Summary']
        # Loop through the titles and print each section
        for title in titles:
            text_final.append(print_section(soup,title))
        return text_final[0], text_final[1],text_final[2]
    except:
        return "","",""

def extract_information(url):
    response = requests.get(url)
    if response.status_code == 200:
        # Parse the content of the page with BeautifulSoup
        soup = BeautifulSoup(response.content, 'html.parser')
        # Parse the content of the page with BeautifulSoup
        # Initialize variables to store extracted information
        pdf_link = "https://missingpdf.com"
        topic_name = None
        year = None
        level = None
        categories = []
        text_final = None
        parent_topic = None

        # failed one to the new csv
        # passed to the original csv 

        # Extract the PDF download link
        ## PDF link extraction
        for a_tag in soup.find_all('a'):
            if 'Download the full reading (PDF)' in a_tag.text:
                pdf_link = "https://cfainstitute.org" + a_tag.get('href')
                break

        # Extract the topic name
        title_tag = soup.find('title')
        if title_tag:
            topic_name = title_tag.text

        # Extract the year and level from the content utility section
        content_utility = soup.find('div', class_='content-utility')
        if content_utility:
            text = content_utility.get_text()
            year, level, parent_topic = extract_info_year_level_topic(clean_text(text))    
        card_title = soup.find('p', class_='card-title', text='Categories')
        if card_title:
            # Find all <p> tags following the 'Categories' card title
            for sibling in card_title.find_next_siblings('p'):
                a_tag = sibling.find('a')
                if a_tag and a_tag.text.strip():
                    categories.append(a_tag.text.strip())

        Intro, LearningOutcome, Summary  = getContent(soup)

        return pdf_link, parent_topic, year, level, Intro, LearningOutcome, Summary , categories, topic_name
    else:
        return "","","","","","","","",""


def extract_info_year_level_topic(topic):
    parent_topics = [
        "Portfolio Management and Wealth Planning",
        "Fixed Income",
        "Corporate Finance",
        "Equity Investments",
        "Financial Reporting and Analysis",
        "Quantitative Methods",
        "Derivatives",
        "Alternative Investments",
        "Economics",
        "Ethical and Professional Standards"
    ]
    # Regex pattern for year, level, and parent topic
    pattern = r'(?P<year>20[0-2]\d) Curriculum CFA Program (?P<level>Level [I]{1,3}) (?P<topic>.+)'
    match = re.match(pattern, topic)

    if match:
        year = match.group('year')
        level = match.group('level')
        topic = match.group('topic')

        # Check if the extracted topic is in the predefined parent topics list
        for parent_topic in parent_topics:
            if parent_topic in topic:
                return str(year), str(level), str(parent_topic)
    return "","",""


def write_to_csv(file_path, header, content):
    # Check if the CSV file already exists
    file_exists = os.path.isfile(file_path)
    
    # Open the file in append mode if it exists, or write mode if it doesn't
    with open(file_path, mode='a' if file_exists else 'w', newline='') as file:
        writer = csv.writer(file)
        
        # If the file didn't exist, write the header first
        if not file_exists:
            writer.writerow(header)
        
        # Write the content to the CSV file
        writer.writerow(content)

def loadenv():
    load_dotenv('../config/.env',override=True)
    
    csv_filename = os.getenv("CSV_CFA_WEB")
    folderpath = os.getenv("DIR_CFA_WEB")
    txt_filename = os.getenv("TXT_CFA_LINKS")
    print("INSIDEEEEEEEEEEEEEEEEE",csv_filename, folderpath, txt_filename)
    return csv_filename, folderpath, txt_filename
    
def process_urls(urls):
    # Create a list to hold the results.
    url_objects = []
    # Initialize the progress bar with the total number of URLs.
    with tqdm(total=len(urls), desc="Processing URLs") as progress_bar:
        # Use ThreadPoolExecutor for multithreading.
        with concurrent.futures.ThreadPoolExecutor() as executor:
            # Create a future for each URL.
            futures = [executor.submit(create_url_object, url) for url in urls]
            # As each future completes, update the progress bar and add the result to the list.
            for future in concurrent.futures.as_completed(futures):
                url_objects.append(future.result())
                progress_bar.update(1)  # Update the progress bar by one step.
    return url_objects

def create_url_object(url):
    try:
        data = extract_information(url)
        # Using ** to unpack the dictionary directly
        data_keys = ['pdfLink', 'parentTopic', 'year', 'level', 'introduction', 
                    'learningOutcome', 'summary', 'categories', 'topicName']
        data = dict(zip(data_keys, data))
        data['url'] = url
        url_instance = UrlClass(**data)
        return url_instance
    except Exception as e :
        print('error for '+ str(url) +'url: '+ str(e))
        
def delete_csv_if_exists(filename):
    # Check if the file exists
    if os.path.exists(filename):
        # Delete the file
        os.remove(filename)
        print(f"File '{filename}' has been deleted.")
    else:
        print(f"File '{filename}' does not exist, no need to delete.")

    
def write_url_objects_to_csv(url_objects: List[UrlClass], filename: str):
    # Open the file in write mode
    with open(filename, mode='w', newline='', encoding='utf-8') as file:
        # Create a csv writer
        writer = csv.writer(file)

        # Write the header row
        headers = ['pdfLink', 'parentTopic', 'year', 'level', 'introduction',
                   'learningOutcome', 'summary', 'categories', 'topicName', 'url']
        writer.writerow(headers)

        # Write data rows
        for row in url_objects:
            # Convert UrlClass object to dictionary and handle list of categories
            # row = obj.dict()
            row['categories'] = ';'.join(row['categories'])  # Convert list to semicolon-separated string
            # Write the row values in the order of headers
            writer.writerow([row[header] for header in headers])

if __name__ == '__main__':

    csv_filename, folderpath, txt_filename =loadenv()
    count = 2

    file_path = folderpath+txt_filename  # Replace with the actual file path
    ## Create/overwrite the file to empty it
    try:
        # Open the file in write mode ('w') or truncate mode ('w+')
        with open(file_path, 'w+', encoding='utf-8'):
            pass  # The 'pass' statement does nothing, effectively emptying the file

        print(f"The file '{file_path}' has been emptied.")
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' does not exist.")
    except Exception as e:
        print(f"An error occurred: {e}")
    listUrl = []
    while(count>=0):
        url = f"https://www.cfainstitute.org/en/membership/professional-development/refresher-readings#first={count*100}&sort=%40refreadingcurriculumyear%20descending&numberOfResults=100"
        listUrl += scrape_coveo_links(url)
        count = count - 1 
    # print(listUrl)
    url_objects = process_urls(listUrl)

    csv_path = folderpath+csv_filename
    delete_csv_if_exists(csv_path)

    # write_url_objects_to_csv(url_objects,csv_path)
    Utility.store_to_csv(url_objects,folderpath,csv_filename)
    # Utility.upload_text_files_to_s3_root(os.getcwd()+"/output_data")




