from dotenv import load_dotenv
import os
import sqlite3
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.runnables import RunnablePassthrough
from operator import itemgetter

class DatabaseHandler:
    def __init__(self):
        load_dotenv()
        self.google_api_key = os.getenv('GOOGLE_API_KEY')
        if not self.google_api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment variables")
        
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-pro",
            google_api_key=self.google_api_key,
            temperature=0.1  # Lower temperature for more precise SQL generation
        )
        
        # Initialize database connection
        self.db_path = 'database/data.db'
        os.makedirs('database', exist_ok=True)
        self.init_database()
        
        # Initialize chat history
        self.chat_history = []
        
        # Create the conversation chain
        self.prompt = PromptTemplate.from_template("""
            You are an HR Analytics expert. Based on the following context and results, provide a brief, insightful analysis.
            
            Previous Messages: {chat_history}
            Current Question: {question}
            Query Results: {results}
            
            Provide a concise, professional analysis of these results. Consider previous context when relevant.
            Focus on key insights and business implications. Be direct and specific.
            If this is a follow-up question, reference previous insights when appropriate.
        """)
    
    def init_database(self):
        """Initialize the database with sample tables and data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create tables
        cursor.executescript('''
            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY,
                name TEXT,
                department TEXT,
                salary REAL,
                hire_date DATE,
                position TEXT,  -- Added position field
                email TEXT     -- Added email field
            );
            
            CREATE TABLE IF NOT EXISTS departments (
                id INTEGER PRIMARY KEY,
                name TEXT,
                budget REAL,
                location TEXT,
                head_count INTEGER,  -- Added head count
                established_date DATE -- Added establishment date
            );
            
            -- Clear existing data
            DELETE FROM employees;
            DELETE FROM departments;
            
            -- Insert sample departments
            INSERT INTO departments (name, budget, location, head_count, established_date) VALUES
            ('IT', 1500000, 'New York', 15, '2020-01-01'),
            ('HR', 800000, 'Chicago', 8, '2020-01-01'),
            ('Sales', 2000000, 'Los Angeles', 20, '2020-03-15'),
            ('Engineering', 3000000, 'San Francisco', 25, '2020-02-01'),
            ('Marketing', 1200000, 'Boston', 12, '2021-01-01'),
            ('Finance', 1000000, 'Chicago', 10, '2020-01-01'),
            ('Research', 2500000, 'Seattle', 18, '2021-06-01'),
            ('Operations', 900000, 'Miami', 9, '2022-01-01');
            
            -- Insert sample employees with more diverse data
            INSERT INTO employees (name, department, salary, hire_date, position, email) VALUES
            -- IT Department
            ('John Doe', 'IT', 85000, '2022-01-15', 'Senior Developer', 'john.doe@company.com'),
            ('Charlie Wilson', 'IT', 78000, '2023-01-25', 'System Administrator', 'charlie.w@company.com'),
            ('Sarah Connor', 'IT', 92000, '2022-03-10', 'Security Specialist', 'sarah.c@company.com'),
            ('Mike Ross', 'IT', 75000, '2023-02-15', 'Frontend Developer', 'mike.r@company.com'),
            
            -- HR Department
            ('Jane Smith', 'HR', 65000, '2021-06-20', 'HR Coordinator', 'jane.s@company.com'),
            ('Fiona Clark', 'HR', 67000, '2021-12-10', 'Recruiter', 'fiona.c@company.com'),
            ('Tom Harris', 'HR', 72000, '2022-08-15', 'HR Manager', 'tom.h@company.com'),
            
            -- Sales Department
            ('Bob Johnson', 'Sales', 75000, '2023-03-10', 'Sales Representative', 'bob.j@company.com'),
            ('Diana Miller', 'Sales', 72000, '2022-08-15', 'Sales Associate', 'diana.m@company.com'),
            ('James Wilson', 'Sales', 85000, '2022-05-20', 'Sales Manager', 'james.w@company.com'),
            ('Lisa Chen', 'Sales', 71000, '2023-01-10', 'Sales Representative', 'lisa.c@company.com'),
            
            -- Engineering Department
            ('Alice Brown', 'Engineering', 95000, '2022-11-05', 'Senior Engineer', 'alice.b@company.com'),
            ('Edward Davis', 'Engineering', 92000, '2023-04-01', 'Software Architect', 'edward.d@company.com'),
            ('Rachel Green', 'Engineering', 88000, '2022-09-15', 'DevOps Engineer', 'rachel.g@company.com'),
            ('David Kim', 'Engineering', 90000, '2023-02-01', 'Backend Developer', 'david.k@company.com'),
            
            -- Marketing Department
            ('Emma Watson', 'Marketing', 70000, '2022-07-01', 'Marketing Specialist', 'emma.w@company.com'),
            ('Chris Evans', 'Marketing', 82000, '2021-11-15', 'Marketing Manager', 'chris.e@company.com'),
            ('Sophie Turner', 'Marketing', 68000, '2023-01-20', 'Content Creator', 'sophie.t@company.com'),
            
            -- Finance Department
            ('Michael Scott', 'Finance', 88000, '2021-08-10', 'Financial Analyst', 'michael.s@company.com'),
            ('Pam Beesly', 'Finance', 75000, '2022-03-15', 'Accountant', 'pam.b@company.com'),
            ('Oscar Martinez', 'Finance', 82000, '2021-09-01', 'Senior Accountant', 'oscar.m@company.com'),
            
            -- Research Department
            ('Walter White', 'Research', 98000, '2021-07-15', 'Research Director', 'walter.w@company.com'),
            ('Jesse Pinkman', 'Research', 75000, '2022-01-10', 'Research Associate', 'jesse.p@company.com'),
            ('Gus Fring', 'Research', 92000, '2021-11-30', 'Senior Researcher', 'gus.f@company.com'),
            
            -- Operations Department
            ('Tony Stark', 'Operations', 95000, '2022-04-15', 'Operations Manager', 'tony.s@company.com'),
            ('Peter Parker', 'Operations', 72000, '2023-01-05', 'Operations Analyst', 'peter.p@company.com'),
            ('Bruce Banner', 'Operations', 85000, '2022-06-20', 'Process Specialist', 'bruce.b@company.com');
        ''')
        
        conn.commit()
        conn.close()
    
    def natural_language_to_sql(self, question):
        """Convert natural language to SQL query with business insights"""
        if "insight" in question.lower() or "overview" in question.lower():
            return """
                SELECT 
                    d.name as Department,
                    COUNT(e.id) as Employee_Count,
                    ROUND(AVG(e.salary), 2) as Avg_Salary,
                    MIN(e.salary) as Min_Salary,
                    MAX(e.salary) as Max_Salary,
                    d.budget as Department_Budget,
                    ROUND(d.budget/COUNT(e.id), 2) as Budget_Per_Employee,
                    COUNT(CASE WHEN ((julianday('now') - julianday(e.hire_date))/365) >= 2 THEN 1 END) as Senior_Employees,
                    GROUP_CONCAT(DISTINCT e.position) as Positions
                FROM departments d
                LEFT JOIN employees e ON d.name = e.department
                GROUP BY d.name
                ORDER BY d.budget DESC;
            """

        prompt = PromptTemplate(
            template="""You are an AI SQL and HR analytics expert. Convert the following business/HR question into an appropriate SQL query.
            
            Available tables and their schemas:
            - employees (id, name, department, salary, hire_date, position, email)
            - departments (id, name, budget, location, head_count, established_date)
            
            For promotion-related queries, consider:
            - Tenure (based on hire_date)
            - Current salary compared to department average
            - Position level
            
            Example business queries you can handle:
            1. "Who deserves a promotion?" 
               → Look for employees with longer tenure and below-average department salary
            2. "Which departments need more budget?"
               → Compare department budgets per head count
            3. "Who are our top performers?"
               → Find senior positions with above-average salaries
            4. "Where should we hire more people?"
               → Analyze departments by head count and budget ratio
            5. "Who might leave the company?"
               → Find employees with longer tenure but below-average salaries
            
            Business Question: {question}
            
            Return only the SQL query that provides relevant insights. No formatting or explanation.
            """,
            input_variables=["question"]
        )
        
        # Map common business questions to SQL queries
        business_queries = {
            "promotion": """
                SELECT 
                    e.name,
                    e.department,
                    e.position,
                    e.salary,
                    e.hire_date,
                    ROUND(AVG(e2.salary), 2) as dept_avg_salary,
                    ROUND(((julianday('now') - julianday(e.hire_date))/365), 1) as years_of_service,
                    ROUND((e.salary - AVG(e2.salary))/AVG(e2.salary) * 100, 1) as salary_vs_avg_percent
                FROM employees e
                JOIN employees e2 ON e.department = e2.department
                GROUP BY e.id
                HAVING 
                    years_of_service >= 1.5 
                    AND salary_vs_avg_percent < 0
                ORDER BY 
                    years_of_service DESC,
                    salary_vs_avg_percent ASC
                LIMIT 10;
            """,
            "budget": """
                SELECT 
                    d.name as department,
                    d.budget,
                    d.head_count,
                    ROUND(d.budget/d.head_count, 2) as budget_per_employee,
                    COUNT(e.id) as current_employees,
                    ROUND(d.budget/COUNT(e.id), 2) as actual_budget_per_employee
                FROM departments d
                LEFT JOIN employees e ON d.name = e.department
                GROUP BY d.name
                ORDER BY budget_per_employee DESC;
            """,
            "retention": """
                SELECT 
                    e.name,
                    e.department,
                    e.position,
                    e.salary,
                    ROUND(((julianday('now') - julianday(e.hire_date))/365), 1) as years_of_service,
                    ROUND((e.salary - avg_salary)/avg_salary * 100, 1) as salary_diff_percent
                FROM employees e
                JOIN (
                    SELECT department, AVG(salary) as avg_salary
                    FROM employees
                    GROUP BY department
                ) dept_avg ON e.department = dept_avg.department
                WHERE 
                    years_of_service >= 2 
                    AND salary_diff_percent < -10
                ORDER BY salary_diff_percent ASC;
            """,
            "email": """
                SELECT 
                    SUBSTR(e.email, INSTR(e.email, '@') + 1) as domain,
                    COUNT(*) as count,
                    GROUP_CONCAT(e.department) as departments,
                    GROUP_CONCAT(e.position) as positions
                FROM employees e
                GROUP BY domain
                ORDER BY count DESC;
            """,
            "email_pattern": """
                SELECT 
                    e.department,
                    e.position,
                    e.email,
                    CASE 
                        WHEN e.email LIKE '%__%@company.com' THEN 
                            CASE 
                                WHEN e.email LIKE '%_%_%@company.com' THEN 'full_name'
                                WHEN e.email LIKE '%_%@company.com' THEN 'first_initial_last'
                                ELSE 'other'
                            END
                        ELSE 'external'
                    END as email_pattern
                FROM employees e
                ORDER BY department, position;
            """
        }

        question_lower = question.lower()
        
        # Check if it's a common business question
        if "promot" in question_lower or "deserve" in question_lower:
            return business_queries["promotion"]
        elif "budget" in question_lower or "spend" in question_lower:
            return business_queries["budget"]
        elif "leave" in question_lower or "retention" in question_lower or "risk" in question_lower:
            return business_queries["retention"]
        
        # Add email-related keywords
        if "email" in question_lower or "domain" in question_lower:
            if "pattern" in question_lower or "format" in question_lower:
                return business_queries["email_pattern"]
            return business_queries["email"]
        
        # For other questions, use the LLM
        chain = prompt | self.llm | StrOutputParser()
        sql_query = chain.invoke({"question": question})
        
        # Clean the query
        sql_query = sql_query.strip()
        sql_query = sql_query.replace('```sql', '').replace('```', '')
        sql_query = sql_query.strip()
        
        return sql_query

    def format_results(self, results):
        """Format results with business insights"""
        if not results:
            return "No relevant data found for analysis."

        formatted_results = []
        for row in results:
            # Add business insights based on the data
            if 'years_of_service' in row:
                row['tenure_insight'] = (
                    'Senior' if row['years_of_service'] > 3 
                    else 'Mid-level' if row['years_of_service'] > 1.5 
                    else 'Junior'
                )
            if 'salary_vs_avg_percent' in row:
                row['compensation_status'] = (
                    'Above Average' if row.get('salary_vs_avg_percent', 0) > 0
                    else 'Below Average'
                )
            formatted_results.append(row)

        return formatted_results

    def generate_natural_language_response(self, question, results):
        """Generate a natural language response with context awareness"""
        try:
            formatted_history = "\n".join([
                f"Human: {msg.content}" if isinstance(msg, HumanMessage) else f"Assistant: {msg.content}"
                for msg in self.chat_history
            ])
            
            # Add email analysis template
            if "email" in question.lower() or "domain" in question.lower():
                analysis_prompt = PromptTemplate.from_template("""
                    You are an Email Systems Analyst. Analyze the following email data:
                    
                    Previous Messages: {chat_history}
                    Current Question: {question}
                    Query Results: {results}
                    
                    Format your response like this:
                    
                    📧 Email Domain Analysis
                    • Primary domain distribution
                    • Department-specific patterns
                    • External vs internal emails
                    
                    🔍 Email Format Patterns
                    • Most common naming conventions
                    • Consistency across departments
                    • Any pattern violations
                    
                    ⚡ Key Observations
                    • Standardization status
                    • Security implications
                    • Recommended actions
                    
                    Keep points brief and use specific numbers.
                    Maximum 4-5 points per section.
                """)
            else:
                # Use existing analysis prompt for non-email queries
                analysis_prompt = self.prompt

            chain = analysis_prompt | self.llm | StrOutputParser()
            analysis = chain.invoke({
                "chat_history": formatted_history,
                "question": question,
                "results": str(results)
            })
            
            # Update chat history
            self.chat_history.extend([
                HumanMessage(content=question),
                AIMessage(content=analysis)
            ])
            
            return analysis.strip()
        except Exception as e:
            return "Unable to generate analysis: " + str(e)

    def handle_follow_up_query(self, question):
        """Handle follow-up questions by considering conversation context"""
        try:
            # Format chat history
            formatted_history = "\n".join([
                f"Human: {msg.content}" if isinstance(msg, HumanMessage) else f"Assistant: {msg.content}"
                for msg in self.chat_history
            ])
            
            # Create prompt for question interpretation
            interpret_prompt = PromptTemplate.from_template("""
                Based on the conversation history, help interpret this follow-up question.
                
                Conversation History: {chat_history}
                Follow-up Question: {question}
                
                If this is a follow-up question, consider the context from previous questions.
                Return a complete query that includes any relevant context from the conversation.
                If this is a new question, return it as is.
            """)
            
            chain = interpret_prompt | self.llm | StrOutputParser()
            interpreted_question = chain.invoke({
                "chat_history": formatted_history,
                "question": question
            })
            
            return interpreted_question.strip()
        except Exception as e:
            return question

    def execute_query(self, query, original_question):
        """Execute SQL query with conversation memory"""
        try:
            # Interpret question with context
            interpreted_question = self.handle_follow_up_query(original_question)
            
            # Generate and execute SQL
            sql_query = self.natural_language_to_sql(interpreted_question)
            
            query = sql_query.strip()
            if not query.endswith(';'):
                query += ';'
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(query)
            columns = [description[0] for description in cursor.description]
            results = cursor.fetchall()
            conn.close()
            
            formatted_results = []
            for row in results:
                formatted_results.append(dict(zip(columns, row)))
            
            formatted_results = self.format_results(formatted_results)
            
            # Generate contextual analysis
            analysis = self.generate_natural_language_response(interpreted_question, formatted_results)
            
            return {
                'results': formatted_results,
                'analysis': analysis,
                'interpreted_question': interpreted_question if interpreted_question != original_question else None
            }
        except Exception as e:
            raise Exception(f"Error executing query: {str(e)}")

    def clear_memory(self):
        """Clear conversation memory"""
        self.chat_history = [] 