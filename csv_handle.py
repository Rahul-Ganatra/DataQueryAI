import matplotlib
matplotlib.use('Agg')  # Set the backend to Agg before importing pyplot
import matplotlib.pyplot as plt
import pandas as pd
import google.generativeai as genai
from typing import Dict, Any
import os
import json
import seaborn as sns
from io import BytesIO
import base64
import uuid
import numpy as np

class CSVQueryHandler:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv('GOOGLE_GENERATIVE_AI_API_KEY')
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('models/gemini-1.5-flash-latest')
        self.df = None
        self.df_context = None
        self.last_plot_id = None
        plt.style.use('dark_background')  # Use dark theme for plots

    def load_csv(self, file) -> Dict[str, Any]:
        """Load CSV file into a DataFrame and create initial analysis."""
        try:
            self.df = pd.read_csv(file)
            # Take first 100 rows for context
            self.df_context = self.df.head(100)
            
            # Generate initial analysis
            analysis = {
                'columns': self.df.columns.tolist(),
                'head': self.df.head().to_dict(),
                'description': self.df.describe().to_dict()
            }
            return analysis
        except Exception as e:
            raise Exception(f"Error loading CSV: {str(e)}")

    def query(self, question: str) -> Dict[str, str]:
        """Process natural language query about the dataset."""
        if self.df is None:
            raise ValueError("No CSV file loaded. Please upload a file first.")

        try:
            # Create context for the model
            context = self._create_context()
            
            # Create prompt
            prompt = self._create_prompt(question, context)
            
            # Get response from Gemini
            response = self.model.generate_content(prompt)
            
            # Print the complete response for graph generation requests
            print("\nLLM Response:")
            print("=" * 50)
            print(response.text)
            print("=" * 50 + "\n")
            
            # Process the response to extract code and explanation
            processed_response = self._process_response(response.text, question)
            return processed_response
        except Exception as e:
            raise Exception(f"Error processing query: {str(e)}")

    def _create_context(self) -> str:
        """Create context about the dataset for the model."""
        context = f"""
Dataset Information:
- Total rows: {len(self.df)}
- Columns: {', '.join(self.df.columns)}
- Sample data (first few rows):
{self.df_context.head().to_string()}

Basic Statistics:
{self.df.describe().to_string()}

Column Data Types:
{self.df.dtypes.to_string()}
"""
        return context

    def execute_plot_code(self, code: str) -> Dict[str, Any]:
        """Execute matplotlib code and return the plot as base64 image."""
        try:
            # Clean the code
            code = code.strip()
            if code.startswith('```python'):
                code = code.split('```python')[1]
            if code.startswith('```'):
                code = code.split('```')[1]
            code = code.strip()

            # Create a new figure
            plt.clf()
            
            # Create local namespace with required objects
            local_dict = {
                'df': self.df,
                'plt': plt,
                'sns': sns,
                'pd': pd,
                'np': np
            }
            
            try:
                # Execute the plotting code
                exec(code, local_dict)
            except Exception as code_error:
                print(f"Code execution error: {str(code_error)}")
                print("Attempted to execute code:")
                print(code)
                raise code_error
            
            # Save plot to bytes buffer
            buffer = BytesIO()
            plt.savefig(buffer, format='png', bbox_inches='tight', 
                       facecolor='#1a1a1a', dpi=300)
            buffer.seek(0)
            
            # Generate unique ID for the plot
            plot_id = str(uuid.uuid4())
            self.last_plot_id = plot_id
            
            # Convert to base64 for HTML display
            image_base64 = base64.b64encode(buffer.getvalue()).decode()
            
            # Clear the current figure
            plt.close()
            
            return {
                'plot_id': plot_id,
                'image_data': f'data:image/png;base64,{image_base64}'
            }
        except Exception as e:
            print(f"Plot execution error: {str(e)}")
            raise Exception(f"Error executing plot code: {str(e)}")

    def _create_prompt(self, question: str, context: str) -> str:
        """Create a detailed prompt for the model."""
        prompt = f"""You are a data analysis assistant. You have access to a dataset with the following information:

{context}

The user's question is: {question}

Please provide a response in the following format:

EXPLANATION:
[Provide a comprehensive natural language explanation of the analysis. Include relevant statistics and numbers in your explanation.]

PYTHON_CODE:
# Set the style and figure size
plt.style.use('dark_background')
plt.figure(figsize=(12, 6))

# Create the visualization
[Your plotting code here - use only plt, sns, df, pd, or np]

# Customize the plot
plt.title('[Your title]', size=14, pad=20)
plt.xlabel('[Your x-label]', size=12)
plt.ylabel('[Your y-label]', size=12)
plt.grid(True, alpha=0.3)
plt.tight_layout()

Make sure the code:
1. Does not include any import statements
2. Does not include any print statements
3. Uses only plt, sns, df, pd, or np objects
4. Includes all necessary labels and titles
5. Uses appropriate plot types for the analysis requested

For example, if comparing categories:
plt.figure(figsize=(12, 6))
plt.bar(df['category_column'], df['value_column'])
plt.title('Comparison of Values by Category', size=14, pad=20)
plt.xlabel('Category', size=12)
plt.ylabel('Value', size=12)
plt.grid(True, alpha=0.3)
plt.xticks(rotation=45)
plt.tight_layout()

Please ensure the code is complete and executable."""
        return prompt

    def _process_response(self, response: str, question: str) -> Dict[str, Any]:
        """Process the model's response and execute the plotting code."""
        try:
            sections = response.split('\n\n')
            explanation = ""
            code = ""
            
            current_section = None
            for section in sections:
                if 'EXPLANATION:' in section:
                    current_section = 'explanation'
                    explanation = section.replace('EXPLANATION:', '').strip()
                elif 'PYTHON_CODE:' in section:
                    current_section = 'code'
                    # Extract code, removing any markdown code blocks
                    code_content = section.replace('PYTHON_CODE:', '').strip()
                    if '```python' in code_content:
                        code = code_content.split('```python')[1].split('```')[0].strip()
                    elif '```' in code_content:
                        code = code_content.split('```')[1].split('```')[0].strip()
                    else:
                        code = code_content
                elif current_section == 'explanation':
                    explanation += '\n' + section
                elif current_section == 'code' and '```' not in section:
                    code += '\n' + section

            # Clean up the code
            code = code.strip()
            if not code:
                return {
                    'explanation': explanation.strip(),
                    'visualization': None,
                    'plot_id': None,
                    'code': None
                }

            # Execute the plotting code
            try:
                visualization_data = self.execute_plot_code(code)
            except Exception as e:
                print(f"Error in plot execution: {str(e)}")
                print("Code that failed:")
                print(code)
                return {
                    'explanation': explanation.strip() + f"\n\nError creating visualization: {str(e)}",
                    'visualization': None,
                    'plot_id': None,
                    'code': code
                }

            return {
                'explanation': explanation.strip(),
                'visualization': f'<img src="{visualization_data["image_data"]}" class="img-fluid" alt="Data Visualization">' if visualization_data else None,
                'plot_id': visualization_data["plot_id"] if visualization_data else None,
                'code': code.strip()
            }
        except Exception as e:
            print(f"Error processing response: {str(e)}")
            return {
                'explanation': f'Error processing response: {str(e)}',
                'visualization': None,
                'plot_id': None,
                'code': str(e)
            }

    def get_plot_image(self, plot_id: str = None) -> bytes:
        """Return the last generated plot as PNG bytes."""
        try:
            if plot_id == self.last_plot_id:
                buffer = BytesIO()
                plt.savefig(buffer, format='png', bbox_inches='tight', 
                           facecolor='#1a1a1a', dpi=300)
                buffer.seek(0)
                return buffer.getvalue()
            raise Exception("No plot available for download")
        except Exception as e:
            raise Exception(f"Error generating plot image: {str(e)}")

    def _execute_pandas_operation(self, operation: str) -> Any:
        """Safely execute a pandas operation on the dataframe."""
        try:
            result = eval(f"self.df.{operation}")
            return result
        except Exception as e:
            raise Exception(f"Error executing pandas operation: {str(e)}")