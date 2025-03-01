from dotenv import load_dotenv
import os
import email
import imaplib
from datetime import datetime
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_community.vectorstores import FAISS

class EmailProcessor:
    def __init__(self):
        load_dotenv()
        self.google_api_key = os.getenv('GOOGLE_API_KEY')
        self.email_password = os.getenv('MAIL_PASSWORD')
        self.email_address = os.getenv('MAIL_USERNAME')
        
        if not all([self.google_api_key, self.email_password, self.email_address]):
            raise ValueError("Missing required environment variables")
        
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-pro",
            google_api_key=self.google_api_key,
            temperature=0.7
        )
        
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model="models/embedding-001",
            google_api_key=self.google_api_key,
            task_type="retrieval_query"
        )
        
        self.email_cache = {}
    
    def connect_to_email(self):
        """Connect to email server"""
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(self.email_address, self.email_password)
        return mail
    
    def fetch_emails(self, folder="INBOX", limit=100):
        """Fetch emails from specified folder"""
        try:
            mail = self.connect_to_email()
            mail.select(folder)
            
            _, messages = mail.search(None, "ALL")
            email_ids = messages[0].split()
            
            # Get the last 'limit' number of emails
            email_ids = email_ids[-limit:] if len(email_ids) > limit else email_ids
            
            emails = []
            for email_id in email_ids:
                _, msg = mail.fetch(email_id, "(RFC822)")
                email_body = msg[0][1]
                email_message = email.message_from_bytes(email_body)
                
                # Extract email data
                subject = email_message["subject"]
                from_address = email_message["from"]
                date = email_message["date"]
                
                # Get email content
                content = ""
                if email_message.is_multipart():
                    for part in email_message.walk():
                        if part.get_content_type() == "text/plain":
                            content += part.get_payload(decode=True).decode()
                else:
                    content = email_message.get_payload(decode=True).decode()
                
                emails.append({
                    "id": email_id.decode(),
                    "subject": subject,
                    "from": from_address,
                    "date": date,
                    "content": content
                })
            
            mail.close()
            mail.logout()
            
            return emails
        except Exception as e:
            raise Exception(f"Error fetching emails: {str(e)}")
    
    def analyze_emails(self, emails):
        """Analyze email communications"""
        analysis_prompt = PromptTemplate.from_template("""
            You are an Email Communications Analyst. Analyze the following email data:
            
            Emails: {emails}
            
            Provide a comprehensive analysis using this format:
            
            📊 Communication Patterns
            • Email volume and frequency
            • Most active senders/recipients
            • Peak communication times
            
            🎯 Content Analysis
            • Common topics and themes
            • Sentiment analysis
            • Priority patterns
            
            🔄 Response Metrics
            • Average response times
            • Communication flows
            • Thread lengths
            
            💡 Key Insights
            • Notable patterns
            • Areas for improvement
            • Action recommendations
            
            Keep insights specific and data-driven.
            Focus on actionable patterns and trends.
        """)
        
        chain = analysis_prompt | self.llm | StrOutputParser()
        return chain.invoke({"emails": str(emails)})
    
    def create_email_vectorstore(self, emails):
        """Create vector store for email search"""
        texts = [f"Subject: {e['subject']}\nFrom: {e['from']}\nContent: {e['content']}" for e in emails]
        return FAISS.from_texts(texts=texts, embedding=self.embeddings)
    
    def search_emails(self, query, vectorstore):
        """Search emails using semantic search"""
        results = vectorstore.similarity_search(query)
        return results 