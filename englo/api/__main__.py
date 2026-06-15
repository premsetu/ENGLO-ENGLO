"""Run the API server: python -m englo.api"""

import os
import uvicorn

if __name__ == "__main__":
    # Cloud hosts (Render, Railway, Fly, Heroku) inject $PORT; honour it first.
    port = int(os.getenv("PORT") or os.getenv("API_PORT", "8000"))
    uvicorn.run(
        "englo.api.app:app",
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=port,
        reload=os.getenv("API_RELOAD", "false").lower() == "true",
    )
