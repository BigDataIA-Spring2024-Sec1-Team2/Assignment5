import os
import PyPDF2
from dotenv import load_dotenv

load_dotenv('./config/.env',override=True)

def parse_pdf(folder_path):
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


def main():
    folder_path = os.getenv("DIR_CFA_WEB")  # Replace 'input_folder_path' with the path to your input folder
    parse_pdf(folder_path)

if __name__ == "__main__":
    main()
