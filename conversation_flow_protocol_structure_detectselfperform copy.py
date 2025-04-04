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
    temperature=0.5,
    max_tokens=5000,
    timeout=None,
    max_retries=2,
)

chat_together2 = ChatTogether(
    together_api_key=TOGETHER_API_KEY,
    model="deepseek-ai/DeepSeek-V3",
    temperature=0.5,
    max_tokens=5000,
    timeout=None,
    max_retries=2,
)

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

def detect_self_performed_steps(user_input, conversation_history, all_possible_steps, how_context_relate_query):
    """
    Calls LLM to check if the user has self-tested any troubleshooting steps without customer service guidance.

    Returns:
        dict: JSON response containing detected self-performed steps and their results.
    """
    prompt = f"""
    You are a telco troubleshooting assistant.

    Context: {how_context_relate_query}

    User's latest message:
    "{user_input}"

    Known troubleshooting steps:
    {chr(10).join(f"- {s}" for s in all_possible_steps)}
 
    **Task:**  
    1. **Strictly identify only those troubleshooting steps that the user has EXPLICITLY and DIRECTLY mentioned.**  
       - The user must have CLEARLY stated that they performed the step.  
       - DO NOT assume or infer steps based on vague wording, implications, or indirect hints.  
       - If there is any uncertainty or ambiguity, DO NOT include the step.  
   
    2. **Ensure all of the following conditions are met before including a step:**  
       - The user has **clearly and explicitly** stated performing the step.  
       - The user’s statement **strongly and directly** matches a troubleshooting step from the known list.  
       - The user provides a **clear result/effect** of the step (e.g., "it didn't work," "issue still persists").  
       - If the user’s wording is unclear, vague, or indirect, the step **must be excluded**.  

    3. **Differentiate between 'Reinserting SIM' and 'Changing SIM':**  
       - *Reinserting SIM* = The user **removed and put back the SAME SIM card**.  
       - *Changing SIM* = The user **bought a new SIM and replaced the old one**.  
       - **Do NOT classify ‘Changing SIM’ as ‘Reinserting SIM’** unless the user explicitly confirms they removed and reinserted the same SIM.

    4.  Follow steps below to identify the matched troubleshooting step:
        - check if there is any step mentioned by user.
        - if yes, analyze if it fulfiled criteria above and if it matches any of the troubleshooting step
        - only detect matched troubleshooting step that fulfil all criteria
        - Based on user input and context provided above, check if curtomer service has suggested or questioned similar step

    5. **For each detected step that fulfiled above criteria, provide:
       - **Exact troubleshooting step name** (e.g. 2b refresh the network connection  ).  
       - **Result** as stated by the user. if result is not explicitly mentioned, return 'none' for result.
       - **if this step has been suggested or questioned by customer service**
       - **Analysis** explaining how the step meets all the strict conditions in (2).  

    6. **Strict Filtering Rules:**  
       - **Do NOT assume intent**—only return steps with direct confirmation.  
       - **Do NOT infer steps from vague statements or implications.**  
       - **If a step does not fully satisfy the strict criteria, do not return it.**  

    7. **Response Format (Strict JSON), example:**  

    ```json
    {{
        "self_performed_steps": [
            {{
                "step": "<step name>",
                "result": "<description/none>",
                "as suggested": "<yes/no>",
                "analysis": "<description>"
            }},
            {{
                "step": "<step name>",
                "result": "<description/none>",
                "as suggested": "<yes/no>",
                "analysis": "<description>"
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
        except json.JSONDecodeError as e:
            print("Invalid JSON:", e)
            self_performed_data = {"self_performed_steps": []} 
    else:
        print("No JSON found in the text.")
        self_performed_data = {"self_performed_steps": []} 

    if self_performed_data['self_performed_steps'] and isinstance(self_performed_data, dict):
        if self_performed_data['self_performed_steps'][0]['as suggested'] == 'yes' or self_performed_data['self_performed_steps'][0]['result']=='none':
            self_performed_data = {"self_performed_steps": []} 
            

    return self_performed_data

def find_failed_condition_match(step_data, user_input, conversation_history, current_step_status):
    """
    Identifies which condition matches the user's failed attempt for the current step.
    
    Args:
        step_data (dict): Current step data containing conditions.
        user_input (str): The latest message from the user.
        conversation_history (list): List of previous conversation exchanges.
        
    Returns:
        str: The matching condition for failure, or None if no match.
    """
    conditions = step_data.get("conditions_to_determine_next_step", [])
    condition_texts = [c["condition"] for c in conditions]
    
    # Skip if there are no conditions to check
    if not condition_texts:
        return None
    
    # Get matching condition for failure scenario
    failure_check_prompt = f"""
    You are a telco troubleshooting expert analyzing the result of a user's attempt.

    Chat History: \"{conversation_history}\"
    Current user message:
    \"{user_input}\"
    Description of result: {current_step_status['result']}

    In the conversation, user has mentioned that they already attempted the current troubleshooting step.
    Based on the description of the test result, which of following conditions best describes their outcome?

    Known conditions:
    {chr(10).join(f"- {c}" for c in condition_texts)}

    Respond ONLY with the matched condition that best describes the result, exactly as listed above.
    Choose the condition that would determine what troubleshooting step should come next after this failure.
    If none match, say "remain".
    """

    response = chat_groq.invoke(failure_check_prompt)
    matched_condition = re.sub(r'^[\s\-\–\—\•\*]+', '', response.content)
    print(f"\n🔍 Matched condition: {matched_condition}")
    
    return matched_condition

def normalize(text):
    # Remove section numbers, emojis, symbols, extra whitespace
    text = re.sub(r'^\s*\w+(\.\w+)*\.?\s*', '', text)  # Remove leading "2A.1."
    text = re.sub(r'[^\w\s]', '', text)  # Remove emojis and punctuation
    return text.lower().strip()

def get_last_step(data):
    if len(data) < 2:
        return None  # Return None if there are less than 2 dictionaries
    return data[-1].get("step") 


    
    # Iterate backwards through the list (excluding the current step itself)
    for prev_step in reversed(step_tracking[:-1]):
        if prev_step != current:
            return prev_step

    return None  # All previous steps are the same as current

def check_current_step_self_tested(current_step, step_status):
    """
    Check if the current step has already been attempted by the user.
    
    Args:
        current_step (str): The current step name.
        step_status (dict): Dictionary tracking status of each troubleshooting step.
        
    Returns:
        bool: True if the step has been attempted and failed, False otherwise.
    """
    normalized_current = normalize(current_step)
    
    for step, status in step_status.items():
        if normalize(step) == normalized_current and status['mode'] == "self-performed":
            return True
    
    return False

def get_step_by_normalized_name(normalized_name, knowledge_base):
    """Find the actual step key from its normalized form."""
    for key in knowledge_base:
        if normalize(key) == normalized_name:
            return key
    return None

# Step 1: Load your parsed knowledge_base (already generated)
# This should be generated by your parse_flexible_knowledge_base() function beforehand
from generate_structured_knowledgebase import knowledge_base  # or paste your dict here

# Step 2: Initialize the conversation
current_step = "0 Introduction & Issue Confirmation"
print("Customer Service: How can I help you?")

conversation_history = []
step_tracking = []
complete_step_tracking_reversed = []
complete_step_tracking = []
step_status = extract_steps2(knowledge_base)

while True:
    user_input = input("User: ")


    depends_on_context, relevant_context, how_context_relate_query = check_query_context(user_input, conversation_history)

    # Check if any steps have already performed by user but unsuccessful, update the step_status
    all_possible_steps = [key.lower() for key in step_status.keys()]
    self_performed_data = detect_self_performed_steps(user_input, conversation_history[-2:] , all_possible_steps, how_context_relate_query)
    step_status = update_step_tracking(self_performed_data, step_status)
    print(self_performed_data)
    print(how_context_relate_query)
    # Get current step data
    #current_step = current_step.replace("Step ", "")
    current_step = current_step.lower().replace("step ", "")
    matched_key = get_step_by_normalized_name(normalize(current_step), knowledge_base)
    
    if not matched_key:
        print("❌ Step not found. Ending conversation.")
        break
        
    step_data = knowledge_base.get(matched_key)
    

     # Extract step components for normal flow
    conditions = step_data.get("conditions_to_determine_next_step", [])
    condition_texts = [c["condition"] for c in conditions]

    # Step 3: Use LLM to determine which condition (if any) matches the user input
    condition_check_prompt = f"""
    You are a telco troubleshooting assistant. We are trying to collect data from the user's response and analyze if the data meets any of the condition below.


    Chat History: \"{conversation_history}\"
    Context: {how_context_relate_query}
    User message:
    \"{user_input}\"

    Analyze following conditions one by one and check if it closely matches the User’s Response:
    {chr(10).join(f"- {c}" for c in condition_texts)}

   1) Return a matched condition ONLY if:
   - There is EXPLICIT mention of the key elements in the condition
   - The user's response contains SPECIFIC TERMINOLOGY that directly addresses the condition
   - You can identify CLEAR TEXT EVIDENCE in the user's exact words that satisfies the condition
   - The match is based on STATED FACTS, not potential implications

    2) For telco-specific matching:
    - Distinguish clearly between device issues, app issues, account issues, and network issues
    - Geographical references (home, work, different locations) must be EXPLICITLY mentioned to match location-based conditions
    - Technical symptoms must be SPECIFICALLY described to match technical conditions
    - Timing patterns must be CLEARLY STATED to match time-based conditions

    3) IMPORTANT: If the user's response does not EXPLICITLY satisfy a condition:
    - Return "remain" without exception
    - Do not attempt to infer implied information
    - Do not match based on what might be "probably" true
    - When in doubt, always default to "remain"

    4) Examples of non-matching scenarios:
    - User: "All my apps are affected" does NOT match "issue persists across geographical locations"
    - User: "It's slow on my phone" does NOT match "issue affects all devices"
    - User: "It stopped working yesterday" does NOT match "issue is intermittent"

    5) Pay careful attention to DEGREE and MAGNITUDE descriptors:
   - Degree and magnitude (slightly, somewhat, significantly, a lot, completely) must match
   - "Improves slightly" does NOT match conditions requiring "improves a lot"
   - "Sometimes" does NOT match conditions requiring "always" or "consistently"
   - "A few" does NOT match conditions requiring "many" or "all"

    5) Respond ONLY with the matched condition exactly as listed above.
    """

    response = chat_together.invoke(condition_check_prompt)
    
    matched_condition = re.sub(r'^[\s\-\–\—\•\*]+', '', response.content)
    print(f"\n🧠 Matched condition: {matched_condition}")

    # Step 4: Find the next step or remain in current step
    matched = next((c for c in conditions if c["condition"].lower() == matched_condition.lower()), None)
    
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



    # Check if current step is one the user already self attempted
    if check_current_step_self_tested(current_step, step_status):
        print(f"🔄 User already self attempted step '{current_step}'.")
        
        # Find the appropriate condition that matches the failure scenario
        matched_condition = find_failed_condition_match(step_data, user_input, conversation_history, step_status[current_step])
        
        if matched_condition and matched_condition.lower() != "remain":
            conditions = step_data.get("conditions_to_determine_next_step", [])
            matched = next((c for c in conditions if c["condition"].lower() == matched_condition.lower()), None)
            
            if matched and matched["next_step"].lower() != "remain" and matched["next_step"].lower() != "step remain":
                next_step = matched["next_step"]
                print(f"⏭️ Skipping failed step and moving to: {next_step}")
                previous_step = current_step
                current_step = next_step
                current_step = current_step.lower().replace("step ", "")
                matched_key = get_step_by_normalized_name(normalize(current_step), knowledge_base)
                step_data = knowledge_base.get(matched_key, {})
                # Generate acknowledgment response for skipping failed step
                skip_response_prompt = f"""
                You are a telco customer support agent helping someone troubleshoot slow data issues.

                Chat History: \"{conversation_history}\"
                User's latest message:
                \"{user_input}\"


                Create a brief and concise response and restricted to following content:
                1. First acknowledge User Responses
                2. Acknowledges they've already self performed the step of {normalize(previous_step)} and it didn't work.
                3. Now we are moving on to the next step {normalize(current_step)}

                
                """

                acknowledgment = chat_groq.invoke(skip_response_prompt)

                # Ask LLM to generate a reply based on data and approaches of next step
                data_to_collect = step_data.get("data_to_collect_from_user", "")
                approaches = step_data.get("approaches_for_llm_to_collect_data", step_data.get("approaches_for_closing_chat", []))

                guidance_prompt = f"""
                You are a telco customer support agent helping someone troubleshoot slow data issues.
                
                Acknowledgement that user has self performed previous step but failed: {acknowledgment}
                Chat History: \"{conversation_history}\"
                Please help the user based on:
                Goal: {data_to_collect}

                Given Approaches:
                {chr(10).join(f"- {a}" for a in approaches)}

                Merge with above acknowledgement as opening.
                Give a helpful, conversational reply to the user guiding them on what to do next based on the given approaches.
                Select the Appropriate Approach from the protocol Based on User's Response in order to achieve the given goal. 
                Apply one approach at a time or multiple approaches at a time depending on user's response.
                
                Keep your response concise and straight to the point.
                """
                reply = chat_groq.invoke(guidance_prompt)
                print(f"\nCustomer Service: {reply.content}")
                conversation_history.append({"role": "user", "content": user_input})
                conversation_history.append({"role": "customer service", "content": acknowledgment.content})


                step_tracking.append(current_step)
                conversation_history = conversation_history[-10:]
                continue
    
    # Extract step components for normal flow
    #conditions = step_data.get("conditions_to_determine_next_step", [])
    #condition_texts = [c["condition"] for c in conditions]

    # Step 3: Use LLM to determine which condition (if any) matches the user input
    #condition_check_prompt = f"""
    #You are a telco troubleshooting assistant.

    #Chat History: \"{conversation_history}\"
    #User message:
    #\"{user_input}\"

    #Known conditions:
    #{chr(10).join(f"- {c}" for c in condition_texts)}

    #Respond ONLY with the matched condition exactly as listed above. If none are matched, say "remain".
    #"""

    #response = chat_groq.invoke(condition_check_prompt)
    
    #matched_condition = re.sub(r'^[\s\-\–\—\•\*]+', '', response.content)
    #print(f"\nMatched condition: {matched_condition}")

    # Step 4: Find the next step or remain in current step
    #matched = next((c for c in conditions if c["condition"].lower() == matched_condition.lower()), None)
    
    #if matched and matched["next_step"].lower() != "remain" and matched["next_step"].lower() != "step remain":
    #    if matched["next_step"] == "Step proceed to previous step":
    #        previous_distinct_step = get_previous_distinct_step(step_tracking)
    #        current_step = previous_distinct_step.replace("Step ", "")
    #        print(f"➡️ Moving to previous step: {current_step}")
    #    else:
    #        next_step = matched["next_step"]
    #        print(f"➡️ Moving to next step: {next_step}")
    #        current_step = next_step
    #        current_step = current_step.replace("Step ", "")
    #    matched_key = get_step_by_normalized_name(normalize(current_step), knowledge_base)
    #    step_data = knowledge_base.get(matched_key, {})
    #else:
    #    print("⏳ Staying in current step (condition not matched or unclear).")

    # Step 5: Ask LLM to generate a reply based on data and approaches
    data_to_collect = step_data.get("data_to_collect_from_user", "")
    approaches = step_data.get("approaches_for_llm_to_collect_data", step_data.get("approaches_for_closing_chat", []))

    guidance_prompt = f"""
    You are a telco customer support agent helping someone troubleshoot slow data issues.

    Chat History: \"{conversation_history}\"
    context awareness: {how_context_relate_query}
    user current query: {user_input}
    Objective: {data_to_collect}

    Given Approaches:
    {chr(10).join(f"- {a}" for a in approaches)}


    Give a helpful, conversational reply to the user guiding them on what to achieve the objective based on the given approaches. 
    Acknowledge User Input.
    Select the Appropriate Approach from the protocol in order to achieve the objective above. Apply one approach at a time.
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