import requests
import json

url_generate = 'http://backend:8000/generate-response'

def get_response(input):
    data = {"session_id": "222", "request": input}
    API_response = requests.post(url_generate, json=data)
    if API_response.status_code != 200:
        return "Error: " + str(API_response.status_code)
    else:
        API_response_data = API_response.json()
        print(API_response_data)
        response = API_response_data['response']
        summary = API_response_data['summarized_response']
        if summary == "None":
            return response
        else:
            return summary

def get_num_conversations(input):
    url_get_num_conversations = 'http://backend:8000/history/' + input['session_id']
    API_response = requests.get(url_get_num_conversations)
    if API_response.status_code != 200:
        return "Error: " + str(API_response.status_code)
    else:
        API_response_data = API_response.json()
        return API_response_data['num_conversations']

def delete_history(input):
    url_delete = 'http://backend:8000/delete-history/' + input['session_id']
    response = requests.delete(url_delete).text
    return response