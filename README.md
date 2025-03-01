# DataQueryAI

DataQueryAI is a versatile application designed to handle various data processing tasks, including PDF processing, database querying, CSV handling, and email analysis. It leverages the power of Flask for web interactions and integrates with several AI and data processing libraries to provide a comprehensive data querying solution.

## Features

- **PDF Processing**: Upload and process PDF files to extract and summarize content.
- **Chat Interface**: Engage with a chat interface for interactive data queries.
- **Database Interaction**: Query databases using a simple web interface.
- **CSV Handling**: Upload and query CSV files for data analysis.
- **Email Analysis**: Fetch and analyze emails for insights.
- **Downloadable Reports**: Generate and download summaries and plots.

## Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd DataQueryAI
   ```

2. **Install dependencies**:
   Ensure you have Python installed, then run:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**:
   Create a `.env` file in the root directory and configure your environment variables as needed.

## Usage

1. **Run the application**:
   ```bash
   python app.py
   ```

2. **Access the web interface**:
   Open your web browser and navigate to `http://localhost:5000`.

## Dependencies

The project relies on several key libraries and frameworks:

- **Flask**: Core framework for web interactions.
- **SQLAlchemy**: Database ORM for handling database operations.
- **PyPDF2, reportlab, fpdf2**: Libraries for PDF processing.
- **LangChain**: AI and language processing.
- **BeautifulSoup4**: Text processing and HTML parsing.
- **Boto3**: AWS integration for deployment.
- **Cryptography, PyJWT, bcrypt**: Security and authentication.
- **Requests, urllib3**: HTTP requests handling.

For a complete list of dependencies, refer to the `requirements.txt` file.

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request for any enhancements or bug fixes.

## License

This project is licensed under the MIT License. See the `LICENSE` file for more details. 

