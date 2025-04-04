import os
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferWindowMemory
from langchain_groq import ChatGroq
from langchain_together import ChatTogether
import json
import re
from langchain.prompts import ChatPromptTemplate
import telco_chatbot
from prompt_template import CONVERSATION_PROMPT, TELCO_USER_PROMPT
from dotenv import load_dotenv
import time
conversationprompt = ChatPromptTemplate.from_template(CONVERSATION_PROMPT)
telcouserprompt = ChatPromptTemplate.from_template(TELCO_USER_PROMPT)

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

memory = ConversationBufferWindowMemory(k=20)
conversation_groq = ConversationChain(
    llm=chat_groq,
    verbose=False,
    memory=memory
)

def check_user_intent_to_end_chat(user_query, chat_history, how_context_relate_query):
    prompt = f"""
        Existing ongoing conversation is about AI chatbot intends to help user resolve the issue of slow mobile data via a series of troubleshooting. 
        Please analyze if the user has clear intent to switch topic or end this troubleshooting. 
        
        Unless the user explicitly introduces a new topic (e.g., asking about a different problem), or clearly signals an end (e.g., 'thanks, that’s all'), 
        assume they are still engaged in the troubleshooting flow, even if they say something like 'hello', 'okay', or 'thanks'.

        Once user is found to have the intent to end the chat, we will proceed to analyse if user has confirmed to end the chat, or has agreed to end the chat. Otherwise, the default answer for whether the user confirm to end the chat is 'NO'

        Return the output strictly in this JSON format:  
        {{
            "does_user_intend_to_end_chat": "YES/NO",
            "Result_of_analysis1": "<summary or empty>",

            "does_user_confirm_to_end_chat": "YES/NO",
            "Result_of_analysis2": "<summary or empty>"
        }}


        Latest User Query: "{user_query}"  
        Conversation History: "{chat_history}"
        Context Awareness: "{how_context_relate_query}"
    """
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
            return 400
        
        does_user_intend_to_end_chat = json_data["does_user_intend_to_end_chat"]
        Result_of_analysis1 = json_data["Result_of_analysis1"]
        does_user_confirm_to_end_chat = json_data["does_user_confirm_to_end_chat"]
        Result_of_analysis2 = json_data["Result_of_analysis2"]

        #print("Does user intent to stop this converstaion:", does_user_intend_to_end_chat)
        #print("Result of analysis1:", Result_of_analysis1)
        #print("Does user confirm to end chat:", does_user_confirm_to_end_chat)
        #print("Result of analysis2:", Result_of_analysis2)
        print("\n\n")

    except json.JSONDecodeError:
        print("Error parsing JSON response")
    except ValueError:
        print("JSON not found in response")

    return does_user_intend_to_end_chat, Result_of_analysis1, does_user_confirm_to_end_chat, Result_of_analysis2
    

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
        response = chat_together.invoke(prompt)
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




def read_protocol_from_md(folder_path, md_filename):
    """Reads troubleshooting protocol from a Markdown file inside a folder."""
    md_file_path = os.path.join(folder_path, md_filename)
    
    if not os.path.exists(md_file_path):
        raise FileNotFoundError(f"Markdown file not found: {md_file_path}")
    
    with open(md_file_path, "r", encoding="utf-8") as file:
        return file.read()

def call_llm(user_message, conversation_history,protocol_content,context_awareness, does_user_intend_to_end_chat, does_user_confirm_to_end_chat):
    """Calls the LLM with the given system prompt and conversation history."""
    
    # Example: Calling OpenAI API (replace with Groq or another API if needed)
    messages = conversationprompt.format_messages(user_query=user_message, conversation_history = conversation_history, protocol_content = protocol_content, context_awareness = context_awareness, does_user_intend_to_end_chat=does_user_intend_to_end_chat, does_user_confirm_to_end_chat=does_user_confirm_to_end_chat)
    response = chat_together.invoke(messages[0].content)


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
                print(json_data)  # Print extracted JSON
            except json.JSONDecodeError as e:
                print("Invalid JSON:", e)
        else:
            print("No JSON found in the text.")
        
        response_to_user = json_data["response_to_user"]

        #print("Depends on Context:", depends_on_context)
        #print("Relevant Context:", relevant_context)
        #print("How Context Relate to Query:", how_context_relate_query)
        print("\n\n")

    except json.JSONDecodeError:
        print("Error parsing JSON response")
    except ValueError:
        print("JSON not found in response")

    
    return response_to_user

def chatbot_loop(folder_path="doc", md_filename="converstaion_protocol.md"):
    """Main chatbot function that loads the protocol and interacts with the user."""
    
    try:
        # Step 1: Load the troubleshooting protocol
        protocol_content = read_protocol_from_md(folder_path, md_filename)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return
    
    # Step 2: Create system prompt

    # Step 3: Start conversation loop
    conversation_history = []
    response_to_user = []
    
    print("AI Chatbot: Hello! How can I assist you?")
    #categories = telco_chatbot.process_md_files()
    while True:
        #user_message = input("You: ")
        message = telcouserprompt.format_messages(response_to_user=response_to_user,conversation_history=conversation_history)
        user_message = chat_groq2.invoke(message[0].content)
        print(f"User: {user_message.content}")
        if user_message.content.lower() in ["exit", "quit", "stop"]:
            print("AI Chatbot: Thank you! Have a great day.")
            break

        time.sleep(15)

        #depends_on_context, relevant_context, how_context_relate_query = check_query_context(user_message.content, conversation_history)
        depends_on_context, relevant_context, how_context_relate_query = check_query_context(user_message.content, conversation_history)
        does_user_intend_to_end_chat, Result_of_analysis1, does_user_confirm_to_end_chat, Result_of_analysis2 = check_user_intent_to_end_chat(user_message, conversation_history, how_context_relate_query)

        # Call LLM with system prompt and user message
        response_to_user = call_llm(user_message, conversation_history, protocol_content,how_context_relate_query,does_user_intend_to_end_chat,does_user_confirm_to_end_chat)
        
        # Display bot response
        print(f"Customer Service: {response_to_user}")

        # Update conversation history
        conversation_history.append({"role": "user", "content": user_message.content})
        conversation_history.append({"role": "customer service", "content": response_to_user})
        conversation_history = conversation_history[-10:]

# Example usage: Default folder is "doc", but can be changed
chatbot_loop(folder_path="doc", md_filename="converstaion_protocol.md")
