# Troubleshooting Guide

This guide provides solutions to common issues encountered during the setup and operation of the Cross-Market Arbitrage Tool.

## 1. Database Issues

### 1.1 MongoDB: E11000 duplicate key error on asin field

- **Symptom:** `E11000 duplicate key error collection: arbitrage_tool.products index: asin_1 dup key: { asin: null }`
- **Cause:** The MongoDB collection has a unique index on the `asin` field, but many MediaMarkt products don't have ASINs (null values). MongoDB's unique indexes don't allow multiple null values by default.
- **Solution:** Update the index to use a partial filter expression that only indexes non-null ASINs:
    ```python
    # In src/config/database.py, the index should be:
    await database.products.create_index(
        "asin", 
        unique=True, 
        partialFilterExpression={"asin": {"$exists": True, "$type": "string"}}
    )
    ```
- **Quick Fix:** If you encounter this error, the index configuration has been updated. Restart your scraping process and it should work correctly.

## 2. Connection & Networking Issues

### 2.1 MongoDB: SSL Certificate Verification Failed

- **Symptom:** `pymongo.errors.ServerSelectionTimeoutError: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed`
- **Cause:** The local environment (especially on macOS) may not have the required root certificates for MongoDB Atlas's SSL chain.
- **Solution:**
    1.  **Install CA Certificates:** Ensure you have the latest certificate authorities.
        ```bash
        brew install ca-certificates
        ```
    2.  **Temporary Fix (for local development only):** In `src/config/database.py`, you can temporarily relax SSL verification by setting `tlsAllowInvalidCertificates=True`.
        ```python
        # src/config/database.py
        mongo_client = AsyncIOMotorClient(
            settings.DATABASE_URL,
            tls=True,
            tlsAllowInvalidCertificates=True # NOT for production
        )
        ```
    3.  **Production Fix:** Ensure the deployment environment has up-to-date CA certificates. Refer to your hosting provider's documentation for managing trust stores.

### 2.2 FastAPI / Streamlit: Connection Refused or Not Starting

- **Symptom:** `curl: (7) Failed to connect to localhost port 8000: Connection refused` or the service fails to start.
- **Cause:** This can be due to several issues, most commonly configuration errors or port conflicts.
- **Troubleshooting Steps:**
    1.  **Check for Port Conflicts:** Ensure ports `8000` (FastAPI) and `8501` (Streamlit) are not in use by another application.
        ```bash
        lsof -i :8000
        lsof -i :8501
        ```
    2.  **Check for Startup Errors:** Run the application in the foreground to see detailed error messages.
        ```bash
        # For FastAPI
        python3 src/main.py

        # For Streamlit
        streamlit run src/dashboard/main.py
        ```
    3.  **Review Configuration:** An `AttributeError` on startup (e.g., `'Settings' object has no attribute 'DEBUG'`) points to a missing variable in your `.env` file or `src/config/settings.py`. Ensure all required settings are present.

### 2.3 Telegram: Chat Not Found

- **Symptom:** Telegram API returns `{"ok":false,"error_code":400,"description":"Bad Request: chat not found"}`.
- **Cause:** The bot cannot initiate a conversation with a user. The user must message the bot first.
- **Solution:**
    1.  Open Telegram and search for your bot (e.g., `@ShemsyMediaBot`).
    2.  Send a `/start` message or any other text to the bot.
    3.  This action creates the chat session, and the bot will now be able to send messages to that `chat_id`.

## 3. Python & Module Errors

### 3.1 `ModuleNotFoundError: No module named 'src'`

- **Symptom:** Occurs when running Streamlit or other scripts from the project root.
- **Cause:** The script's execution path does not include the project's root directory, so it cannot find the `src` module.
- **Solution:** Add the project root to `sys.path` at the beginning of the script.
    ```python
    # src/dashboard/main.py
    import sys
    from pathlib import Path

    # Add project root to Python path
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))

    # ... rest of the script
    ```

### 3.2 `ImportError: cannot import name '...'`

- **Symptom:** `ImportError: cannot import name 'render_alerts_table' from 'src.dashboard.components.alerts'`.
- **Cause:** This typically happens when the `import` statement is trying to import a function that doesn't exist, often because the component was refactored into a class.
- **Solution:**
    1.  **Inspect the Module:** Open the file mentioned in the error (e.g., `src/dashboard/components/alerts.py`).
    2.  **Identify the Class:** Look for a class definition (e.g., `class AlertsTable:`).
    3.  **Update the Import:** In the file that has the error, change the import from the function to the class.
        ```python
        # Before
        from src.dashboard.components.alerts import render_alerts_table

        # After
        from src.dashboard.components.alerts import AlertsTable
        ```
    4.  **Update the Call:** Find where the old function was called and replace it with class instantiation and a call to its `render` method.
        ```python
        # Before
        render_alerts_table(data_loader)

        # After
        alerts_table = AlertsTable(data_loader)
        alerts_table.render()
        ```

## 4. Configuration & Settings Errors

### 4.1 `AttributeError: 'Settings' object has no attribute '...'`

- **Symptom:** Application fails on startup with an error like `AttributeError: 'Settings' object has no attribute 'DEBUG'`.
- **Cause:** The code is trying to access a setting (e.g., `settings.DEBUG`) that is not defined in the `Settings` class in `src/config/settings.py`.
- **Solution:**
    1.  Open `src/config/settings.py`.
    2.  Add the missing attribute to the `Settings` class with its correct type hint and a default value if applicable.
        ```python
        class Settings(BaseSettings):
            # ... other settings
            DEBUG: bool = False
        ```
    3.  Ensure the corresponding variable is set in your `.env` file if it doesn't have a default.

## 5. General Debugging Flow

1.  **Read the Error Message Carefully:** The traceback usually points to the exact file and line number causing the problem.
2.  **Run Services in Foreground:** Always run `uvicorn` and `streamlit` directly in your terminal first to see live error output.
3.  **Check the `.env` file:** Ensure all required environment variables are present and have correct values.
4.  **Test Components in Isolation:** Use the `test_end_to_end.py` script or run small, targeted scripts to validate individual parts of the system (like database or Redis connections).
5.  **Check `git status`:** Make sure you haven't accidentally modified a file that is causing the issue.
6.  **Restart Processes:** After making a fix, always kill the old process (`pkill -f uvicorn`) and restart it to ensure your changes are loaded. 