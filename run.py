import uvicorn
import os
from dotenv import load_dotenv

if __name__ == "__main__":
    load_dotenv() # Ensure environment variables like API_HOST/PORT are loaded if needed here
    api_host = os.getenv("API_HOST", "0.0.0.0")
    api_port = int(os.getenv("API_PORT", "8000"))

    # You can add --reload logic here if needed, but start simple
    uvicorn.run("app.main:app", host=api_host, port=api_port, reload=True)
    # For testing without reload first:
    # uvicorn.run("app.main:app", host=api_host, port=api_port, reload=False) 