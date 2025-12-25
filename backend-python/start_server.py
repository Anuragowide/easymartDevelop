"""
Simple script to start the Easymart Assistant server
"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8088,
        reload=False,  # Disable reload for testing
        log_level="info"
    )
