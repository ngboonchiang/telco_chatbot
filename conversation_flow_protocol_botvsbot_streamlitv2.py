import streamlit as st
import time
from dotenv import load_dotenv
import os
from langchain_groq import ChatGroq
from langchain_together import ChatTogether
from langchain.prompts import ChatPromptTemplate
import re
import json
from prompt_template import TELCO_USER_PROMPT, CONDITION_CHECK_PROMPTV2, CUSTOMER_SERVICE_PROMPT, SUMMARY_PROMPT
from generate_structured_knowledgebase import knowledge_base

# --- Environment Variable Loading ---
# Try loading from .env, fall back to Streamlit secrets if available
try:
    load_dotenv()
    GROQ_API_KEY = os.environ["GROQ_API_KEY"]
    TOGETHER_API_KEY = os.environ["TOGETHER_API_KEY"]
except KeyError:
    try:
        GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
        TOGETHER_API_KEY = st.secrets["TOGETHER_API_KEY"]
    except KeyError:
        st.error("API keys not found. Please set GROQ_API_KEY and TOGETHER_API_KEY in your environment or Streamlit secrets.")
        st.stop()
except FileNotFoundError:
     try:
        GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
        TOGETHER_API_KEY = st.secrets["TOGETHER_API_KEY"]
     except KeyError:
        st.error("API keys not found and .env file missing. Please set API keys or create a .env file.")
        st.stop()


# --- LLM Setup ---
# Wrap in try-except blocks to handle potential initialization errors
try:
    chat_groq = ChatGroq(
        temperature=0,
        top_p=1,
        groq_api_key=GROQ_API_KEY,
        model_name="llama-3.1-70b-versatile", # Using 3.1 as 3.3 might not be available or stable
        max_tokens=5000,
    )
except Exception as e:
    st.error(f"Error initializing Groq LLM: {e}")
    st.stop()

try:
    chat_together = ChatTogether(
        together_api_key=TOGETHER_API_KEY,
        # model="deepseek-ai/DeepSeek-V2", # Using V2 as V3 might not be available/stable
        model="meta-llama/Llama-3-70b-chat-hf",
        temperature=0,
        top_p=1,
        max_tokens=5000,
        timeout=None,
        max_retries=2,
    )
except Exception as e:
    st.error(f"Error initializing Together LLM: {e}")
    st.stop()

# --- Helper Functions ---

def extract_json(response):
    # Improved regex to handle potential variations and leading/trailing whitespace
    match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL | re.IGNORECASE)
    if match:
        json_str = match.group(1).strip()
        try:
            # Attempt to clean potential escape issues before parsing
            json_str = json_str.replace('\\n', '\n').replace('\\"', '"')
            data = json.loads(json_str)
            return data
        except json.JSONDecodeError as e:
            print(f"Invalid JSON detected: {e}")
            print(f"Faulty JSON string: >>>{json_str}<<<")
            # Fallback: Try finding the first '{' and last '}'
            try:
                start = response.find('{')
                end = response.rfind('}')
                if start != -1 and end != -1 and end > start:
                    json_str_fallback = response[start:end+1].strip()
                    data = json.loads(json_str_fallback)
                    print("Successfully parsed with fallback method.")
                    return data
                else:
                    print("Fallback JSON extraction failed: No clear boundaries.")
            except json.JSONDecodeError as e_fallback:
                 print(f"Fallback JSON parsing also failed: {e_fallback}")
                 print(f"Fallback faulty JSON string: >>>{json_str_fallback}<<<")

    else:
        # Try finding JSON without backticks as a last resort
        try:
            start = response.find('{')
            end = response.rfind('}')
            if start != -1 and end != -1 and end > start:
                json_str_fallback = response[start:end+1].strip()
                data = json.loads(json_str_fallback)
                print("Successfully parsed JSON without backticks.")
                return data
            else:
                print("No JSON structure found in the text.")
        except json.JSONDecodeError as e_no_ticks:
            print(f"Parsing JSON without backticks failed: {e_no_ticks}")
            print(f"String attempted (no backticks): >>>{response[start:end+1].strip()}<<<")

    return None # Return None if all attempts fail

def check_query_context(user_query, chat_history):
    """Check if the query depends on previous chat history."""
    prompt = f"""
    You are an AI assistant with memory. The user’s queries may be brief or contextually dependent on prior conversation history.
    Analyze the latest query in relation to the conversation history and determine:
    - If the latest query depends on prior context.
    - If yes, extract the relevant details of the conversation and explain how this context relate to user query for context awareness purpose.
    - If no, return 'NO'.

    Return the output strictly in this JSON format:
    ```json
    {{
      "depends_on_context": "YES/NO",
      "relevant_context": "<summary or empty>",
      "how_context_relate_query": "<summary or empty>"
    }}
    ```

    language: same as the language of user query, either in english or mandarin
    Latest User Query: "{user_query}"
    Conversation History: "{chat_history}"
    """
    print("\n--- Checking Query Context ---")
    #print(f"Prompt:\n{prompt}") # Optional: for debugging prompt
    response_content = "" # Initialize
    try:
        response = chat_groq.invoke(prompt)
        response_content = response.content
        print(f"Context Check LLM Raw Response:\n{response_content}")
    except Exception as e:
        print(f"Error calling context check LLM: {e}")
        return "NO", "", "" # Default fallback

    json_data = extract_json(response_content)

    if json_data:
        try:
            depends_on_context = json_data.get("depends_on_context", "NO").upper()
            relevant_context = json_data.get("relevant_context", "")
            how_context_relate_query = json_data.get("how_context_relate_query", "")
            print("Context Check Successful:")
            print(f"  Depends: {depends_on_context}")
            print(f"  Context: {relevant_context}")
            print(f"  Relation: {how_context_relate_query}")
            print("--- End Context Check ---")
            return depends_on_context, relevant_context, how_context_relate_query
        except Exception as e:
             print(f"Error processing extracted JSON for context check: {e}")
    else:
        print("Context Check Failed: Could not extract JSON.")

    print("--- End Context Check ---")
    return "NO", "", "" # Default fallback if JSON parsing fails

# (Keep your other helper functions: update_step_tracking, extract_steps2, normalize,
# get_last_step, get_step_by_normalized_name, extract_number, get_original_step,
# find_step_index, update_step_tracking (the second one seems misnamed/redundant?), clean_step_names)

# Make sure this function is correctly defined (seems like a duplicate name?)
def update_selected_steps(complete_step_tracking_reversed, selected_step):
    """Updates the list to include steps only up to the selected step."""
    step_index = find_step_index(complete_step_tracking_reversed, selected_step)

    if step_index is None:
        print(f"Warning: Selected step '{selected_step}' not found in tracking list.")
        return complete_step_tracking_reversed # Return original list if step not found

    return complete_step_tracking_reversed[:step_index + 1]  # Keep only steps up to selected one


# --- Prompt Templates ---
telcouserprompt = ChatPromptTemplate.from_template(TELCO_USER_PROMPT)
conditioncheckprompt = ChatPromptTemplate.from_template(CONDITION_CHECK_PROMPTV2)
customerserviceprompt = ChatPromptTemplate.from_template(CUSTOMER_SERVICE_PROMPT)
summaryprompt = ChatPromptTemplate.from_template(SUMMARY_PROMPT)

# --- Streamlit Interface ---
st.set_page_config(page_title="Bilateral Conversational Chatbot")
st.title("Bilateral Conversational Chatbot: Telco Customer Service Troubleshooting Scenario")

# --- Initialize Session State ---
# Conversation history for display
if "messages" not in st.session_state:
    st.session_state.messages = []
# Flag to control the chat loop
if "conversation_active" not in st.session_state:
    st.session_state.conversation_active = False
# Store conversation state variables needed within the loop
if "chat_state" not in st.session_state:
    st.session_state.chat_state = {}

# --- Sidebar Controls ---
with st.sidebar:
    st.header("Controls")
    start_pressed = st.button("Start Conversation")
    stop_pressed = st.button("Stop Conversation")

# --- Handle Button Presses ---
if start_pressed:
    st.session_state.conversation_active = True
    # Reset chat history and state for a new conversation
    st.session_state.messages = [{"role": "Customer Service", "content": "How can I help you?"}]
    st.session_state.chat_state = {
        "current_step": "0 Introduction & Issue Confirmation",
        "conversation_history_llm": [], # History specifically for LLM context
        "conversation_history_complete": [], # Complete history for summary
        "step_tracking": [],
        "complete_step_tracking_reversed": [],
        "complete_step_tracking": [],
        "step_status": extract_steps2(knowledge_base),
        "skip_key": 0,
    }
    st.rerun() # Rerun to display the initial message and prepare for the loop

if stop_pressed:
    if st.session_state.conversation_active:
        st.session_state.conversation_active = False
        st.session_state.messages.append({"role": "System", "content": "Conversation stopped by user."})
        st.rerun() # Rerun to update the display and stop the loop if running
    else:
        # Optionally notify user if already stopped
        # st.sidebar.warning("Conversation is already stopped.")
        pass

# --- Display Chat History ---
chat_container = st.container()
with chat_container:
    for message in st.session_state.messages:
        # Don't display system messages
        if message["role"] != "System":
            st.write(f"**{message['role']}:** {message['content']}")

# --- Main Conversation Loop ---
if st.session_state.conversation_active:
    # Load state from session_state into local variables for easier access
    current_step = st.session_state.chat_state.get("current_step", "0 Introduction & Issue Confirmation")
    conversation_history_llm = st.session_state.chat_state.get("conversation_history_llm", [])
    conversation_history_complete = st.session_state.chat_state.get("conversation_history_complete", [])
    step_tracking = st.session_state.chat_state.get("step_tracking", [])
    complete_step_tracking_reversed = st.session_state.chat_state.get("complete_step_tracking_reversed", [])
    complete_step_tracking = st.session_state.chat_state.get("complete_step_tracking", [])
    step_status = st.session_state.chat_state.get("step_status", extract_steps2(knowledge_base))
    skip_key = st.session_state.chat_state.get("skip_key", 0)

    # Get the last message to determine who should speak next
    last_message = st.session_state.messages[-1] if st.session_state.messages else None

    # Only proceed if it's the user's turn (last message was from CS) or it's the very start
    if last_message and last_message["role"] == "Customer Service":

        # Simulate a brief pause before the user "responds"
        # time.sleep(2) # Optional delay

        try: # Wrap the core logic in try/except for robustness
            response_to_user = last_message["content"]

            # Check skip_key logic (ensure it's correctly handled)
            if skip_key == 0:
                # --- User Turn (LLM Simulation) ---
                st.info("Generating user response...") # Indicate activity
                message_user_prompt = telcouserprompt.format_messages(
                    response_to_user=response_to_user,
                    conversation_history=conversation_history_llm # Use LLM-specific history
                )
                user_message = chat_groq.invoke(message_user_prompt[0].content)
                user_input = user_message.content
                st.session_state.messages.append({"role": "User", "content": user_input})

                # Update histories immediately after getting user input
                conversation_history_complete.append({"role": "user", "content": user_input})
                conversation_history_llm = conversation_history_complete[-10:] # Keep LLM history concise

                # --- Customer Service Logic Turn ---
                st.info("Processing user input and determining next step...") # Indicate activity
                time.sleep(1) # Small delay for better UX

                depends_on_context, relevant_context, how_context_relate_query = check_query_context(user_input, conversation_history_llm)

                current_step_normalized_name = normalize(current_step.lower().replace("step ", ""))
                matched_key = get_step_by_normalized_name(current_step_normalized_name, knowledge_base)

                if not matched_key:
                    st.error(f"❌ Step key not found for normalized step: '{current_step_normalized_name}'. Ending conversation.")
                    st.session_state.messages.append({"role": "System", "content": f"Error: Step key not found for '{current_step}'."})
                    st.session_state.conversation_active = False
                    st.rerun()


                step_data = knowledge_base.get(matched_key, {}) # Use default empty dict
                conditions = step_data.get("conditions_to_determine_next_step", [])
                next_step = "" # Initialize next_step

                if conditions: # Only run condition check if conditions exist for the step
                    condition_texts = [c["condition"] for c in conditions]
                    # Ensure listofconditions is correctly formatted as a string
                    listofconditions_str = "\n".join(f"- {c}" for c in condition_texts)

                    condition_check_prompt = conditioncheckprompt.format_messages(
                        conversation_history=conversation_history_llm,
                        how_context_relate_query=how_context_relate_query,
                        user_input=user_input,
                        listofconditions=listofconditions_str # Pass the formatted string
                    )
                    response_cond_check = chat_together.invoke(condition_check_prompt[0].content)
                    json_data = extract_json(response_cond_check.content)

                    matched = None
                    if json_data and "one_exact_matched_condition" in json_data:
                        matched_condition_raw = json_data["one_exact_matched_condition"]
                        # Normalize raw condition from LLM
                        matched_condition_llm_normalized = normalize_condition(re.sub(r'^[\s\-\–\—\•\*]+', '', matched_condition_raw))

                        # Find the best match in our defined conditions
                        for c in conditions:
                            if normalize_condition(c["condition"]) == matched_condition_llm_normalized:
                                matched = c
                                break
                        if not matched:
                             print(f"Warning: LLM matched condition '{matched_condition_raw}' (Normalized: '{matched_condition_llm_normalized}') not found in step '{current_step}' conditions.")

                    else:
                         print(f"Warning: Could not extract matched condition from LLM response for step '{current_step}'. Response: {response_cond_check.content}")

                else:
                    # If no conditions, assume we proceed (or handle based on step definition)
                    # This might need refinement based on how steps without conditions should behave.
                    # For now, let's assume it might default to staying or having a default next step.
                    print(f"No conditions defined for step: {current_step}")
                    # Check if there's an implicit next step even without conditions
                    # This part depends on your knowledge_base structure conventions
                    if len(conditions) == 0 and step_data.get("next_step"): # Example convention
                         next_step = step_data["next_step"].lower()
                    else:
                         next_step = "remain" # Default to staying if no conditions and no explicit next_step


                # --- Determine Next Step Based on Condition Matching ---
                move_to_next_step_flag = False
                if matched and matched["next_step"].lower() not in ["remain", "step remain"]:
                    next_step = matched["next_step"].lower()
                    move_to_next_step_flag = True
                    print(f"Condition matched: '{matched['condition']}'. Moving to: '{next_step}'")

                    if next_step == "step 51 close the chat":
                        st.success("✅ Chat ending based on condition!")
                        st.session_state.messages.append({"role": "Customer Service", "content": "Okay, it looks like we've resolved the issue or reached the end of the process. Thank you!"}) # Add a closing message
                        st.session_state.conversation_active = False
                        st.rerun()

                    elif next_step == "step proceed to previous step":
                        complete_step_data = {
                            "step": current_step,
                            "mode": "customer guide",
                            "condition_met": next_step, # Use the raw next step string
                            "next step": next_step
                        }
                        complete_step_tracking.append(complete_step_data) # Add to forward tracking

                        if len(complete_step_tracking_reversed) > 0:
                            previous_distinct_step_data = complete_step_tracking_reversed.pop() # Remove last step
                            if len(complete_step_tracking_reversed) > 0:
                                current_step = complete_step_tracking_reversed[-1]["step"] # Get the new last step
                                print(f"➡️ Moving to previous step: {current_step}")
                                # Need to re-fetch matched_key and step_data for the *new* current_step
                                current_step_normalized_name = normalize(current_step.lower().replace("step ", ""))
                                matched_key = get_step_by_normalized_name(current_step_normalized_name, knowledge_base)
                                if matched_key:
                                    step_data = knowledge_base.get(matched_key, {})
                                else:
                                    st.error(f"❌ Error returning to previous step: Key not found for '{current_step}'. Stopping.")
                                    st.session_state.conversation_active = False
                                    st.rerun()

                            else:
                                st.warning("⚠️ Cannot go back further. Already at the beginning.")
                                # Decide behavior: stay at current step or end? For now, let's stay.
                                current_step = previous_distinct_step_data['step'] # Revert to the step we popped
                                complete_step_tracking_reversed.append(previous_distinct_step_data) # Put it back
                                move_to_next_step_flag = False # Force staying in current step logic
                        else:
                            st.warning("⚠️ Cannot go back. No previous steps recorded.")
                            move_to_next_step_flag = False # Force staying in current step logic


                    elif next_step == "step revisit previous step":
                        # Logic for allowing user to choose a step to revisit
                        if len(complete_step_tracking_reversed) < 1:
                             response_to_user = "There are no previous steps recorded to revisit."
                             st.session_state.messages.append({"role": "Customer Service", "content": response_to_user})
                             conversation_history_complete.append({"role": "customer service", "content": response_to_user})
                             # Stay in the current step, effectively
                             move_to_next_step_flag = False
                        else:
                            # Generate the list of steps for the user
                            steps_string = clean_step_names(complete_step_tracking_reversed)
                            revisit_prompt = f"Please key in the NUMBER of the step you would like to revisit:\n\nList of Previous Steps:\n{steps_string}"
                            st.session_state.messages.append({"role": "Customer Service", "content": revisit_prompt})
                            conversation_history_complete.append({"role": "customer service", "content": revisit_prompt})

                            # Set skip_key = 1 to indicate the *next* user input is the step number
                            skip_key = 1
                            # Don't generate another CS response yet, wait for user number input
                            # Store necessary state before rerunning
                            st.session_state.chat_state["current_step"] = current_step
                            st.session_state.chat_state["conversation_history_llm"] = conversation_history_llm
                            st.session_state.chat_state["conversation_history_complete"] = conversation_history_complete
                            st.session_state.chat_state["step_tracking"] = step_tracking
                            st.session_state.chat_state["complete_step_tracking_reversed"] = complete_step_tracking_reversed
                            st.session_state.chat_state["complete_step_tracking"] = complete_step_tracking
                            st.session_state.chat_state["step_status"] = step_status
                            st.session_state.chat_state["skip_key"] = skip_key
                            st.rerun() # Rerun to display the prompt and wait for user number

                    else: # Normal step progression
                        complete_step_data = {
                            "step": current_step,
                            "mode": "customer guide",
                            "condition_met": next_step,
                            "next step": next_step
                        }
                        complete_step_tracking.append(complete_step_data)
                        # Add to reversed tracking *only if* it's different from the last one or list is empty
                        if not complete_step_tracking_reversed or complete_step_tracking_reversed[-1]['step'] != current_step:
                             complete_step_tracking_reversed.append(complete_step_data)

                        current_step = next_step.replace("step ", "") # Update current step name
                        print(f"➡️ Moving to next step: {current_step}")

                        # Fetch data for the *new* current step
                        current_step_normalized_name = normalize(current_step.lower())
                        matched_key = get_step_by_normalized_name(current_step_normalized_name, knowledge_base)
                        if matched_key:
                           step_data = knowledge_base.get(matched_key, {})
                        else:
                            st.error(f"❌ Error moving to next step: Key not found for '{current_step}'. Stopping.")
                            st.session_state.conversation_active = False
                            st.rerun()

                else: # Condition not matched or step should remain
                    move_to_next_step_flag = False
                    # Add current step to tracking if it's not already the last one
                    if not complete_step_tracking_reversed or complete_step_tracking_reversed[-1]['step'] != current_step:
                         complete_step_data = {
                            "step": current_step,
                            "mode": "customer guide",
                            "condition_met": "remain / not matched", # Indicate why we stayed
                            "next step": "remain"
                         }
                         # Only add to reversed tracking if distinct
                         complete_step_tracking_reversed.append(complete_step_data)
                    print(f"⏳ Staying in current step: {current_step} (Condition: {matched['condition'] if matched else 'Not Matched / Remain'})")


                # --- Generate Customer Service Response ---
                if st.session_state.conversation_active: # Check again if conversation ended mid-logic
                    data_to_collect = step_data.get("data_to_collect_from_user", "")
                    # Handle potential variations in key names
                    approaches = step_data.get("approaches_for_llm_to_collect_data") or \
                                 step_data.get("approaches_for_closing_chat") or \
                                 step_data.get("customer_service_guidance") or \
                                 [] # Default to empty list

                    listofapproaches_str = "\n".join(f"- {a}" for a in approaches)

                    if normalize(current_step) == "summary":
                        listofsteps_str = clean_step_names(complete_step_tracking_reversed)
                        # Use the complete history for summary context
                        guidance_prompt = summaryprompt.format_messages(
                            conversation_history=conversation_history_complete,
                            user_input=user_input,
                            listofsteps=listofsteps_str
                        )
                    else:
                        guidance_prompt = customerserviceprompt.format_messages(
                            conversation_history=conversation_history_llm, # Use shorter history here
                            how_context_relate_query=how_context_relate_query,
                            user_input=user_input,
                            data_to_collect=data_to_collect,
                            listofapproaches=listofapproaches_str
                        )

                    st.info("Generating customer service response...") # Indicate activity
                    reply = chat_groq.invoke(guidance_prompt[0].content)
                    response_to_user = reply.content
                    st.session_state.messages.append({"role": "Customer Service", "content": response_to_user})
                    conversation_history_complete.append({"role": "customer service", "content": response_to_user})
                    step_tracking.append(current_step) # Track the step we just processed

            elif skip_key == 1:
                 # --- Handling User Input for Revisiting Step ---
                 st.info("Processing step selection...")
                 user_input = st.session_state.messages[-1]["content"] # Get the user's number input
                 conversation_history_complete.append({"role": "user", "content": user_input}) # Log it

                 selected_step_name = get_original_step(complete_step_tracking_reversed, user_input)

                 if selected_step_name in ["Number is out of range!", "Wrong input format"]:
                     response_to_user = f"Invalid selection: {selected_step_name}. Please enter a valid number from the list."
                     st.session_state.messages.append({"role": "Customer Service", "content": response_to_user})
                     conversation_history_complete.append({"role": "customer service", "content": response_to_user})
                     skip_key = 1 # Keep skip_key = 1 to re-prompt
                 else:
                     # Successfully selected a step to revisit
                     current_step = selected_step_name
                     print(f"Revisiting step: {current_step}")
                     # Update tracking to reflect the jump back
                     complete_step_tracking_reversed = update_selected_steps(complete_step_tracking_reversed, current_step)

                     # Reset skip_key to resume normal flow
                     skip_key = 0

                     # Need to generate a CS response for the revisited step
                     current_step_normalized_name = normalize(current_step.lower().replace("step ", ""))
                     matched_key = get_step_by_normalized_name(current_step_normalized_name, knowledge_base)
                     if matched_key:
                         step_data = knowledge_base.get(matched_key, {})
                         data_to_collect = step_data.get("data_to_collect_from_user", "")
                         approaches = step_data.get("approaches_for_llm_to_collect_data") or \
                                     step_data.get("approaches_for_closing_chat") or \
                                     step_data.get("customer_service_guidance") or \
                                     []
                         listofapproaches_str = "\n".join(f"- {a}" for a in approaches)

                         # Use a slightly modified prompt to acknowledge the revisit? (Optional)
                         # For simplicity, using the standard prompt for now.
                         guidance_prompt = customerserviceprompt.format_messages(
                            conversation_history=conversation_history_llm, # Use shorter history
                            how_context_relate_query="", # Context might be less relevant when jumping back
                            user_input=f"User chose to revisit step: {current_step}", # Provide context
                            data_to_collect=data_to_collect,
                            listofapproaches=listofapproaches_str
                         )
                         st.info("Generating customer service response for revisited step...")
                         reply = chat_groq.invoke(guidance_prompt[0].content)
                         response_to_user = reply.content
                         st.session_state.messages.append({"role": "Customer Service", "content": response_to_user})
                         conversation_history_complete.append({"role": "customer service", "content": response_to_user})
                         step_tracking.append(current_step) # Track the revisited step
                     else:
                        st.error(f"❌ Error revisiting step: Key not found for '{current_step}'. Stopping.")
                        st.session_state.conversation_active = False


            # --- Save State and Rerun ---
            # Store updated state back into session_state before rerunning
            st.session_state.chat_state["current_step"] = current_step
            st.session_state.chat_state["conversation_history_llm"] = conversation_history_llm
            st.session_state.chat_state["conversation_history_complete"] = conversation_history_complete
            st.session_state.chat_state["step_tracking"] = step_tracking
            st.session_state.chat_state["complete_step_tracking_reversed"] = complete_step_tracking_reversed
            st.session_state.chat_state["complete_step_tracking"] = complete_step_tracking
            st.session_state.chat_state["step_status"] = step_status
            st.session_state.chat_state["skip_key"] = skip_key

            if st.session_state.conversation_active: # Only rerun if conversation should continue
                st.rerun()

        except Exception as e:
            st.error(f"An error occurred during the conversation loop: {e}")
            import traceback
            st.error(traceback.format_exc()) # Print full traceback for debugging
            st.session_state.messages.append({"role": "System", "content": f"Error occurred: {e}. Stopping conversation."})
            st.session_state.conversation_active = False
            st.rerun()

    elif not last_message and st.session_state.conversation_active:
        # This case handles the very first turn after Start is pressed and the initial message is shown.
        # The loop logic expects the last message to be 'Customer Service', so it should proceed correctly.
        # No action needed here, the main condition `if last_message and last_message["role"] == "Customer Service":`
        # will be met in the next rerun after the initial message is displayed.
        pass

    # elif last_message and last_message["role"] == "User":
    #     # This means the user's message was just added, and we are waiting for the CS response part of the loop.
    #     # No action needed here, the script will rerun, and the CS logic will execute above.
    #     pass


# Add a message if the conversation ends naturally (not by stop button)
if not st.session_state.conversation_active and st.session_state.messages and st.session_state.messages[-1]["role"] != "System":
     # Check if the last *non-system* message indicates a natural end, maybe add a final system message.
     # This part is optional and depends on how you want to signify the end.
     pass