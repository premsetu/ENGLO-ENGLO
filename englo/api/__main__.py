"""Run the API server: python -m englo.api"""

import os
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "englo.api.app:app",
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", "8000")),
        reload=os.getenv("API_RELOAD", "true").lower() == "true",
    )
