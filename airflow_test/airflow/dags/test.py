import requests
url = 'http://localhost:8078/api/processFulltextDocument'
output_txt_path = 'C:/Users/aptea/OneDrive/Documents/NEU/Sem6/BDIA/Asgn4/Assignment4/airflow_test/airflow/output_data/grobid/2024-l1-topics-combined-2.txt'
input_pdf_path = 'C:/Users/aptea/OneDrive/Documents/NEU/Sem6/BDIA/Asgn4/Assignment4/airflow_test/airflow/config/2024-l1-topics-combined-2.pdf'
with open(input_pdf_path, 'rb') as file:
        files = {'input': file}
        response = requests.post(url, files=files)

        # Check if the request was successful
        print('2')
        if response.status_code == 200:
            with open(output_txt_path, 'w', encoding="utf-8") as output_file:
                output_file.write(response.text)
            print(f'Successfully processed and saved output to {output_txt_path}')