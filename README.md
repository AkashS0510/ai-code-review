# AI Code Review System

## Project Overview
The AI Code Review System is an asynchronous GitHub Pull Request (PR) analysis and AI code review platform. It leverages OpenAI's GPT models to provide detailed code reviews, including suggestions for improvements, identification of potential bugs, and adherence to best practices.

---

## Project Setup Instructions

### Prerequisites
- Python 3.11
- PostgreSQL
- Redis
- Docker (optional for containerized setup)

### Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/AkashS0510/ai-code-review
   cd ai-code-review
   ```

2. Set up a virtual environment:
   ```bash
   python3 -m venv ai-code-review/pyvenv
   source ai-code-review/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r src/requirements.txt
   ```

4. Configure environment variables:
   - Copy `.env.example` to `.env`:
     ```bash
     cp src/.env.example src/.env
     ```
   - Update the `.env` file with your database, Redis, and Azure OpenAI credentials.

5. Start the Celery Worker
   To start the Celery worker for background task processing, run the following command:
   ```bash
   celery -A src.celery_app worker --loglevel=info
   ```

   - **`-A src.celery_app`**: Specifies the application module where the Celery instance is defined.
   - **`--loglevel=info`**: Sets the logging level to `info` for detailed logs during task execution.

6. Start the application:
   ```bash
   uvicorn src.main:app --reload
   ```



---

## API Documentation

### Base URL
`http://localhost:8000`

### Live API URL
The live API is hosted at: `https://ai-code-review-e6zw.onrender.com`

### Endpoints

#### Health Check
- **GET** `/`
  - **Description**: Check if the service is running.
  - **Response**:
    ```json
    {
      "message": "AI Code Review System is running",
      "status": "healthy"
    }
    ```

#### Start PR Analysis
- **POST** `/api/v1/analyze`
  - **Description**: Start a new PR analysis task.
  - **Request Body**:
    ```json
    {
      "repo_url": "https://github.com/user/repo",
      "pr_number": 123,
      "github_token": "<optional-token>"
    }
    ```
  - **Response**:
    ```json
    {
      "task_id": "<unique-task-id>",
      "status": "PENDING",
      "message": "PR analysis started"
    }
    ```
  - **Example cURL Command**:
    ```bash
    curl -X POST \
      https://ai-code-review-e6zw.onrender.com/api/v1/analyze \
      -H "Content-Type: application/json" \
      -d '{
        "repo_url": "https://github.com/user/repo",
        "pr_number": 123,
        "github_token": "<optional-token>"
      }'
    ```

#### Get Task Status
- **GET** `/api/v1/status/{task_id}`
  - **Description**: Retrieve the status of a specific task.
  - **Example cURL Command**:
    ```bash
    curl -X GET \
      https://ai-code-review-e6zw.onrender.com/api/v1/status/<task_id>
    ```

#### Get Task Results
- **GET** `/api/v1/results/{task_id}`
  - **Description**: Retrieve the AI review results for a completed task.
  - **Example cURL Command**:
    ```bash
    curl -X GET \
      https://ai-code-review-e6zw.onrender.com/api/v1/results/<task_id>
    ```

#### List Tasks
- **GET** `/api/v1/tasks`
  - **Description**: List all tasks with optional pagination and status filtering.

#### Delete Task
- **DELETE** `/api/v1/tasks/{task_id}`
  - **Description**: Delete a specific task and its results.

#### System Statistics
- **GET** `/api/v1/stats`
  - **Description**: Retrieve overall system statistics.

---

## Design Decisions

1. **Asynchronous Processing**:
   - **Why**: Pull request analysis can involve processing large amounts of data, which may take significant time. To ensure the API remains responsive, tasks are processed asynchronously.
   - **How**: Celery is used as the task queue, and Redis serves as the message broker. This allows tasks to be queued and processed in the background without blocking the main application thread.

2. **Database Choice**:
   - **Why**: A relational database is ideal for storing structured data such as task metadata, user information, and analysis results.
   - **How**: PostgreSQL is chosen for its reliability, scalability, and support for advanced features like JSONB for semi-structured data storage.

3. **AI Integration**:
   - **Why**: The core functionality of the system relies on AI to perform code reviews. OpenAI's GPT models are well-suited for natural language understanding and generating detailed code reviews.
   - **How**: Azure OpenAI is used to integrate GPT models. The integration is secured using API keys and environment variables to ensure sensitive information is not hardcoded.

4. **API Framework**:
   - **Why**: A modern, high-performance framework is essential for building a scalable and maintainable API.
   - **How**: FastAPI is chosen for its asynchronous capabilities, automatic OpenAPI documentation generation, and ease of use.

5. **Scalability and Fault Tolerance**:
   - **Why**: The system needs to handle multiple concurrent tasks and ensure reliability even under high load.
   - **How**: Redis is used as a message broker for Celery, enabling horizontal scaling of workers. Additionally, Celery's retry mechanism ensures tasks are retried in case of transient failures.

6. **Structured Output**:
   - **Why**: Consistent and structured output is crucial for downstream processing and user interpretation.
   - **How**: Pydantic models are used to define and validate the structure of input and output data, ensuring consistency and reducing errors.

7. **Security**:
   - **Why**: The system interacts with external APIs and processes potentially sensitive data.
   - **How**: Environment variables are used to store sensitive information like API keys. Additionally, input validation and sanitization are implemented to prevent injection attacks.

8. **Modular Design**:
   - **Why**: A modular architecture makes the system easier to maintain, test, and extend.
   - **How**: The codebase is organized into distinct modules such as `services`, `workers`, and `models`, each responsible for a specific aspect of the system.


---

## Future Improvements

1. **Enhanced AI Review**:
   - Incorporate additional AI models for specialized code analysis (e.g., security, performance).

2. **User Authentication**:
   - Add OAuth-based authentication for secure access to the API.

3. **Web Interface**:
   - Develop a frontend dashboard for easier task management and result visualization.

4. **Multi-Language Support**:
   - Extend support for analyzing code in multiple programming languages.

5. **Real-Time Notifications**:
   - Integrate real-time notifications for task status updates.

6. **Error Handling**:
   - Improve error handling and logging for better debugging and user feedback.

---

## Running Tests

To ensure the system is functioning as expected, you can run the test suite provided in the `tests/` directory. The tests are written using `pytest`.

1. Set up a virtual environment:
   ```bash
   python3 -m venv ai-code-review/pyvenv
   source ai-code-review/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -r src/requirements.txt
   ```

3. Run the tests:
   ```bash
   pytest -v tests/
   ```


