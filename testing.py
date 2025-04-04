from dotenv import load_dotenv
import os
from langchain_groq import ChatGroq
from langchain_together import ChatTogether
from langchain.prompts import ChatPromptTemplate
import re
import json
from prompt_template import TELCO_USER_PROMPT
import time
telcouserprompt = ChatPromptTemplate.from_template(TELCO_USER_PROMPT)

load_dotenv()
GROQ_API_KEY = os.environ["GROQ_API_KEY"]
TOGETHER_API_KEY = os.environ["TOGETHER_API_KEY"]

chat_groq = ChatGroq(
    temperature=0,
    top_p=1,
    groq_api_key=GROQ_API_KEY,
    model_name="llama-3.3-70b-versatile",
    max_tokens=5000,
)

chat_together = ChatTogether(
    together_api_key=TOGETHER_API_KEY,
    model="deepseek-ai/DeepSeek-V3",
    top_p=1,
    temperature=0,
    max_tokens=5000,
    timeout=None,
    max_retries=2
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

conversation_history = []
current_step = "0 Introduction & Issue Confirmation"
response_to_user = "How can I help you?"
print(f"Customer Service; {response_to_user}")

while True:
    message = telcouserprompt.format_messages(response_to_user=response_to_user,conversation_history=conversation_history)
    user_message = chat_groq.invoke(message[0].content)
    user_input = user_message.content
    print(f"User: {user_message.content}")
    depends_on_context, relevant_context, how_context_relate_query = check_query_context(user_input, conversation_history)
    time.sleep(10)
    prompt= f""" 
    You are a telco troubleshooting assistant. We are trying to collect data from the user's response and analyze if the data meets any of the condition below.


            Chat History: {conversation_history}
            Context: {how_context_relate_query}
            User message:{user_input}

            Analyze following conditions one by one and check if it closely matches the User’s Response:
            *if the user has exceeded their data limit -Step 50 Summary  
            *if user confirmed data throttling policies or fair usage policies are applied to their account-Step 50 Summary    
            *if the user confirmed they do not experience throttling-Step 2C.2 Reinserting SIM  
            *if data throttling policies or fair usage policies are not applied to user's account-Step 2C.2 Reinserting SIM
            *if the user has unlimited data plan-Step 2C.2 Reinserting SIM  
            *if user requests to move to previous step-Proceed to previous step
            *if the user's response is unclear-remain

            1) Return a matched condition ONLY if:
            -if user response closely and fully matches the content of the condition
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

            Analyze the user's response ONLY against these conditions. Return one exact matched condition if fully satisfied with explicit evidence. Otherwise, return 'remain'. Do NOT infer.
            Provide analyse result and reasoning for the choice of condition.

    """

    response = chat_together.invoke(prompt)
    print(response.content)

    guidance_prompt = f"""
    You are a telco customer support agent helping someone troubleshoot slow data issues.

    Chat History: \"{conversation_history}\"
    context awareness: {how_context_relate_query}
    user current query: {user_input}
    Objective: 
    a. Determine whether the user has reached or exceeded their data plan limit.  
    b. Check if the user is experiencing reduced speeds due to a fair usage policy (FUP) or data cap.  
    c. Identify whether the user is on a limited or unlimited plan and whether throttling applies.     

    Given Approaches:
    a. Ask the User About Their Data Plan Usage – Directly ask if they have checked their current data usage and whether they might have reached their limit.  
    b. Guide the User to Check Data Usage himself – Provide steps to check data usage via carrier apps, USSD codes, or online portals.  
    c. Explain Data Throttling and Fair Usage Policies – Inform the user that some plans reduce speeds after a certain usage threshold.  
    d. Guide the user to check if Fair Usage Policy is applied for their plan-You can check your plan’s Fair Usage Policy by logging into your account online or via our mobile app. Look under ‘Plan Details’ or ‘Usage Policy’.
    e. Confirm Whether Fair Usage Policy Is the Cause of the Issue – Ask if they notice a pattern of slow speeds after using a certain amount of data.
    f. Do not allow moving a step further if user requests for it
    g. Do allow moving to previous step if user requests for it


    Give a helpful, conversational reply to the user guiding them on what to do in order to achieve the given objective based on the given approaches. 
    Acknowledge User Input.
    Select the Appropriate Approach from the protocol in order to achieve the objective above. Apply one approach at a time.
    Avoid explicitly mentioning which approach you're using.
    Keep your response concise and straight to the point. 
    """

    reply = chat_together.invoke(guidance_prompt)
    print(f"Customer Service: {reply.content}")

    conversation_history.append({"role": "user", "content": user_input})
    conversation_history.append({"role": "customer service", "content": reply.content})
    conversation_history = conversation_history[-10:]