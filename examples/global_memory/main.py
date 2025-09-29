import subprocess
import sys
import os


def main():
    """Run the Streamlit application"""
    print("Starting TiDB Memory Chatbot...")
    print("Make sure to configure your .env file before running!")
    print("See .env.example for configuration options.\n")

    # Check if .env file exists
    if not os.path.exists(".env"):
        print("⚠️  Warning: .env file not found!")
        print("Please copy .env.example to .env and configure your API keys.\n")

    try:
        # Run streamlit
        subprocess.run([sys.executable, "-m", "streamlit", "run", "app.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running Streamlit: {e}")
        print("Make sure all dependencies are installed: uv install")
    except KeyboardInterrupt:
        print("\nApplication stopped by user.")


if __name__ == "__main__":
    main()
