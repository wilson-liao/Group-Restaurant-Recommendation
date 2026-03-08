import os
import sys
import subprocess

def main():
    print("--- Starting ForkSync Restaurant Recommendation System ---")
    
    # Path to the Streamlit app file
    app_path = os.path.join(os.path.dirname(__file__), 'app.py')
    
    if not os.path.exists(app_path):
        print(f"❌ Error: Could not find '{app_path}'")
        sys.exit(1)
        
    print("Launching Streamlit UI...")
    
    try:
        # Run the Streamlit application
        subprocess.run([sys.executable, "-m", "streamlit", "run", app_path], check=True)
    except KeyboardInterrupt:
        print("\nShutting down ForkSync...")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Streamlit process exited with error: {e}")
    except Exception as e:
        print(f"\n❌ An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()
