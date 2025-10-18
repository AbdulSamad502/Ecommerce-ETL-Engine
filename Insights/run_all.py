import os
import subprocess
import pyttsx3

def speak(msg):
    engine = pyttsx3.init()  # Initialize engine every time
    engine.say(msg)
    engine.runAndWait()
    engine.stop()  # Stop engine after speaking

# Folder where scripts are
script_folder = "C:/Users/ABDUL SAMAD/Documents/Ecom_Analysis/Insights"

scripts = [
    ("data_cleaning.py", "Sir, Data cleaning is completed"),
    ("data_analyzing.py", "Data analysis is Done"),
    ("charts.py", "Charts generation is Done"),
    ("conclusion.py", "PDF report is generated")
]
start_message = "the Ecom Analysis Engine is starting now."
print(start_message)
speak(start_message)

for script, message in scripts:
    full_path = os.path.join(script_folder, script)
    # Run the script and wait until it finishes
    result = subprocess.run(["python", full_path])
    
    if result.returncode == 0:
        speak(message)  # Voice confirmation after each script
    else:
        speak(f"Sir,There is an Error Found in {script}")
end_massage= "Thankyou  for using me Sir. Have a nice day."
speak(end_massage)