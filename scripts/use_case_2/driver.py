import snowflake_setup
import generate_qna
import save_to_pinecone
import parse_pdf

def main():
    parse_pdf.main()
    
    knowledge_base = snowflake_setup.main()

    generate_qna.main(knowledge_base)

    save_to_pinecone.main()

if __name__ == "__main__":
    main()
