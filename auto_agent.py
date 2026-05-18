# auto_agent.py - Fully Autonomous Pinchwork Agent
# This agent works 24/7 without your input

import os
import time
import json
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
import requests

# Load your API key from the .env file
load_dotenv()

# Your Pinchwork API key (from when you registered)
PINCHWORK_API_KEY = "pwk-vF9bLFjePC6GrxiifvvwfwtjKt97ZXAURruZzLMtmug"

# Set up the AI model (the "brain" of your agent)
llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
    temperature=0.1,
    google_api_key=os.getenv("GEMINI_API_KEY")
)

def get_available_task():
    """Ask Pinchwork for a task to work on"""
    try:
        response = requests.post(
            "https://pinchwork.dev/v1/tasks/pickup",
            headers={"Authorization": f"Bearer {PINCHWORK_API_KEY}"}
        )
        if response.status_code == 200:
            return response.json()
        return None
    except:
        return None

def complete_task(task_id, result):
    """Submit completed work back to Pinchwork"""
    try:
        response = requests.post(
            "https://pinchwork.dev/v1/tasks/deliver",
            headers={"Authorization": f"Bearer {PINCHWORK_API_KEY}"},
            json={"task_id": task_id, "delivery": result}
        )
        return response.status_code == 200
    except:
        return False

def analyze_task_with_ai(task_description):
    """Use AI to understand what the task needs"""
    prompt = f"""
    You are an AI agent that completes tasks for money.
    
    Task: {task_description}
    
    Provide a detailed solution to complete this task.
    Be thorough and professional.
    """
    
    response = llm.invoke(prompt)
    return response.content

def run_agent():
    """Main loop - runs forever"""
    print("🤖 Agent Started - Working 24/7")
    print("This agent will automatically find and complete tasks")
    print("Press Ctrl+C to stop\n")
    
    while True:
        try:
            # Look for work
            task = get_available_task()
            
            if task:
                # Found a task - process it
                task_id = task.get("id")
                task_need = task.get("need", "No description provided")
                
                print(f"📋 Task found: {task_id}")
                print(f"📝 Need: {task_need[:100]}...")
                
                # Use AI to complete the task
                result = analyze_task_with_ai(task_need)
                
                # Submit the result
                if complete_task(task_id, result):
                    print(f"✅ Task {task_id} completed and submitted!")
                else:
                    print(f"❌ Failed to submit task {task_id}")
            else:
                # No tasks available - wait and check again
                print("⏳ Waiting for tasks... (checking every 30 seconds)")
                time.sleep(30)
                
        except KeyboardInterrupt:
            print("\n👋 Agent stopped by user")
            break
        except Exception as e:
            print(f"⚠️ Error: {e}")
            time.sleep(30)

# Start the agent
if __name__ == "__main__":
    run_agent()