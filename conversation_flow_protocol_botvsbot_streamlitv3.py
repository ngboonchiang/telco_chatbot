import streamlit as st
from dotenv import load_dotenv
import os
from langchain_groq import ChatGroq
from langchain_together import ChatTogether
from langchain.prompts import ChatPromptTemplate
import re
import json
from prompt_template import TELCO_USER_PROMPT, CONDITION_CHECK_PROMPTV2, CONDITION_CHECK_PROMPT, CUSTOMER_SERVICE_PROMPT, SUMMARY_PROMPT, TELCO_USER_PROMPTV2
import time
from generate_structured_knowledgebase import knowledge_base

# === Helper Functions ===
def extract_json(response):
    match = re.search(r'```json\n(.*?)\n```', response, re.DOTALL)
    if match:
        json_str = match.group(1).strip()
        try:
            data = json.loads(json_str)
            return data
        except json.JSONDecodeError as e:
            print("Invalid JSON:", e)
    else:
        print("No JSON found in the text.")
    return None

def check_query_context(user_query, chat_history):
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

    try:
        response = chat_groq.invoke(prompt)
    except Exception as e:
        print(f"Unexpected error: {e}")
        response = None

    try:
        match = re.search(r'\{.*\}', response.content, re.DOTALL)
        if match:
            json_str = match.group()
            json_data = json.loads(json_str)
        else:
            print("No JSON found in the text.")
        return (
            json_data["depends_on_context"],
            json_data["relevant_context"],
            json_data["how_context_relate_query"]
        )
    except Exception as e:
        print("Error parsing JSON:", e)
        return "NO", "", ""

def extract_steps2(troubleshooting_dict):
    return {
        step.lower(): {"mode": "none", "result": "none"} 
        for step in troubleshooting_dict.keys()
    }

def normalize(text):
    text = re.sub(r'^\s*\w+(\.\w+)*\.?\s*', '', text)
    text = re.sub(r'[^\w\s]', '', text)
    return text.lower().strip()

def get_last_step(data):
    if len(data) < 2:
        return None
    return data[-1].get("step")

def get_step_by_normalized_name(normalized_name, knowledge_base):
    for key in knowledge_base:
        if normalize(key) == normalized_name:
            return key
    return None

def extract_number(user_input):
    match = re.search(r'\d+', user_input)
    return int(match.group()) if match else None

def get_original_step(complete_step_tracking_reversed, user_input):
    user_choice = extract_number(user_input)
    if user_choice is None:
        return "Wrong input format"
    if 1 <= user_choice <= len(complete_step_tracking_reversed):
        return complete_step_tracking_reversed[user_choice - 1]["step"]
    return "Number is out of range!"

def find_step_index(complete_step_tracking_reversed, selected_step):
    for idx, item in enumerate(complete_step_tracking_reversed):
        if item["step"] == selected_step:
            return idx
    return None

def update_step_tracking(complete_step_tracking_reversed, selected_step):
    step_index = find_step_index(complete_step_tracking_reversed, selected_step)
    if step_index is None:
        return "Step not found."
    return complete_step_tracking_reversed[:step_index + 1]

def clean_step_names(complete_step_tracking_reversed):
    cleaned_steps = []
    for idx, item in enumerate(complete_step_tracking_reversed):
        cleaned_step = re.sub(r'^[\d\.a-zA-Z]+ ', '', item['step'])
        formatted_step = f"{idx + 1}. {cleaned_step}"
        cleaned_steps.append(formatted_step)
    return "\n".join(cleaned_steps)

def type_message(role, icon, message, delay=0.05):
    with st.chat_message(role):
        msg_placeholder = st.empty()
        full_message = f"{icon} **{role}:** "
        for i in range(len(message) + 1):
            msg_placeholder.markdown(full_message + message[:i])
            time.sleep(delay)

# === Streamlit UI Setup ===
if 'running' not in st.session_state:
    st.session_state.running = False
if 'paused' not in st.session_state:
    st.session_state.paused = False
if 'initialized' not in st.session_state:
    st.session_state.initialized = False

# Sidebar access control
st.sidebar.subheader("🔐 Access Control")
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    password = st.sidebar.text_input("Enter password to unlock controls", type="password")
    if password == "sapientusmalaysia":
        st.session_state.authenticated = True
        st.sidebar.success("✅ Access granted.")
    elif password:
        st.sidebar.error("❌ Incorrect password.")

# Persona options
persona_options = {
    "Cooperative User": """
        -Describe the Issue Clearly
        -Mention relevant details (e.g., location, device type, signal strength).
        -Be patient if the operator is helpful.
        -Express mild frustration or concern if the operator is unhelpful, but remain cooperative.
        -Attempt the solutions provided (e.g., restart phone, toggle airplane mode).
        -You are a regular user, not a tech expert.
        -Keep responses concise and brief.
    """,
    "Skeptical User": """
        -Describe the Issue in detailed
        -Express great frustration and concern if the operator is unhelpful.
        -disbelieves customer service's solutions.
        -Need to be convinced before attempting the solutions provided (e.g., restart phone, toggle airplane mode).
        -You are a regular user, not a tech expert.
        -Keep responses full of hostility.
    """
}


if st.session_state.authenticated:
    selected_persona_label = st.sidebar.selectbox(
        "🎭 Select User Persona",
        options=list(persona_options.keys()),
        index=0
    )

    user_persona = persona_options[selected_persona_label]

    if st.sidebar.button("Start"):
        st.session_state.running = True
        st.session_state.paused = False

    #if st.sidebar.button("Pause"):
    #    st.session_state.paused = True
    #if st.sidebar.button("Continue"):
    #    st.session_state.paused = False
    #    if st.session_state.initialized == True:
    #        for msg in st.session_state.conversation_history_complete:
    #            role = "user" if msg["role"] == "user" else "assistant"
    #            icon = "👤" if role == "user" else "🤖"
    #            with st.chat_message(role):
    #                st.markdown(f"{icon} **{role.title()}:** {msg['content']}")
    if st.sidebar.button("Stop"):
        st.session_state.running = False
        st.session_state.paused = False
        st.session_state.initialized = False
        st.session_state.intro_shown = False

st.title("Bilateral AI Customer Service Chatbot")


# Load env
load_dotenv()
GROQ_API_KEY = os.environ["GROQ_API_KEY"]
TOGETHER_API_KEY = os.environ["TOGETHER_API_KEY"]

# Setup prompts and models
telcouserprompt = ChatPromptTemplate.from_template(TELCO_USER_PROMPT)
telcouserpromptv2 = ChatPromptTemplate.from_template(TELCO_USER_PROMPTV2)
conditioncheckprompt = ChatPromptTemplate.from_template(CONDITION_CHECK_PROMPTV2)
customerserviceprompt = ChatPromptTemplate.from_template(CUSTOMER_SERVICE_PROMPT)
summaryprompt = ChatPromptTemplate.from_template(SUMMARY_PROMPT)

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
    temperature=0,
    top_p=1,
    max_tokens=5000,
    timeout=None,
    max_retries=2,
)

# Initialize state variables
if not st.session_state.initialized:
    st.session_state.conversation_history_complete = []
    st.session_state.conversation_history = []
    st.session_state.step_tracking = []
    st.session_state.complete_step_tracking_reversed = []
    st.session_state.complete_step_tracking = []
    st.session_state.current_step = "0 Introduction & Issue Confirmation"
    st.session_state.step_status = extract_steps2(knowledge_base)
    st.session_state.skip_key = 0
    st.session_state.initialized = True

# === Display chat history if paused or idle ===
if not st.session_state.running or st.session_state.paused:
    for msg in st.session_state.conversation_history_complete:
        role = "user" if msg["role"] == "user" else "AI"
        icon = "👤" if role == "user" else "🤖"
        with st.chat_message(role):
            st.markdown(f"{icon} **{role.title()}:** {msg['content']}")


# === Main Loop ===
if st.session_state.running:
    while st.session_state.running:
        if st.session_state.paused:
            st.warning("⏸ Paused. Click 'Continue' to resume.")
            break

        current_step = st.session_state.current_step
        # Inside the main loop, replace the response_to_user assignment block with:
        if 'intro_shown' not in st.session_state:
            st.session_state.intro_shown = False

        #response_to_user = ""
        if current_step == "0 Introduction & Issue Confirmation" and not st.session_state.intro_shown:
            response_to_user = "How can I help you?"
            st.session_state.conversation_history_complete.append({"role": "customer service", "content": response_to_user})
            st.session_state.intro_shown = True
            type_message("AI", "🤖", response_to_user)

        if st.session_state.skip_key == 0:
            message = telcouserpromptv2.format_messages(response_to_user=response_to_user, conversation_history=st.session_state.conversation_history, user_persona=user_persona)
            user_message = chat_groq.invoke(message[0].content)
            user_input = user_message.content
            type_message("user", "👤", user_input)

            depends_on_context, relevant_context, how_context_relate_query = check_query_context(user_input, st.session_state.conversation_history)
            current_step = current_step.lower().replace("step ", "")
            matched_key = get_step_by_normalized_name(normalize(current_step), knowledge_base)

            if not matched_key:
                type_message("AI", "❌", "Step not found. Ending conversation.")
                st.session_state.running = False
                break

            step_data = knowledge_base.get(matched_key)
            conditions = step_data.get("conditions_to_determine_next_step", [])
            condition_texts = [c["condition"] for c in conditions]
            listofconditions = {chr(10).join(f"- {c}" for c in condition_texts)}
            condition_check_prompt = conditioncheckprompt.format_messages(
                conversation_history=st.session_state.conversation_history,
                how_context_relate_query=how_context_relate_query,
                user_input=user_input,
                listofconditions=listofconditions)
            response = chat_together.invoke(condition_check_prompt[0].content)
            json_data = extract_json(response.content)
            matched_condition_raw = json_data["one_exact_matched_condition"]
            matched_condition = re.sub(r'^[\s\-\–\—\•\*]+', '', matched_condition_raw)

            def normalize_condition(condition):
                return condition.lower().strip().lstrip("if ").strip()

            normalized_matched_condition = normalize_condition(matched_condition)
            matched = next(
                (c for c in conditions if normalize_condition(c["condition"]) == normalized_matched_condition),
                None
            )

        if matched and matched["next_step"].lower() not in ["remain", "step remain"]:
            if matched["next_step"].lower() == "step 51 close the chat":
                type_message("AI", "🤖", "Chat ending!")
                st.session_state.running = False
                break
            else:
                next_step = matched["next_step"].lower()
                complete_step_data = {
                    "step": current_step,
                    "mode": "customer guide",
                    "condition_met": matched["next_step"].lower(),
                    "next step": matched["next_step"].lower()
                }
                st.session_state.complete_step_tracking.append(complete_step_data)
                st.session_state.complete_step_tracking_reversed.append(complete_step_data)
                current_step = next_step.lower().replace("step ", "")
                st.session_state.current_step = current_step
                matched_key = get_step_by_normalized_name(normalize(current_step), knowledge_base)
                step_data = knowledge_base.get(matched_key, {})

        data_to_collect = step_data.get("data_to_collect_from_user", "")
        approaches = step_data.get("approaches_for_llm_to_collect_data", step_data.get("approaches_for_closing_chat", []))
        listofapproaches = {chr(10).join(f"- {a}" for a in approaches)}
        if normalize(current_step) == "summary":
            listofsteps = clean_step_names(st.session_state.complete_step_tracking_reversed)
            st.session_state.conversation_history = st.session_state.conversation_history_complete
            guidance_prompt = summaryprompt.format_messages(
                conversation_history=st.session_state.conversation_history,
                user_input=user_input,
                listofsteps=listofsteps)
        else:
            guidance_prompt = customerserviceprompt.format_messages(
                conversation_history=st.session_state.conversation_history,
                how_context_relate_query=how_context_relate_query,
                user_input=user_input,
                data_to_collect=data_to_collect,
                listofapproaches=listofapproaches)

        reply = chat_groq.invoke(guidance_prompt[0].content)
        response_to_user = reply.content

        type_message("AI", "🤖", response_to_user)

        st.session_state.conversation_history_complete.append({"role": "user", "content": user_input})
        st.session_state.conversation_history_complete.append({"role": "customer service", "content": response_to_user})
        st.session_state.step_tracking.append(current_step)
        st.session_state.conversation_history = st.session_state.conversation_history_complete[-10:]
        time.sleep(1)

if not st.session_state.running and not st.session_state.paused:
    st.rerun()
