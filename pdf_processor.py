import os
from PyPDF2 import PdfReader
from langchain.text_splitter import CharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_community.vectorstores import FAISS
from dotenv import load_dotenv
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import os

class PDFProcessor:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        # Get API key from environment
        google_api_key = os.getenv('GOOGLE_API_KEY')
        if not google_api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment variables")
            
        # Updated embeddings configuration
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model="models/embedding-001",
            google_api_key=google_api_key,
            task_type="retrieval_query"
        )
        
        # Updated LLM configuration with numeric safety settings
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-pro",
            google_api_key=google_api_key,
            temperature=0.7,
            generation_config={
                "temperature": 0.7,
                "top_p": 0.8,
                "top_k": 40,
                "max_output_tokens": 2048,
            }
        )
    
    def get_pdf_text(self, pdf_files):
        pdf_text_with_page_numbers = []
        for pdf in pdf_files:
            try:
                pdf_reader = PdfReader(pdf)
                for page_num, page in enumerate(pdf_reader.pages, start=1):
                    text = page.extract_text()
                    if text and text.strip():  # Only add non-empty text
                        # Clean and format the text
                        cleaned_text = ' '.join(text.split())  # Remove extra whitespace
                        pdf_text_with_page_numbers.append((cleaned_text, page_num))
            except Exception as e:
                print(f"Error processing PDF {pdf.name}: {str(e)}")
        return pdf_text_with_page_numbers

    def get_text_chunks(self, text_with_page_numbers):
        text_splitter = CharacterTextSplitter(
            separator="\n",
            chunk_size=1500,  # Increased chunk size
            chunk_overlap=200,
            length_function=len
        )
        
        chunks_with_metadata = []
        for text, page_num in text_with_page_numbers:
            chunks = text_splitter.split_text(text)
            for chunk in chunks:
                if chunk.strip():  # Only add non-empty chunks
                    chunks_with_metadata.append({
                        "chunk": chunk,
                        "page_num": page_num,
                        "source": f"Page {page_num}"
                    })
        return chunks_with_metadata

    def get_vectorstore(self, chunks_with_metadata):
        texts = [chunk['chunk'] for chunk in chunks_with_metadata]
        metadatas = [{"page_num": chunk['page_num']} for chunk in chunks_with_metadata]
        return FAISS.from_texts(texts=texts, embedding=self.embeddings, metadatas=metadatas)

    def summarize_text(self, text_chunks):
        summarization_prompt = PromptTemplate(
            template="""Please provide a comprehensive summary of the following text. Include key points and main ideas:

{text}

Summary:""",
            input_variables=["text"]
        )
        
        # Create a new chain using the modern approach
        chain = (
            {"text": RunnablePassthrough()} 
            | summarization_prompt 
            | self.llm 
            | StrOutputParser()
        )
        
        full_text = " ".join([chunk['chunk'] for chunk in text_chunks])
        return chain.invoke(full_text) 
    
    def generate_summary_pdf(self, summary_text):
        """
        Generates a PDF file containing the summary text.
        Returns the file path.
        """
        output_dir = "generated_pdfs"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        pdf_path = os.path.join(output_dir, "summary.pdf")
        
        # Create PDF
        c = canvas.Canvas(pdf_path, pagesize=letter)
        c.setFont("Helvetica", 12)
        
        y_position = 750  # Starting position for text

        # Split summary into lines and write to PDF
        for line in summary_text.split("\n"):
            c.drawString(50, y_position, line)
            y_position -= 20  # Move down for next line

        c.save()
        return pdf_path