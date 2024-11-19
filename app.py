import os
import logging
from openai import OpenAI
from dotenv import load_dotenv
from flask import Flask, request, jsonify
import requests
import json
from get_image import get_image
from vision import process_images

load_dotenv()
class WatchSellingAssistant:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=self.api_key)
        self.memory_dir = "user_memory"
        self.initialize_memory_dir()

    # Ensure that the directory for user memory files exists
    def initialize_memory_dir(self):
        if not os.path.exists(self.memory_dir):
            os.makedirs(self.memory_dir)

    # Get the file path for a specific user
    def get_user_memory_file(self, wa_id):
        return os.path.join(self.memory_dir, f"{wa_id}_memory.txt")

    # Save conversation to a text file
    def save_to_memory(self, wa_id, user_message, assistant_reply):
        file_path = self.get_user_memory_file(wa_id)
        with open(file_path, "a") as f:
            f.write(f"User: {user_message}\n")
            f.write(f"Assistant: {assistant_reply}\n")

    # Load conversation history from a text file
    def load_from_memory(self, wa_id):
        file_path = self.get_user_memory_file(wa_id)
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                return f.read()
        return ""

    # Generate assistant's response with memory history
    def get_assistant_response(self, wa_id, prompt):
        try:
            # Load conversation history
            history = self.load_from_memory(wa_id)

            # Prepare messages for the OpenAI API
            messages = [
                {"role": "system", "content": """You are a professional and friendly assistant helping users sell their watches. You should guide the conversation naturally, like a human watch dealer. remember you are the selling plate form, you cannot suggest client to hike the price, if the client gives you price according to it, you will send thank you message like, thank you for all the information, let me confirm with all my team and they will get back to you..
             Here's the flow you should follow: 
             1. Greet the user warmly and ask how you can assist them. 
             2. If the user mentions selling a watch, ask for the model of the watch. 
             3. Once the model is provided, compliment the watch and ask for the year of purchase. 
            4. then ask if they have a price in mind
             5. Do you have original box and bill and warranty card with you? 
             6. do you have any ovbious marks scratches in your watch,
             7. Are you urgent in wanting to sell it? 
             8. If the user provides a price, thank them and let them know you'll confirm the details. 
             9. Got it, let me confirm some details with my team, can you send a photo of the watch??
            10.thank you for all the info let me share all the details according to you and get back to you. Throughout, maintain a friendly and professional tone, keeping the conversation respectful and smooth."""},
                
            ]

            # Append history to the messages if it exists
            if history:
                for line in history.splitlines():
                    if line.startswith("User:"):
                        messages.append({"role": "user", "content": line[6:]})
                    elif line.startswith("Assistant:"):
                        messages.append({"role": "assistant", "content": line[11:]})

            # Add the latest user message
            messages.append({"role": "user", "content": prompt})

            # Generate response from OpenAI API
            response = self.client.chat.completions.create(
                model="gpt-4o",  
                messages=messages,
                max_tokens=150,
                n=1,
                stop=None,
                temperature=0.7,
            )
            assistant_reply = response.choices[0].message.content.strip()

            # Save the new interaction to memory
            self.save_to_memory(wa_id, prompt, assistant_reply)

            return assistant_reply
        except Exception as e:
            logging.error(f"OpenAI API request failed: {e}")
            return "I'm sorry, but I couldn't process your request at the moment."


class WhatsAppAPI:
    def __init__(self, assistant):
        self.assistant = assistant

    # Send message to WhatsApp API
    def send_message(self, to, message):
        try:
            url = "https://crmapi.wa0.in/api/meta/v19.0/418218771378739/messages"
            payload = json.dumps({
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": to,
                "type": "text",
                "text": {
                    "preview_url": False,
                    "body": message
                }
            })
            headers = {
                'Content-Type': 'application/json',
                'Authorization': os.getenv("AUTH-salk")
            }

            response = requests.post(url, headers=headers, data=payload)

            if response.status_code == 200:
                logging.info("Message sent successfully!")
            else:
                logging.error(f"Failed to send message: {response.status_code} - {response.text}")

        except Exception as e:
            logging.error(f"Failed to send message to {to}: {e}")


# Flask application setup
app = Flask(__name__)
app.secret_key = "supersecretkey"
assistant = WatchSellingAssistant()
whatsapp_api = WhatsAppAPI(assistant)
image_ids_list = []

@app.route('/userChat', methods=['GET', 'POST'])
def user_chat():
    if request.method == 'GET':
        challenge = request.args.get('challenge') or request.args.get('challange')
        echo = request.args.get('echo', 'false').lower() == 'true'
        if challenge:
            if echo:
                app.logger.info("Echoing challenge.")
                return challenge, 200
            else:
                app.logger.info("Challenge received but not echoed.")
                return "Challenge received but not echoed.", 200
        app.logger.warning("No challenge parameter found.")
        return "No challenge", 400

    elif request.method == 'POST':
        if request.is_json:
            data = request.json
            # app.logger.info(f"This is the json ------- \n {data}")
            try:
                wa_id = data['entry'][0]['changes'][0]['value']['contacts'][0]['wa_id']
                # app.logger.info(f"Sender wa_id: {wa_id}")
                message_info = data['entry'][0]['changes'][0]['value']['messages'][0]
        
                 # Loop through messages and append image IDs
                messages = data['entry'][0]['changes'][0]['value']['messages']
                for message in messages:
                    if message['type'] == 'image':
                        image_id = message['image']['id']
                        # Append the image ID to the global list
                        image_ids_list.append(image_id)


                if message_info['type'] == 'image':
                    get_image(wa_id,image_ids_list)
                    res=process_images(wa_id)

                    # generate_image_response(message_info["image"])
                    # logging.info(message_info["image"])
                    

                    response_message = "Thanks for sharing the image; our team will contact you shortly."
                    app.logger.info(f"Response message: {response_message}")
                    whatsapp_api.send_message(wa_id, response_message)
                    return jsonify({"message": "Image processed"}), 200
                


                elif message_info['type'] == 'text':
                    body_content = message_info['text']['body']
                    app.logger.info(f"Body content: {body_content}")

                    assistant_response = assistant.get_assistant_response(wa_id, body_content)
                    app.logger.info(f"Assistant response: {assistant_response}")

                    whatsapp_api.send_message(wa_id, assistant_response)
                    return jsonify({"message": "Text processed"}), 200

                else:
                    app.logger.warning("Unhandled message type.")
                    return jsonify({"error": "Unhandled message type"}), 400

            except (KeyError, IndexError) as e:
                app.logger.error(f"Error extracting data: {e}")
                return jsonify({"error": "Invalid data format"}), 400

            except Exception as e:
                app.logger.error(f"Error processing message: {e}")
                return jsonify({"error": "Failed to process message"}), 500

        else:
            app.logger.error("Unsupported Media Type.")
            return jsonify({"error": "Unsupported Media Type"}), 415



if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app.run(debug=True, port=5000)
