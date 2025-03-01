from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from fpdf import FPDF
from dotenv import load_dotenv
import os

class ChatHandler:
    def __init__(self):
        self.conversation = None
        self.chat_history = []
        load_dotenv()
        self.google_api_key = os.getenv('GOOGLE_API_KEY')
        if not self.google_api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment variables")
        
    def initialize_conversation(self, vectorstore):
        llm = ChatGoogleGenerativeAI(
            model="gemini-pro",
            temperature=0.7,
            google_api_key=self.google_api_key,
            convert_system_message_to_human=True,
            max_output_tokens=2048
        )
        
        # Create a proper PromptTemplate with better language handling
        prompt = PromptTemplate(
            template="""You are a helpful assistant that provides information about documents.

Context: {context}

Question: {question}

Previous conversation:
{chat_history}

Instructions:
1. If the question asks for a language change (e.g., "in English", "tell in English"), respond in English
2. If the question is in Hindi, respond in Hindi
3. If the question is in Arabic, respond in Arabic
4. If asked for a summary or overview, provide a comprehensive summary of the document
5. Always base your answer on the provided context
6. If you can't find specific information, say so clearly

Answer:""",
            input_variables=["context", "question", "chat_history"]
        )
        
        memory = ConversationBufferMemory(
            memory_key='chat_history',
            return_messages=True,
            output_key='answer'
        )
        
        self.conversation = ConversationalRetrievalChain.from_llm(
            llm=llm,
            retriever=vectorstore.as_retriever(
                search_type="similarity",
                search_kwargs={
                    "k": 6,  # Increased for better context
                    "return_metadata": True,
                    "fetch_k": 10
                }
            ),
            memory=memory,
            return_source_documents=True,
            chain_type="stuff",
            verbose=True,
            combine_docs_chain_kwargs={"prompt": prompt}
        )

    def handle_question(self, question):
        if not self.conversation:
            raise Exception("Conversation not initialized")
            
        try:
            # Clean and validate the question
            if not question or question.strip() == "":
                return {
                    'answer': "Please ask a specific question about the document.",
                    'sources': []
                }

            # Handle language change requests
            question_lower = question.lower()
            if "in english" in question_lower or "tell in english" in question_lower:
                # Modify the question to explicitly request English
                question = "Please provide the previous answer in English"

            # Handle document summary requests
            if any(phrase in question_lower for phrase in ["tell everything", "what was in the", "summarize", "tell about the pdf"]):
                question = """Please provide a comprehensive summary of the document, including:
                1. The main purpose/solution
                2. Key features
                3. Challenges addressed
                4. Expected impact"""

            response = self.conversation({
                'question': question
            })
            
            # Update chat history
            self.chat_history = response.get('chat_history', [])
            
            # Format response with source information
            sources = []
            if 'source_documents' in response:
                for source in response['source_documents']:
                    page_number = source.metadata.get('page_num', 'Unknown')
                    if page_number not in sources:  # Avoid duplicate page numbers
                        sources.append(page_number)
                
                sources.sort()  # Sort page numbers
            
            answer = response.get('answer', '').strip()
            
            # If no meaningful answer or sources were found
            if not answer or not sources:
                return {
                    'answer': "I apologize, but I couldn't find relevant information in the document to answer your question.",
                    'sources': []
                }
            
            return {
                'answer': answer,
                'sources': [f"Page {page}" for page in sources]
            }
        except Exception as e:
            print(f"Error in handle_question: {str(e)}")
            return {
                'answer': "I apologize, but I encountered an error processing your question. Please try rephrasing it.",
                'sources': []
            }

    def create_conversation_pdf(self):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        
        for message in self.chat_history:
            content = message.content
            role = "User" if message.type == "human" else "Bot"
            pdf.multi_cell(0, 10, f"{role}: {content}")
            pdf.ln(5)
        
        output_file = "conversation.pdf"
        pdf.output(output_file)
        return output_file 