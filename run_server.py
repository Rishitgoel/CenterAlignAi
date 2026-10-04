"""
Launcher script for CentrAlign Mock Enterprise ERP System and Web Operator Portal.
Usage:
    python run_server.py
"""
import sys
import uvicorn

if __name__ == "__main__":
    print("=" * 60)
    print("Starting CentrAlign Mock Enterprise ERP & Portal")
    print("Web Portal: http://127.0.0.1:8000/portal")
    print("Swagger Docs: http://127.0.0.1:8000/docs")
    print("=" * 60)
    try:
        uvicorn.run("mock_erp.app:app", host="127.0.0.1", port=8000, reload=False, log_level="info")
    except KeyboardInterrupt:
        print("\nCentrAlign ERP server stopped.")
        sys.exit(0)
