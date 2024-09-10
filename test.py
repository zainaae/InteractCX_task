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
        date_obj = datetime.fromisoformat(iso_date[:-1])  # Remove 'Z' and parse
        return date_obj.strftime("%A, %d %b %Y")
    except ValueError:
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

# Function to handle API call for non-hardcoded orders
def fetch_order_status_from_api(order_id):
    api_url = 'https://orderstatusapi-dot-organization-project-311520.uc.r.appspot.com/api/getOrderStatus'
    
    try:
        # Prepare the payload to send
        payload = {'orderId': order_id}
        headers = {'Content-Type': 'application/json'}  # Explicitly set content-type header
        
        # Log the outgoing request details
        logging.info(f"Sending API request for order ID {order_id} with payload: {payload}")
        
        # Send the POST request to the API
        response = requests.post(api_url, json=payload, headers=headers)
        
        # Log the status code and response
        logging.info(f"API Response Status: {response.status_code}")
        logging.info(f"API Response Content: {response.content}")

        # Check if the response is successful (status code 200)
        if response.status_code != 200:
            return f"Error: API request failed with status code {response.status_code}"

        # Try to parse the JSON response
        data = response.json()
        shipment_date = data.get('shipmentDate', 'Not available')
        
        logging.info(f"Shipment Date from API: {shipment_date}")
        return convert_to_human_readable_date(shipment_date)

    except requests.exceptions.RequestException as e:
        logging.error(f"API request failed for order {order_id}: {str(e)}")
        return f"Error: Unable to fetch shipment date for order {order_id}. Details: {str(e)}"

@app.route('/webhook', methods=['POST'])
def webhook():
    req = request.get_json(silent=True, force=True)
    logging.info(f"Received request: {req}")

    # Extract intent name to determine the flow
    intent_name = req['queryResult']['intent']['displayName']
    
    # If the intent is 'Ending', just send the thank you response with audio
    if intent_name == 'Default Ending':
        audio_link = "https://www.dropbox.com/scl/fi/tq3cc782qlmstn8m81kov/Heavens-Choir-Sound-Effect.mp3?rlkey=8ymiu2yz5ssov3af2a50hvvub&st=1yv03qk1&raw=1"
        response_audio = {
            'fulfillmentText': "You're welcome!",
            'fulfillmentMessages': [
                {
                    "text": {
                        "text": ["You're welcome!"]
                    }
                },
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

    # Otherwise, handle the order inquiry
    elif intent_name == 'Fetch Shipment details':
        order_id = req['queryResult']['parameters'].get('orderid', 'Unknown')
        if order_id == 'Unknown':
            return jsonify({'fulfillmentText': "Sorry, I couldn't find the order ID."})

        # Check for hardcoded order first
        shipment_date = handle_hardcoded_order(order_id)

        # If not hardcoded, attempt API call
        if not shipment_date:
            shipment_date = fetch_order_status_from_api(order_id)

        # Construct response
        if "Error" in shipment_date:
            response_text = shipment_date
        else:
            response_text = f"The shipment date for order ID {order_id} is {shipment_date}."
        
        return jsonify({'fulfillmentText': response_text})

    # Default case if intent doesn't match any expected
    else:
        return jsonify({'fulfillmentText': "Sorry, I couldn't handle this request."})

# Start the Flask server
if __name__ == '__main__':
    app.run(port=5000, debug=True)
