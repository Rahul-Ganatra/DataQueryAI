import os
import streamlit as st
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from langchain.text_splitter import CharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain, LLMChain
from langchain.prompts import PromptTemplate
from htmlTemplates import css, bot_template, user_template
from langchain_community.vectorstores import FAISS
from fpdf import FPDF
from googletrans import Translator  # Import googletrans for translation support

# Step 1: Extract text and page numbers from PDF documents
def get_pdf_text(pdf_docs):
    pdf_text_with_page_numbers = []
    for pdf in pdf_docs:
        pdf_reader = PdfReader(pdf)
        for page_num, page in enumerate(pdf_reader.pages, start=1):
            page_text = page.extract_text()
            if page_text:
                pdf_text_with_page_numbers.append((page_text, page_num))
            else:
                print(f"No text found on page: {page_num}")
    return pdf_text_with_page_numbers

# Step 2: Split text into chunks and include page numbers
def get_text_chunks(text_with_page_numbers):
    text_splitter = CharacterTextSplitter(
        separator="\n",
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len
    )

    chunks_with_metadata = []
    for text, page_num in text_with_page_numbers:
        chunks = text_splitter.split_text(text)
        for chunk in chunks:
            chunks_with_metadata.append({"chunk": chunk, "page_num": page_num})

    st.info(f"Number of chunks created: {len(chunks_with_metadata)}")  # Added message display
    return chunks_with_metadata

# Step 3: Create a vectorstore from text chunks with metadata
def get_vectorstore(chunks_with_metadata):
    if not chunks_with_metadata:
        raise ValueError("The text chunks list is empty. Make sure to provide valid text data.")

    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")

    texts = [chunk['chunk'] for chunk in chunks_with_metadata]
    metadatas = [{"page_num": chunk['page_num']} for chunk in chunks_with_metadata]

    vectorstore = FAISS.from_texts(texts=texts, embedding=embeddings, metadatas=metadatas)
    st.success("Vectorstore created successfully!")  # Added message display
    return vectorstore

# Step 4: Create a conversational chain that retrieves metadata
def get_conversation_chain(vectorstore):
    llm = ChatGoogleGenerativeAI(model="models/gemini-1.5-flash-latest", temperature=0.2)
    memory = ConversationBufferMemory(memory_key='chat_history', return_messages=True)

    conversation_chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=vectorstore.as_retriever(search_type="similarity", search_kwargs={"return_metadata": True}),
        memory=memory
    )
    st.info("Conversation chain initialized.")  # Added message display
    return conversation_chain

# Step 5: Summarize the text chunks
summarization_prompt = PromptTemplate(
    template="Summarize the following text:\n\n{text}",
    input_variables=["text"]
)

def summarize_text(text_chunks):
    llm = ChatGoogleGenerativeAI(model="models/gemini-1.5-flash-latest", temperature=0.2)  # Initialize the LLM
    summary_chain = LLMChain(llm=llm, prompt=summarization_prompt)  # Use the prompt template here
    full_text = " ".join([chunk['chunk'] for chunk in text_chunks])  # Combine chunks into one string
    summary = summary_chain.run({"text": full_text})  # Pass the combined text to the chain
    st.success("Summary generated!")  # Added message display
    return summary

# Step 6: Create a PDF with the conversation
def create_pdf(chat_history):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    pdf.set_font("Arial", size=12)
    
    # Add title
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="Conversation with the Bot", ln=True, align="C")
    pdf.ln(10)  # Line break
    
    # Add conversation messages
    pdf.set_font("Arial", size=12)
    for i, message in enumerate(chat_history):
        if i % 2 == 0:  # User message
            pdf.set_text_color(0, 0, 255)  # Blue for user
            pdf.multi_cell(0, 10, f"User: {message.content}")
        else:  # Bot response
            pdf.set_text_color(255, 0, 0)  # Red for bot
            pdf.multi_cell(0, 10, f"Bot: {message.content}")
        
        pdf.ln(5)  # Add space between messages
    
    # Save PDF to a file
    pdf_file = "conversation.pdf"
    pdf.output(pdf_file)
    return pdf_file

# Translation utility function to handle multilingual input and output
def translate_from_english(text, original_language="en"):
    translator = Translator()
    translated = translator.translate(text, src='en', dest=original_language)
    return translated.text

def translate_to_english(text, target_language="en"):
    translator = Translator()
    translated = translator.translate(text, dest=target_language)
    return translated.text

# Define the prompt template for question generation
question_generation_prompt = PromptTemplate(
    template="Generate questions and answers based on the following summary:\n\n{text}",
    input_variables=["text"]
)

# Define the function to generate questions and answers from the summary
def generate_questions_answers_from_llm(summary_text):
    llm = ChatGoogleGenerativeAI(model="models/gemini-1.5-flash-latest", temperature=0.7)
    question_generation_chain = LLMChain(llm=llm, prompt=question_generation_prompt)
    questions_answers = question_generation_chain.run({"text": summary_text})
    return questions_answers

# Step 7: Handle user input and allow PDF download
def handle_userinput(user_question):
    original_language = 'en'  # Default is English

    # Translate question if it's not in English
    # Example usage in your handle_userinput function:
    if user_question != "":
        detected_lang = Translator().detect(user_question).lang
    if detected_lang != "en":
        user_question = translate_to_english(user_question, target_language="en")
        original_language = detected_lang  # Store the original language

    
    # Get the bot's response to the translated question
    response = st.session_state.conversation({'question': user_question})
    st.session_state.chat_history = response['chat_history']

    # Translate the response back to the user's language
    for i, message in enumerate(st.session_state.chat_history):
        if i % 2 == 0:  # User message
            st.write(user_template.replace("{{MSG}}", message.content), unsafe_allow_html=True)
        else:  # Bot response
            if 'source_documents' in response and response['source_documents']:
                sources = response['source_documents']
                source_info = []
                for source in sources:
                    page_number = source.metadata.get('page_num', 'Unknown')
                    source_info.append(f"Page {page_number}")
                
                # Format the bot response with the page number(s) included
                bot_response_with_page = f"{message.content}\n\n_Source(s): {', '.join(source_info)}_"
            else:
                bot_response_with_page = message.content

            # Translate the bot's response back to the user's original language
            if original_language != "en":
                bot_response_with_page = translate_from_english(bot_response_with_page, original_language)

            st.write(bot_template.replace("{{MSG}}", bot_response_with_page), unsafe_allow_html=True)

    # Allow the user to download the conversation as PDF
    if st.button("Download Conversation as PDF"):
        pdf_file = create_pdf(st.session_state.chat_history)
        with open(pdf_file, "rb") as f:
            st.download_button("Download PDF", f, file_name="conversation.pdf", mime="application/pdf")


def main():
    load_dotenv()
    st.set_page_config(page_title="Chat with multiple PDFs", page_icon=":books:")
    st.write(css, unsafe_allow_html=True)

    # Initialize session state variables
    if "conversation" not in st.session_state:
        st.session_state.conversation = None
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = None
    if "summary" not in st.session_state:
        st.session_state.summary = None
    if "show_summary" not in st.session_state:
        st.session_state.show_summary = False
    if "questions_answers" not in st.session_state:
        st.session_state.questions_answers = None

    st.header("Chat with multiple PDFs :books:")

    # Sidebar for PDF processing
    with st.sidebar:
        st.subheader("Your documents")
        pdf_docs = st.file_uploader("Upload your PDFs here and click on 'Process'", accept_multiple_files=True)
        if st.button("Process"):
            with st.spinner("Processing"):
                if not pdf_docs:
                    st.error("Please upload at least one PDF document.")
                    return
                raw_text = get_pdf_text(pdf_docs)
                text_chunks = get_text_chunks(raw_text)
                if not text_chunks:
                    st.error("No valid text chunks created. Please check your PDF files.")
                    return
                vectorstore = get_vectorstore(text_chunks)
                st.session_state.conversation = get_conversation_chain(vectorstore)

                # Generate the summary
                st.session_state.summary = summarize_text(text_chunks)
                st.success("PDF processed and summary generated!")
                st.session_state.show_summary = False  # Reset the summary display

    # Chat input section
    user_question = st.text_input("Ask a question about your documents:")
    if user_question and not st.session_state.show_summary:
        handle_userinput(user_question)

    # Option to show the generated summary
    if st.session_state.summary:
        if st.button("Show Summary"):
            st.session_state.show_summary = not st.session_state.show_summary
            st.session_state.questions_answers = generate_questions_answers_from_llm(st.session_state.summary)
        
        if st.session_state.show_summary:
            st.subheader("Summary of the PDFs:")
            st.write(st.session_state.summary)
            
            if st.session_state.questions_answers:
                st.subheader("Generated Questions and Answers:")
                st.write(st.session_state.questions_answers)

if __name__ == "__main__":
    main()

