import os
import requests
import time
import asyncio
import csv
from openai import OpenAI
import asyncio
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)

# Instantiate the OpenAI client
client = OpenAI(api_key='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')
class DataHandler:
    def __init__(self):
        self._event_name = None
        self._selected_numbers = None
        self._model = None
    @property
    def event_name(self):
        return self._event_name
    @event_name.setter
    def event_name(self, value):
        self._event_name = value
    @property
    def selected_numbers(self):
        return self.selected_numbers
    @selected_numbers.setter
    def selected_numbers(self, value):
        self._selected_numbers = value
    @property
    def model(self):
        return self.model
    @model.setter
    def model(self, value):
        self._model = value
data_handler = DataHandler()
@app.route('/process', methods=['POST'])
def process_request():
    global data_handler
    data =  request.get_json()
    print("data: ", data)
    event_name = data["event_name"]
    selected_numbers=data["selected_numbers"]
    model=data["model"]
    # Use the setter to set the event_name
    data_handler.event_name = event_name
    data_handler.selected_numbers = selected_numbers
    data_handler.model = model
    
    print("Event Name ------>", data_handler)
    return jsonify({"message": "Data received successfully."})

def get_captions(event_name, last_position, line_length, language_code):
    url = f"https://www.streamtext.net/captions?event={event_name}&last={last_position}&length={line_length}&language={language_code}"
    
    print(f"Requesting URL: {url}")
    response = requests.get(url)
    print(f"Response Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        return data['content'], data['lastPosition']
    else:
        return None, None

def concise_summary(content, context_summaries, model):
    prompt = "Here are some previous summaries for context:\n\n"
    for summary in context_summaries:
        prompt += f"- {summary}\n"
    prompt += "\nNow, summarize the following new text in about 100 characters, considering the context but not including it in the summary:\n\n"
    prompt += f"New Content: {content}\n\nSummary:"

    try:
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=model,
        )
        return chat_completion.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error during OpenAI API call: {e}")
        return None

def translation_with_context(content, context_summaries, source_language, target_language, model):
    prompt = f"Translate the following content from {source_language} to {target_language}, considering the context:\n\n"
    for summary in context_summaries:
        prompt += f"- {summary}\n"
    prompt += f"\nNew Content: {content}\n\nTranslation:"
    try:
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=model,
        )
        return chat_completion.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error during OpenAI API call: {e}")
        return None


def bullet_point_summary(content, context_summaries, model):
    prompt = "Here are some previous summaries for context:\n\n"
    for summary in context_summaries:
        prompt += f"- {summary}\n"
    prompt += "\nNow, provide a summary in bullet point format with no more than three concise bullet points approximately 150 characters each, considering the context but not including it in the bullet points:\n\n"
    prompt += f"New Content: {content}\n\nSummary:"

    try:
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=model,
        )
        return chat_completion.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error during OpenAI API call: {e}")
        return None

def get_event_name():
    global data_handler
    input_str = data_handler.event_name
    if 'streamtext.net' in input_str and 'event=' in input_str:
        event_name = input_str.split('event=')[-1]
    else:
        event_name = input_str
    return event_name

def get_user_choices():
    options = {}
    global data_handler
    available_options = {'1': 'concise', '2': 'bullet_point', '3': 'translation'}
    print("Available options: 1. Concise, 2. Bullet Points, 3. Translation")
    selected_numbers = "1"
    # data_handler.selected_numbers
    print("selected_numbers------>",selected_numbers)
    # input("Select options by numbers (e.g., 1,2 for Concise and Bullet Points): ").split(',')

    for number in selected_numbers:
        option = available_options.get(number.strip())
        if option:
            line_length = input(f"Choose line length for {option} - short (200), medium (500), or long (750): ")
            sleep_time = input(f"Enter sleep time (in seconds) after each {option} request: ")
            if option == 'translation':
                source_language = input("Enter source language for translation (e.g., English): ")
                target_language = input("Enter target language for translation (e.g., Spanish): ")
                options[option] = {
                    'line_length': {'short': 200, 'medium': 500, 'long': 750}.get(line_length, 500),
                    'sleep_time': int(sleep_time),
                    'source_language': source_language,
                    'target_language': target_language
                }
            else:
                options[option] = {
                    'line_length': {'short': 200, 'medium': 500, 'long': 750}.get(line_length, 500),
                    'sleep_time': int(sleep_time)
                }
    return options

def get_model_choice():
    global data_handler
    model_choice =data_handler.model 
    # input("Select AI model: 1. Basic (gpt-3.5-turbo), 2. Advanced (gpt-4): ")
    return "gpt-4" if model_choice.strip() == "2" else "gpt-3.5-turbo"

def save_to_csv(filename, content, summary):
    script_dir = os.path.dirname(os.path.abspath(__file__))  # Directory of the script
    filepath = os.path.join(script_dir, filename)  # Path for the CSV file
    print(f"Saving to: {filepath}")  # Debug statement
    with open(filepath, 'a', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([content, summary])

async def async_summarize(content, context_summaries, options, model):
    loop = asyncio.get_event_loop()
    tasks = []
    results = {}

    for option, settings in options.items():
        if option == 'bullet_point':
            tasks.append(loop.run_in_executor(None, bullet_point_summary, content, context_summaries, model))
        elif option == 'concise':
            tasks.append(loop.run_in_executor(None, concise_summary, content, context_summaries, model))
        elif option == 'translation':
            source_language = settings.get('source_language')
            target_language = settings.get('target_language')
            tasks.append(loop.run_in_executor(None, translation_with_context, content, context_summaries, source_language, target_language, model))

    completed, pending = await asyncio.wait(tasks)
    for task in completed:
        result = task.result()
        if result:
            results[option] = result

    return results

# Main script
# event_name = get_event_name()
# model = get_model_choice()
language_code = "en"
last_positions = {'concise': 0, 'bullet_point': 0, 'translation': 0}

options = get_user_choices()
context_summaries = []

async def main():
    while True:
        for option, settings in options.items():
            content, last_positions[option] = get_captions(get_event_name(), last_positions[option], settings['line_length'], language_code)

            if content is not None and content.strip() != "":
                print(f"Caption for {option}: {content}")
                
                summaries = await async_summarize(content, context_summaries, {option: settings}, get_model_choice())
                if summaries.get(option):
                    print(f"{option.capitalize()} Summary: {summaries[option]}")
                    context_summaries.append(summaries[option])
                    if len(context_summaries) > 5:
                        context_summaries.pop(0)

                    # Save to CSV with a specific filename for each option
                    csv_filename = f"{get_event_name()}_{option}_summaries.csv"
                    save_to_csv(csv_filename, content, summaries[option])

            elif content is None:
                print(f"Error in fetching captions for {option}.")
            else:
                print(f"No new caption content for {option}.")

            time.sleep(settings['sleep_time'])

asyncio.run(main())