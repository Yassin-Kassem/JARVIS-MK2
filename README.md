# J.A.R.V.I.S MK2 🧠🤖
A modular, extensible Python-based virtual assistant inspired by Tony Stark’s J.A.R.V.I.S. system.  
This project provides a flexible framework for intelligent agent logic, prompt management, tool integration, and web search, designed for both experimentation and practical personal use.

---

## 🚀 Project Overview
**J.A.R.V.I.S MK2** is a virtual assistant built in Python that leverages modular components for:
- **Agent Logic** – Core decision-making and orchestration of tasks.
- **Prompt Management** – Centralized handling of LLM prompts.
- **Tool Integration** – Extendable tools for system tasks, display utilities, and external services.
- **Web Search** – Search capabilities with structured results.
- **Environment Configs** – Easily manage secrets and configs using `.env`.

This project is structured for clarity and scalability, making it simple to add new tools, modules, or integrations.

---

## ✨ Features
- 🧩 **Modular architecture** – Each component lives in its own folder for easy extension.
- 🔌 **Tool integration** – Add system, display, or custom tools seamlessly.
- 🌍 **Web search support** – Fetch live information directly via integrated search tools.
- 🗂️ **Prompt management** – Maintain and version your assistant’s prompt templates.
- 📝 **Logging system (KMS)** – Keep track of actions and outputs with structured logs.
- ⚙️ **Environment configuration** – Manage keys and secrets securely through `.env`.

---

## 🛠️ Installation

### Requirements
- **Python 3.10+**  
- `pip` for package management  
- Recommended: **virtualenv** or **conda** environment

### Steps
1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/J.A.R.V.I.S-MK2.git
   cd J.A.R.V.I.S-MK2
   
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate   # On Linux/Mac
   venv\Scripts\activate      # On Windows
3. Install dependancies
  ```bash
     pip install -r requirements.txt
  ```

### Usage
  ```bash
    python agent.py console
  ```

### Example Interaction 
  > Hello J.A.R.V.I.S
[Jarvis]: Good evening, Sir. How may I assist you today?

> Search for the latest Python release
[Jarvis]: The latest stable Python version is 3.13, released in October 2025.

### Environment Variables

This project uses .env for configuration.
Example .env file:
  # API keys
    OPENAI_API_KEY=your-openai-key-here
    SEARCH_API_KEY=your-search-key-here
