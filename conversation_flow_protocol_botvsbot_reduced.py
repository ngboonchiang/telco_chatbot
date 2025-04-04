from dotenv import load_dotenv
import os
from langchain_groq import ChatGroq
from langchain_together import ChatTogether
from langchain.prompts import ChatPromptTemplate
import re
import json
from prompt_template import TELCO_USER_PROMPT, CONDITION_CHECK_PROMPTV2, CONDITION_CHECK_PROMPT, CUSTOMER_SERVICE_PROMPT, SUMMARY_PROMPT
import time
from generate_structured_knowledgebase import knowledge_base  # or paste your dict here
telcouserprompt = ChatPromptTemplate.from_template(TELCO_USER_PROMPT)
conditioncheckprompt = ChatPromptTemplate.from_template(CONDITION_CHECK_PROMPTV2)
customerserviceprompt = ChatPromptTemplate.from_template(CUSTOMER_SERVICE_PROMPT)
summaryprompt = ChatPromptTemplate.from_template(SUMMARY_PROMPT)

load_dotenv()
GROQ_API_KEY = os.environ["GROQ_API_KEY"]
TOGETHER_API_KEY = os.environ["TOGETHER_API_KEY"]

# Set up LLaMA model with memory
chat_groq = ChatGroq(
    temperature=0,
    top_p=1,
    groq_api_key=GROQ_API_KEY,
    model_name="llama-3.3-70b-versatile",
    max_tokens=5000,
)

chat_groq2 = ChatGroq(
    temperature=0,
    top_p=1,
    groq_api_key=GROQ_API_KEY,
    model_name="llama-3.3-70b-versatile",
    max_tokens=5000,
)

chat_together = ChatTogether(
    together_api_key=TOGETHER_API_KEY,
    model="deepseek-ai/DeepSeek-V3",
    temperature=0,
    top_p=1,
    max_tokens=5000,
    timeout=None,
    max_retries=2,
)

chat_together2 = ChatTogether(
    together_api_key=TOGETHER_API_KEY,
    model="deepseek-ai/DeepSeek-V3",
    temperature=0,
    top_p=1,
    max_tokens=5000,
    timeout=None,
    max_retries=2,
)


def extract_json(response):
    match = re.search(r'```json\n(.*?)\n```', response, re.DOTALL) # Lazy match JSON
    if match:
        json_str = match.group(1).strip()  # Extract and clean JSON string
        try:
            data = json.loads(json_str)  # Parse JSON
            return data
        except json.JSONDecodeError as e:
            print("Invalid JSON:", e)
    else:
        print("No JSON found in the text.")

    return None

def check_query_context(user_query, chat_history):
    """Check if the query depends on previous chat history."""
    
    prompt = f"""
    You are an AI assistant with memory. The user’s queries may be brief or contextually dependent on prior conversation history. 
    Analyze the latest query in relation to the conversation history and determine:  
    - If the latest query depends on prior context.  
    - If yes, extract the relevant details of the conversation and explain how this context relate to user query for context awareness purpose.  
    - If no, return 'NO'. 


    Return the output strictly in this JSON format:  
    {{
      "depends_on_context": "YES/NO",
      "relevant_context": "<summary or empty>",
      "how_context_relate_query": "<summary or empty>"
    }}

    language: same as the language of user query, either in english or mandarin
    Latest User Query: "{user_query}"  
    Conversation History: "{chat_history}"
    """

    print("\n\n")
    try:
        response = chat_groq.invoke(prompt)
    except Exception as e:
        print(f"Unexpected error: {e}")
        response = None

    try:
        #json_start = response.content.index("{")  # Find where JSON starts
        #print(response.content)
        #json_data = json.loads(response.content[json_start:])  # Parse JSON
        # Use regex to extract JSON content
        match = re.search(r'\{.*\}', response.content, re.DOTALL)

        if match:
            json_str = match.group()  # Extract JSON string
            try:
                json_data = json.loads(json_str)  # Convert to Python dictionary
                #print(json_data)  # Print extracted JSON
            except json.JSONDecodeError as e:
                print("Invalid JSON:", e)
        else:
            print("No JSON found in the text.")
        
        depends_on_context = json_data["depends_on_context"]
        relevant_context = json_data["relevant_context"]
        how_context_relate_query = json_data["how_context_relate_query"]

        #print("Depends on Context:", depends_on_context)
        #print("Relevant Context:", relevant_context)
        #print("How Context Relate to Query:", how_context_relate_query)
        print("\n\n")

    except json.JSONDecodeError:
        print("Error parsing JSON response")
    except ValueError:
        print("JSON not found in response")

    return depends_on_context, relevant_context, how_context_relate_query

def update_step_tracking(self_performed_data, step_status):
    """
    Updates step tracking dictionary with self-performed steps.
    
    Args:
        self_performed_data (dict): JSON response from LLM.
        step_status (dict): Dictionary tracking status of each troubleshooting step.

    Returns:
        dict: Updated step tracking dictionary.
    """
    for detected_step in self_performed_data["self_performed_steps"]:
        step_name = detected_step["step"]
        result = detected_step["result"].lower()

        if step_name in step_status:
            step_status[step_name]["mode"] = "self-performed"
            step_status[step_name]["result"] = result

    return step_status

def extract_steps2(troubleshooting_dict):
    """
    Extracts all troubleshooting steps and initializes their status with both mode and result.

    Args:
        troubleshooting_dict (dict): The dictionary containing troubleshooting steps.

    Returns:
        dict: A dictionary with each step mapped to a dict containing mode and result.
    """
    step_status = {
        step.lower(): {
            "mode": "none",  # Possible values: none, self-performed, agent-guided
            "result": "none"  # Possible values: none, success, failure, unclear
        } 
        for step in troubleshooting_dict.keys()
    }
    return step_status

def normalize(text):
    # Remove section numbers, emojis, symbols, extra whitespace
    text = re.sub(r'^\s*\w+(\.\w+)*\.?\s*', '', text)  # Remove leading "2A.1."
    text = re.sub(r'[^\w\s]', '', text)  # Remove emojis and punctuation
    return text.lower().strip()

def get_last_step(data):
    if len(data) < 2:
        return None  # Return None if there are less than 2 dictionaries
    return data[-1].get("step") 

def get_step_by_normalized_name(normalized_name, knowledge_base):
    """Find the actual step key from its normalized form."""
    for key in knowledge_base:
        if normalize(key) == normalized_name:
            return key
    return None

def extract_number(user_input):
    """ Extract the first number found in the input string """
    match = re.search(r'\d+', user_input)  # Find first number
    return int(match.group()) if match else None  # Convert to int if found, else None

def get_original_step(complete_step_tracking_reversed, user_input):
    user_choice = extract_number(user_input)  # Extract numeric part
    
    if user_choice is None:
        return "Wrong input format"  # No valid number found
    
    if 1 <= user_choice <= len(complete_step_tracking_reversed):
        return complete_step_tracking_reversed[user_choice - 1]["step"]  # Retrieve original step
    
    return "Number is out of range!" # Number is out of range

def find_step_index(complete_step_tracking_reversed, selected_step):
    """Finds the index of the selected step in the original list."""
    for idx, item in enumerate(complete_step_tracking_reversed):
        if item["step"] == selected_step:
            return idx  # Return the index of the selected step
    return None  # If not found, return None

def update_step_tracking(complete_step_tracking_reversed, selected_step):
    """Updates the list to include steps only up to the selected step."""
    step_index = find_step_index(complete_step_tracking_reversed, selected_step)
    
    if step_index is None:
        return "Step not found."  # Handle case where step does not exist
    
    return complete_step_tracking_reversed[:step_index + 1]  # Keep only steps up to selected one
def clean_step_names(complete_step_tracking_reversed):
    cleaned_steps = []

    for idx, item in enumerate(complete_step_tracking_reversed):
        cleaned_step = re.sub(r'^[\d\.a-zA-Z]+ ', '', item['step'])  # Remove leading numbering
        formatted_step = f"{idx + 1}. {cleaned_step}"  # New numbering
        cleaned_steps.append(formatted_step)

    return "\n".join(cleaned_steps)
# Step 1: Load your parsed knowledge_base (already generated)
# This should be generated by your parse_flexible_knowledge_base() function beforehand


# Step 2: Initialize the conversation
current_step = "0 Introduction & Issue Confirmation"
response_to_user = "How can I help you?"
print(f"Customer Service; {response_to_user}")

conversation_history = []
conversation_history_complete = []
step_tracking = []
complete_step_tracking_reversed = []
complete_step_tracking = []
step_status = extract_steps2(knowledge_base)
skip_key = 0
while True:
    if skip_key == 0:
        #user_input = input("User: ")
        message = telcouserprompt.format_messages(response_to_user=response_to_user,conversation_history=conversation_history)
        user_message = chat_groq.invoke(message[0].content)
        user_input = user_message.content
        print(f"User: {user_message.content}")
        time.sleep(5)
        depends_on_context, relevant_context, how_context_relate_query = check_query_context(user_input, conversation_history)
        print(f"context:{how_context_relate_query}")
        current_step = current_step.lower().replace("step ", "")
        matched_key = get_step_by_normalized_name(normalize(current_step), knowledge_base)
        
        if not matched_key:
            print("❌ Step not found. Ending conversation.")
            break
            
        step_data = knowledge_base.get(matched_key)
        

        # Extract step components for normal flow
        conditions = step_data.get("conditions_to_determine_next_step", [])
        condition_texts = [c["condition"] for c in conditions]
        steps_string = ""
        # Step 3: Use LLM to determine which condition (if any) matches the user input
        listofconditions={chr(10).join(f"- {c}" for c in condition_texts)}
        condition_check_prompt=conditioncheckprompt.format_messages(conversation_history=conversation_history,how_context_relate_query=how_context_relate_query,user_input=user_input,listofconditions=listofconditions)
        response = chat_together.invoke(condition_check_prompt[0].content)
        json_data = extract_json(response.content)
        matched_condition_raw=json_data["one_exact_matched_condition"]
        analysis_result=json_data["analysis_reasoning"]
        print(f"\n\nAnalysis:{analysis_result}\n\n")

        matched_condition = re.sub(r'^[\s\-\–\—\•\*]+', '', matched_condition_raw)
        print(f"\n🧠 Matched condition: {matched_condition}")

        # Step 4: Find the next step or remain in current step
        def normalize_condition(condition):
            return condition.lower().strip().lstrip("if ").strip()

        normalized_matched_condition = normalize_condition(matched_condition)

        matched = next(
        (c for c in conditions if normalize_condition(c["condition"]) == normalized_matched_condition),
        None
        )
        #matched = next((c for c in conditions if c["condition"].lower() == matched_condition.lower()), None)
    
    if matched and matched["next_step"].lower() != "remain" and matched["next_step"].lower() != "step remain":
        if matched["next_step"].lower() == "step proceed to previous step":
            complete_step_data = {
                "step": current_step,              # Replace with your current_step value
                "mode": "customer guide",         # Replace with your mode (e.g., "manual", "auto")
                "condition_met": matched["next_step"].lower(),  # Replace with your condition status (True/False)
                "next step": matched["next_step"].lower()
            }
            complete_step_tracking.append(complete_step_data)
            previous_distinct_step = get_last_step(complete_step_tracking_reversed)
            complete_step_tracking_reversed = complete_step_tracking_reversed[:-1]
            current_step = previous_distinct_step.lower().replace("step ", "")
            print(f"➡️ Moving to previous step: {current_step}")
        elif matched["next_step"].lower() == "step 51 close the chat":
            print("Chat ending!")
            break
        elif matched["next_step"].lower() == "step revisit previous step":
            second_last_step=complete_step_tracking_reversed[-2]['step']
            if normalize(second_last_step) != "escalation":
                matched_key = get_step_by_normalized_name(normalize(second_last_step), knowledge_base)
                second_last_step_data = knowledge_base.get(matched_key, {})
                new_step = second_last_step_data['conditions_to_determine_next_step'][0]['next_step']
                new_step_reformatted = new_step.lower().replace("step ", "")
                complete_step_data_temp = {
                    "step": new_step_reformatted,              # Replace with your current_step value
                    "mode": "customer guide",         # Replace with your mode (e.g., "manual", "auto")
                    "condition_met": "",   # Replace with your condition status (True/False)
                    "next step": ""
                }
                complete_step_tracking_reversed_temp = complete_step_tracking_reversed + [complete_step_data_temp] 
                steps_string = clean_step_names(complete_step_tracking_reversed_temp)
            else:
                complete_step_tracking_reversed_temp = complete_step_tracking_reversed 
                steps_string = clean_step_names(complete_step_tracking_reversed_temp)
            
            response_to_user =f"Please key in the NUMBER of following step which you would like to revisit:\n\n List of Previous Steps:\n{steps_string}"
            print(response_to_user)
            message = telcouserprompt.format_messages(response_to_user=response_to_user,conversation_history=conversation_history)
            user_message = chat_groq.invoke(message[0].content)
            user_input = user_message.content
            print(f"User: {user_message.content}")
            #user_input = input("User: ")
            response = get_original_step(complete_step_tracking_reversed, user_input)
            if response == "Number is out of range!" or response == "Wrong input format":
                conversation_history.append({"role": "customer service", "content": response_to_user})
                conversation_history.append({"role": "user", "content": user_input})
                time.sleep(15)
                skip_key = 1
                continue
            else:
                current_step = response
                complete_step_tracking_reversed = update_step_tracking(complete_step_tracking_reversed, current_step)
                skip_key = 0
                
        else:
            next_step = matched["next_step"].lower()
            print(f"➡️ Moving to next step: {next_step}")
            
            complete_step_data = {
                "step": current_step,              # Replace with your current_step value
                "mode": "customer guide",         # Replace with your mode (e.g., "manual", "auto")
                "condition_met": matched["next_step"].lower(),   # Replace with your condition status (True/False)
                "next step": matched["next_step"].lower()
            }
            complete_step_tracking.append(complete_step_data)
            complete_step_tracking_reversed.append(complete_step_data)
            current_step = next_step
            current_step = current_step.lower().replace("step ", "")

        matched_key = get_step_by_normalized_name(normalize(current_step), knowledge_base)
        step_data = knowledge_base.get(matched_key, {})
    else:
        print("⏳ Staying in current step (condition not matched or unclear).")

    # Step 5: Ask LLM to generate a reply based on data and approaches
    data_to_collect = step_data.get("data_to_collect_from_user", "")
    approaches = step_data.get("approaches_for_llm_to_collect_data", step_data.get("approaches_for_closing_chat", []))
    listofapproaches={chr(10).join(f"- {a}" for a in approaches)}
    if normalize(current_step) == "summary":
        listofsteps=clean_step_names(complete_step_tracking_reversed)
        conversation_history = conversation_history_complete
        guidance_prompt=summaryprompt.format_messages(conversation_history=conversation_history,user_input=user_input,listofsteps=listofsteps)
    else:
        guidance_prompt=customerserviceprompt.format_messages(conversation_history=conversation_history,how_context_relate_query=how_context_relate_query,user_input=user_input,data_to_collect=data_to_collect,listofapproaches=listofapproaches)

    reply = chat_groq.invoke(guidance_prompt[0].content)

    response_to_user = reply.content
    print(f"\nCustomer Service: {response_to_user}")

    # Update conversation history
    conversation_history_complete.append({"role": "user", "content": user_input})
    conversation_history_complete.append({"role": "customer service", "content": response_to_user})
    step_tracking.append(current_step)
    conversation_history = conversation_history_complete[-10:]