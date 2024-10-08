from flask import Flask, request, jsonify
import requests
from datetime import datetime
import logging

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)

# Function to convert ISO 8601 date to human-readable format
def convert_to_human_readable_date(iso_date):
    try:
        # Strip 'Z' if it's present and convert to human-readable format
        date_obj = datetime.fromisoformat(iso_date.rstrip('Z'))
        return date_obj.strftime("%A, %d %b %Y")
    except ValueError:
        logging.error(f"Invalid date format encountered: {iso_date}")
        return "Not available"

# Function to handle hardcoded order (if any)
def handle_hardcoded_order(order_id):
    hardcoded_orders = {
        "31313": "2022-08-18T21:31:25.565Z"
    }
    
    if order_id in hardcoded_orders:
        logging.info(f"Order {order_id} is hardcoded. Returning hardcoded shipment date.")
        return convert_to_human_readable_date(hardcoded_orders[order_id])
    
    return None

# Function to sanitize the order ID (optional based on your order ID format)
def sanitize_order_id(order_id):
    sanitized_order_id = order_id.strip()
    if not sanitized_order_id or not sanitized_order_id.isdigit():  # Assuming valid order IDs are digits
        logging.warning(f"Sanitization failed for order ID: {order_id}")
        return None
    return sanitized_order_id

# Function to handle API call for non-hardcoded orders
def fetch_order_status_from_api(order_id):
    api_url = 'https://orderstatusapi-dot-organization-project-311520.uc.r.appspot.com/api/getOrderStatus'
    
    try:
        # Prepare the payload to send
        payload = {'orderId': order_id}
        headers = {'Content-Type': 'application/json'}
        
        # Log the outgoing request details
        logging.info(f"Sending API request for order ID {order_id}")
        
        # Send the POST request to the API
        response = requests.post(api_url, json=payload, headers=headers)
        
        # Log response status and content
        logging.info(f"API Response Status: {response.status_code}")
        
        # Handle invalid order ID (status code 400)
        if response.status_code == 400:
            logging.warning(f"Invalid order ID provided: {order_id}")
            return "The order ID is invalid. Please check and try again."
        
        # Handle general non-200 responses
        if response.status_code != 200:
            logging.error(f"API request failed with status code {response.status_code}")
            return f"Error: API request failed with status code {response.status_code}"

        # Parse the JSON response
        data = response.json()
        shipment_date = data.get('shipmentDate', 'Not available')
        
        logging.info(f"Shipment Date from API for order {order_id}: {shipment_date}")
        return convert_to_human_readable_date(shipment_date)

    except requests.exceptions.RequestException as e:
        logging.error(f"API request failed for order {order_id}: {str(e)}")
        return f"Error: Unable to fetch shipment date for order {order_id}. Details: {str(e)}"

@app.route('/webhook', methods=['POST'])
def webhook():
    req = request.get_json(silent=True, force=True)
    logging.info(f"Received request: {req}")

    # Extract the intent name to determine the flow
    intent_name = req['queryResult']['intent']['displayName']
    
    # Handle the 'Default Ending' intent with a thank you audio response
    if intent_name == 'Default Ending':
        audio_link = "https://welcome-audio.s3.eu-north-1.amazonaws.com/Heavens+Choir+Sound+Effect.mp3"
        response_audio = {
            'fulfillmentText': "You're welcome!",
            'fulfillmentMessages': [
                {"text": {"text": ["You're welcome!"]}},
                {
                    "payload": {
                        "google": {
                            "expectUserResponse": False,
                            "richResponse": {
                                "items": [
                                    {
                                        "simpleResponse": {
                                            "textToSpeech": "You're welcome!"
                                        }
                                    },
                                    {
                                        "mediaResponse": {
                                            "mediaType": "AUDIO",
                                            "mediaObjects": [
                                                {
                                                    "name": "Audio Response",
                                                    "contentUrl": audio_link,
                                                    "description": "Thank you music"
                                                }
                                            ]
                                        }
                                    }
                                ]
                            }
                        }
                    }
                }
            ]
        }
        return jsonify(response_audio)

    # Handle the 'Fetch Shipment details' intent
    elif intent_name == 'Fetch Shipment details':
        order_id = req['queryResult']['parameters'].get('orderid', 'Unknown')
        
        if order_id == 'Unknown':
            return jsonify({'fulfillmentText': "Sorry, I couldn't find the order ID."})

        sanitized_order_id = sanitize_order_id(order_id)
        
        if not sanitized_order_id:
            return jsonify({'fulfillmentText': "The order ID provided is invalid. Please check and try again."})

        # Check for hardcoded order first
        shipment_date = handle_hardcoded_order(sanitized_order_id)

        # If not hardcoded, attempt an API call
        if not shipment_date:
            shipment_date = fetch_order_status_from_api(sanitized_order_id)

        # Construct the response based on the result
        if "Error" in shipment_date:
            response_text = shipment_date
        else:
            response_text = f"The shipment date for order ID {sanitized_order_id} is {shipment_date}."
        
        return jsonify({'fulfillmentText': response_text})

    # Default case if the intent doesn't match any expected flow
    else:
        logging.error(f"Unhandled intent: {intent_name}")
        return jsonify({'fulfillmentText': "Sorry, I couldn't handle this request."})

# Start the Flask server
if __name__ == '__main__':
    app.run(port=5000, debug=True)
