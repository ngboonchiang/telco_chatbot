import os
import mistune
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferWindowMemory
from langchain_groq import ChatGroq
from langchain_together import ChatTogether
from langchain.prompts import ChatPromptTemplate
from prompt_template import PREPROCESS_PROMPT, PREPROCESS_PROMPT2, PREPROCESS_PROMPT3
from dotenv import load_dotenv
import json
import re

firstprompt = ChatPromptTemplate.from_template(PREPROCESS_PROMPT)
secondprompt = ChatPromptTemplate.from_template(PREPROCESS_PROMPT2)
thirdprompt = ChatPromptTemplate.from_template(PREPROCESS_PROMPT3)
# Load environment variables
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

chat_together = ChatTogether(
    together_api_key=TOGETHER_API_KEY,
    model="deepseek-ai/DeepSeek-V3",
    #model="meta-llama/Llama-3.3-70B-Instruct-Turbo",
    temperature=0.5,
    max_tokens=5000,
    timeout=None,
    max_retries=2,
)

memory = ConversationBufferWindowMemory(k=4)
conversation_groq = ConversationChain(
    llm=chat_groq,
    verbose=False,
    memory=memory
)

def clean_title(title):
    """ Remove leading # and extra spaces but keep numbering. """
    return re.sub(r"^[#]+\s*", "", title).strip()


def extract_md_structure(md_content):
    structure = {}
    category = None
    subtitle = None
    subcategories = []

    lines = md_content.split("\n")
    for line in lines:
        if line.startswith("###"):  # Main category title
            if category and subtitle and subcategories:
                structure[category][subtitle] = subcategories
                subcategories = []
            category = clean_title(line)
            structure[category] = {}
        elif line.startswith("##"):  # Subtitle (keeps numbering)
            if category and subtitle and subcategories:
                structure[category][subtitle] = subcategories
                subcategories = []
            subtitle = clean_title(line)
            structure[category][subtitle] = []
        elif re.match(r'^[a-zA-Z]\.', line.strip()):  # Sub-subcategory (a. b. c. format)
            if subtitle:
                subcategories.append(line.strip())
        elif line.strip() == "THE END":  # End of document
            if category and subtitle and subcategories:
                structure[category][subtitle] = subcategories
    
    return structure

def process_md_files(doc_folder="doc"):
    final_structure = {}

    for filename in os.listdir(doc_folder):
        if filename.endswith(".md"):
            with open(os.path.join(doc_folder, filename), "r", encoding="utf-8") as file:
                md_content = file.read()
                md_structure = extract_md_structure(md_content)
                
                # Merge with final_structure
                for category, subtitles in md_structure.items():
                    if category not in final_structure:
                        final_structure[category] = {}
                    final_structure[category].update(subtitles)

    return final_structure

def classify_intent(user_query, categories):
    #prompt = f"""
    #Identify all relevant categories and subcategories for the user's query from the following options:
    #Categories: {', '.join(categories.keys())}
    #Subcategories:
    #"""
    categoriesstr= ', '.join(categories.keys())
    subcategories = ""
    for cat, subs in categories.items():
        subcategories += f"\n{cat}: {', '.join(subs.keys())}"

    messages = firstprompt.format_messages(user_query=user_query,categoriesstr=categoriesstr)

    response = chat_groq.invoke(input=messages[0].content)
    match = re.search(r'\{.*\}', response.content, re.DOTALL)

    if match:
        json_data = match.group(0)  # Get JSON string
        data = json.loads(json_data)  # Parse JSON
        print(data)
    else:
        print("No valid JSON found.")

    print(response)

    if data['categories'][0]['category'] == 'G. Others':
        print('\n\nIt does not match any group!')
        return 400

    
    extracted_subcats = extract_subcats(data, categories, threshold=0.7)

    #formatted_extracted_titles = "\n".join(
    #    f"{category}:\n" + "\n".join(titles)
    #    for category, titles in extracted_titles.items()
    #)

    formatted_sections = []

    for category, subcategories in extracted_subcats.items():
        category_section = f"Category: {category}\n" + "Subcategories:\n"+"\n".join(subcategories)  # Format each category with its titles
        formatted_sections.append(category_section)  # Add to list

    # Join all categories with a newline
    formatted_extracted_subcats = "\n\n".join(formatted_sections)

    user_intent = data["potential user intent"]
    messages = secondprompt.format_messages(user_query=user_query,titlestr=formatted_extracted_subcats, user_intent=user_intent)
    response = chat_groq.invoke(input=messages[0].content)
    
    match = re.search(r'\{.*\}', response.content, re.DOTALL)

    if match:
        json_data = match.group(0)  # Get JSON string
        data = json.loads(json_data)  # Parse JSON
        print(data)
    else:
        print("No valid JSON found.")
    
    if data['categories'][0]['category'] == 'G. Others':
        print('\n\nIt does not match any group!')
        return 400

    extracted_issues = extract_high_conf_issues(data, categories, threshold=0.8)
    issuestr = dict_to_string(extracted_issues)

    messages = thirdprompt.format_messages(user_query=user_query,issuestr=issuestr, user_intent=user_intent)
    response = conversation_groq.predict(input=messages[0].content)
    
    match = re.search(r'\{.*\}', response, re.DOTALL)

    if match:
        json_data = match.group(0)  # Get JSON string
        data = json.loads(json_data)  # Parse JSON
        print(data)
    else:
        print("No valid JSON found.")


    return response

def respond_to_query(user_query, categories):
    relevant_issues = classify_intent(user_query, categories)
    if not relevant_issues:
        return "Sorry, I couldn't determine the category of your query. Can you clarify?"

    return relevant_issues


def extract_subcats(data, categories, threshold):
    high_conf_categories = {}
    for cat in data['categories']:
        if cat['confidence'] > threshold:
            high_conf_categories[cat['category']] = cat['confidence']
    extracted_subcats = {}

    for cat, conf in high_conf_categories.items():
        if cat in categories:
            extracted_subcats[cat] = list(categories[cat].keys())

    return extracted_subcats

def remove_subcategory_numbering(subcategory_title):
    """Remove numbering from subcategories (e.g., '1. Network Issues' -> 'Network Issues')."""
    return re.sub(r"^\d+\.\s*", "", subcategory_title).strip()

def extract_high_conf_issues(data, categories, threshold=0.8):
    extracted_issues = {}

    for item in data['categories'][0]['subcategories']:  # Extract relevant titles
        title = item['subcategory']
        confidence = item['confidence']

        if confidence > threshold:
            for category, subcategories in categories.items():
                for subcategory, issues in subcategories.items():
                    if subcategory == title or remove_subcategory_numbering(subcategory) == title:  # Match cleaned title
                        if category not in extracted_issues:
                            extracted_issues[category] = {}
                        extracted_issues[category][subcategory] = issues  # Extract list

    return extracted_issues


def format_filtered_issues(filtered_issues):
    output = []
    
    for category, subcategories in filtered_issues.items():
        output.append(f"{category}")  # Category title without quotes
        for subcategory, issues in subcategories.items():
            output.append(f"{subcategory}")
            output.append("issues:")
            output.extend(issues)  # Add each issue
            output.append("")  # Blank line for spacing
    
    return "\n".join(output)


def dict_to_string(data):
    output = []
    
    for category, subcategories in data.items():
        output.append(f"Category:{category}")  # Add category title
        
        for subcategory, issues in subcategories.items():
            output.append(f"Subcategory:{subcategory}")  # Add subcategory title
            
            for idx, issue in enumerate(issues, start=0):  # Using alphabet (a, b, c)
                #letter = chr(ord('a') + idx)
                output.append(f"{issue}")  # Add lettered issues
            
            output.append("")  # Add a blank line for better readability
    
    return "\n".join(output)



if __name__ == "__main__":
    categories = process_md_files()
    while True:
        user_query = input("You: ")
        if user_query.lower() in ["exit", "quit"]:
            break
        response = respond_to_query(user_query, categories)
        print("Bot:", response)
