from dotenv import load_dotenv
import os
from langchain_groq import ChatGroq
from langchain_together import ChatTogether
import re
import json

load_dotenv()
GROQ_API_KEY = os.environ["GROQ_API_KEY"]
TOGETHER_API_KEY = os.environ["TOGETHER_API_KEY"]

# Set up LLaMA model with memory
chat_groq = ChatGroq(
    temperature=0.5,
    groq_api_key=GROQ_API_KEY,
    model_name="llama-3.3-70b-versatile",
    max_tokens=5000,
)

chat_groq2 = ChatGroq(
    temperature=0.5,
    groq_api_key=GROQ_API_KEY,
    model_name="llama-3.3-70b-versatile",
    max_tokens=5000,
)

chat_together = ChatTogether(
    together_api_key=TOGETHER_API_KEY,
    model="deepseek-ai/DeepSeek-V3",
    #model="meta-llama/Llama-3.3-70B-Instruct-Turbo",
    temperature=0.5,
    max_tokens=5000,
    timeout=None,
    max_retries=2,
)

chat_together2 = ChatTogether(
    together_api_key=TOGETHER_API_KEY,
    model="deepseek-ai/DeepSeek-V3",
    #model="meta-llama/Llama-3.3-70B-Instruct-Turbo",
    temperature=0.5,
    max_tokens=5000,
    timeout=None,
    max_retries=2,
)

def update_step_tracking(self_performed_data, step_status):
    """
    Updates step tracking dictionary with self-performed steps if the result is 'failure'.
    
    Args:
        self_performed_data (dict): JSON response from LLM.
        step_status (dict): Dictionary tracking status of each troubleshooting step.

    Returns:
        dict: Updated step tracking dictionary.
    """
    for detected_step in self_performed_data["self_performed_steps"]:
        step_name = detected_step["step"]
        result = detected_step["result"].lower()

        if step_name in step_status and result == "failure":
            step_status[step_name] = "self performed"

    return step_status

def extract_steps(troubleshooting_dict):
    """
    Extracts all troubleshooting steps and initializes their status as 'none'.

    Args:
        troubleshooting_dict (dict): The dictionary containing troubleshooting steps.

    Returns:
        dict: A dictionary with each step mapped to "none" as the initial status.
    """
    step_status = {step: "none" for step in troubleshooting_dict.keys()}
    return step_status

def detect_self_performed_steps(user_input, conversation_history, all_possible_steps):
    """
    Calls LLM to check if the user has self-tested any troubleshooting steps.
    
    Args:
        user_input (str): The latest message from the user.
        conversation_history (list): List of previous conversation exchanges.
        all_possible_steps (list): A list of all known troubleshooting steps.
        chat_groq (ChatGroq): LLM model instance for generating responses.

    Returns:
        dict: JSON response containing detected self-performed steps and their results.
    """
    prompt = f"""
    You are a telco troubleshooting assistant.

    Chat History: "{conversation_history}"

    User's latest message:
    "{user_input}"

    Known troubleshooting steps:
    {chr(10).join(f"- {s}" for s in all_possible_steps)}

    Task:
    1. Identify any troubleshooting steps that the user has mentioned they have already performed by themselves.
    2. If a step is detected, determine the outcome/result of the step (success, failure, unclear).
    3. Respond strictly in JSON format as follows:

    ```json
    {{
        "self_performed_steps": [
            {{
                "step": "<step_name>",
                "result": "<success/failure/unclear>"
            }}
        ]
    }}
    ```

    If no self-performed step is detected, return:
    ```json
    {{
        "self_performed_steps": []
    }}
    ```

    Strictly follow the JSON format. Do not include any explanations or extra text.
    """

    response = chat_groq.invoke(prompt)
    match = re.search(r'\{.*\}', response.content, re.DOTALL)
    if match:
        json_str = match.group()  # Extract JSON string
        try:
            self_performed_data = json.loads(json_str)  # Convert to Python dictionary
            #print(json_data)  # Print extracted JSON
        except json.JSONDecodeError as e:
            print("Invalid JSON:", e)
            self_performed_data = {"self_performed_steps": []} 
    else:
        print("No JSON found in the text.")
        self_performed_data = {"self_performed_steps": []} 

    return self_performed_data




def normalize(text):
    # Remove section numbers, emojis, symbols, extra whitespace
    text = re.sub(r'^\s*\w+(\.\w+)*\.?\s*', '', text)  # Remove leading "2A.1."
    text = re.sub(r'[^\w\s]', '', text)  # Remove emojis and punctuation
    return text.lower().strip()

def get_previous_distinct_step(step_tracking):
    if len(step_tracking) < 2:
        return None  # Not enough history to compare

    current = step_tracking[-1]
    
    # Iterate backwards through the list (excluding the current step itself)
    for prev_step in reversed(step_tracking[:-1]):
        if prev_step != current:
            return prev_step

    return None  # All previous steps are the same as current

# Step 1: Load your parsed knowledge_base (already generated)
# This should be generated by your parse_flexible_knowledge_base() function beforehand
from generate_structured_knowledgebase import knowledge_base  # or paste your dict here

# Step 2: Initialize the conversation
current_step = "0 Introduction & Issue Confirmation"
print("Customer Service: How can I help you?")

conversation_history = []
step_tracking = []
step_tracking.append(current_step)

while True:
    user_input = input("User: ")


    #check if any steps have already performed by user but unsuccessful, update the step_status
    step_status = extract_steps(knowledge_base)
    all_possible_steps=list(step_status.keys())
    self_performed_data = detect_self_performed_steps(user_input, conversation_history, all_possible_steps)
    step_status = update_step_tracking(self_performed_data, step_status)

    # Retrieve step info
    current_step = current_step.replace("Step ", "")
    # Find matching key in the dict
    matched_key = None
    for key in knowledge_base:
        if normalize(key) == normalize(current_step):
            matched_key = key
            break
    step_data = knowledge_base.get(matched_key)
    if not step_data:
        print("❌ Step not found. Ending conversation.")
        break

    # Extract step components
    conditions = step_data.get("conditions_to_determine_next_step", [])
    condition_texts = [c["condition"] for c in conditions]

    # Step 3: Use GPT to determine which condition (if any) matches the user input
    condition_check_prompt = f"""
    You are a telco troubleshooting assistant.

    Chat History: \"{conversation_history}\"
    User message:
    \"{user_input}\"

    Known conditions:
    {chr(10).join(f"- {c}" for c in condition_texts)}

    Respond ONLY with the matched condition exactly as listed above. If none are matched, say "remain".
    """

    response = chat_groq.invoke(condition_check_prompt)
    
    matched_condition = re.sub(r'^[\s\-\–\—\•\*]+', '', response.content)
    print(f"\n🧠 Matched condition: {matched_condition}")


    # Step 4: Find the next step or remain in current step
    matched = next((c for c in conditions if c["condition"].lower() == matched_condition), None)
    
    if matched and matched["next_step"].lower() != "remain" and matched["next_step"].lower() != "step remain":
        if matched["next_step"] == "Step proceed to previous step":
            previous_distinct_step = get_previous_distinct_step(step_tracking)
            current_step = previous_distinct_step.replace("Step ", "")
            print("➡️ Moving to previous step: {current_step}")
        else:
            next_step = matched["next_step"]
            print(f"➡️ Moving to next step: {next_step}")
            current_step = next_step
            current_step = current_step.replace("Step ", "")
        matched_key = None
        for key in knowledge_base:
            if normalize(key) == normalize(current_step):
                matched_key = key
                break
        step_data = knowledge_base.get(matched_key, {})
    else:
        print("⏳ Staying in current step (condition not matched or unclear).")

    # Step 5: Ask GPT to generate a reply based on data and approaches
    data_to_collect = step_data.get("data_to_collect_from_user", "")
    approaches = step_data.get("approaches_for_llm_to_collect_data", step_data.get("approaches_for_closing_chat", []))

    guidance_prompt = f"""
    You are a telco customer support agent helping someone troubleshoot slow data issues.

    Chat History: \"{conversation_history}\"
    Please help the user based on:
    Goal: {data_to_collect}

    Given Approaches:
    {chr(10).join(f"- {a}" for a in approaches)}

    Give a helpful, conversational reply to the user guiding them on what to do next based on the given approaches. 
    Acknowledge User Responses Before Asking for More Information.
    Select the Appropriate Approach from the protocol Based on User’s Response. No restriction on how many approaches to be applied at a time.
    Keep your response concise and straight to the point.
    """

    reply = chat_groq.invoke(guidance_prompt)

    final_response = reply.content
    print(f"\nCustomer Service: {final_response}")

    # Update conversation history
    conversation_history.append({"role": "user", "content": user_input})
    conversation_history.append({"role": "customer service", "content": final_response})
    step_tracking.append(current_step)
    conversation_history = conversation_history[-10:]
