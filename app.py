from flask import Flask, render_template, request, jsonify, send_file
from pdf_processor import PDFProcessor
from chat_handler import ChatHandler
from dotenv import load_dotenv
import os
from database_handler import DatabaseHandler
from email_processor import EmailProcessor
import pandas as pd
from csv_handle import CSVQueryHandler  # Import the CSVQueryHandler class
from io import BytesIO



vectorstore = None
summary_text_global = ""

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['UPLOAD_FOLDER'] = 'uploads'

# Ensure upload folder exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Initialize processors
pdf_processor = PDFProcessor()
chat_handler = ChatHandler()
db_handler = DatabaseHandler()
email_processor = EmailProcessor()
csv_query_handler = CSVQueryHandler(api_key=os.getenv('GOOGLE_GENERATIVE_AI_API_KEY'))  # Update this line

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    global vectorstore, summary_text_global
    if 'files[]' not in request.files:
        return jsonify({'error': 'No files uploaded'}), 400
    
    files = request.files.getlist('files[]')
    try:
        raw_text = pdf_processor.get_pdf_text(files)
        text_chunks = pdf_processor.get_text_chunks(raw_text)
        vectorstore = pdf_processor.get_vectorstore(text_chunks)
        chat_handler.initialize_conversation(vectorstore)
        
        summary_text_global = pdf_processor.summarize_text(text_chunks)  # Store summary
        
        return jsonify({
            'message': 'Files processed successfully',
            'summary': summary_text_global
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/download-summary', methods=['GET'])
def download_summary():
    global summary_text_global
    if not summary_text_global:
        return jsonify({'error': 'No summary available. Please upload a file first.'}), 400

    try:
        pdf_path = pdf_processor.generate_summary_pdf(summary_text_global)
        return send_file(pdf_path, as_attachment=True, download_name='summary.pdf', mimetype='application/pdf')
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    question = data.get('question')
    
    if not question:
        return jsonify({'error': 'No question provided'}), 400
    
    try:
        response = chat_handler.handle_question(question)
        return jsonify(response)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download-pdf', methods=['POST'])
def download_pdf():
    try:
        pdf_file = chat_handler.create_conversation_pdf()
        return send_file(
            pdf_file,
            as_attachment=True,
            download_name='conversation.pdf',
            mimetype='application/pdf'
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/pdf-chat')
def pdf_chat():
    return render_template('pdf_chat.html')

@app.route('/db-chat')
def db_chat():
    return render_template('db_chat.html')

@app.route('/csv-chat')
def csv_chat():
    return render_template('csv_chat.html')

@app.route('/query-db', methods=['POST'])
def query_db():
    data = request.json
    question = data.get('question')
    
    if not question:
        return jsonify({'error': 'No question provided'}), 400
    
    try:
        # Convert natural language to SQL
        sql_query = db_handler.natural_language_to_sql(question)
        
        # Execute query and get results with analysis
        response = db_handler.execute_query(sql_query, question)
        
        return jsonify({
            'sql_query': sql_query,
            'results': response['results'],
            'analysis': response['analysis']
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/upload-csv', methods=['POST'])
def upload_csv():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    try:
        # Load the CSV file and get initial analysis
        analysis = csv_query_handler.load_csv(file)
        
        return jsonify({
            'message': 'CSV file processed successfully',
            'analysis': analysis
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/query-csv', methods=['POST'])
def query_csv():
    data = request.json
    question = data.get('question')
    
    if not question:
        return jsonify({'error': 'No question provided'}), 400
    
    try:
        # Process the question and get response
        response = csv_query_handler.query(question)
        
        return jsonify({'response': response})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/clear-memory', methods=['POST'])
def clear_memory():
    try:
        db_handler.clear_memory()
        return jsonify({'message': 'Memory cleared successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/email-analysis')
def email_analysis():
    return render_template('email_analysis.html')
@app.route('/fetch-emails', methods=['POST'])
def fetch_emails():
    global vectorstore
    try:
        print("Fetching emails...")
        emails = email_processor.fetch_emails(limit=2)
        print("Analyzing emails...")
        analysis = email_processor.analyze_emails(emails)
        print("Creating email vectorstore...")
        vectorstore = email_processor.create_email_vectorstore(emails)
        chat_handler.initialize_conversation(vectorstore)
        
        return jsonify({
            'message': 'Emails processed successfully',
            'analysis': analysis,
            'email_count': len(emails)
        })
    except Exception as e:
        print(f"Error in fetch_emails: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/search-emails', methods=['POST'])
def search_emails():
    global vectorstore 
    if vectorstore is None:
        return jsonify({'error': 'Please fetch emails first before searching'}), 400
    
    data = request.json
    query = data.get('query')
    
    if not query:
        return jsonify({'error': 'No query provided'}), 400
    
    try:
        results = email_processor.search_emails(query, vectorstore)
        return jsonify({'results': results})
    except Exception as e:
        print(f"Error in search_emails: {str(e)}")  # Add better error logging
        return jsonify({'error': str(e)}), 500
    
@app.route('/download-plot/<plot_id>', methods=['GET'])
def download_plot(plot_id):
    try:
        # Get the plot image from the CSV handler
        img_bytes = csv_query_handler.get_plot_image(plot_id)
        
        # Return the image file
        return send_file(
            BytesIO(img_bytes),
            mimetype='image/png',
            as_attachment=True,
            download_name='plot.png'
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    load_dotenv()
    app.run(debug=True, host='0.0.0.0', port=6363) 