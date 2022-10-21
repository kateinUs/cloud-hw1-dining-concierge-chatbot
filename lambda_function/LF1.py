import re
import os
import time
import json
import boto3
import datetime
import dateutil.parser
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)
queue_url = "https://sqs.us-east-1.amazonaws.com/987428913671/diningsqs"


# Function to handle greeting intent
def get_greeting_intent(intent_request):
    session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}
    return close(session_attributes, 'Fulfilled', {'contentType': 'PlainText',
                                                   'content': 'Hi, Welcome to Dining Conceirge Chatbot. How can I help you?'})


# Function to handle Goodbye intent
def get_thankyou_intent(intent_request):
    session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}
    return close(session_attributes, 'Fulfilled', {'contentType': 'PlainText',
                                                   'content': 'Thank you for using Dining Conceirge Chatbot. Have a nice day!'})


# Return template for dialog action type: ElicitSlot
def elicit_slot(session_attributes, intent_name, slots, slot_to_elicit, message):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'ElicitSlot',
            'intentName': intent_name,
            'slots': slots,
            'slotToElicit': slot_to_elicit,
            'message': message
        }
    }


# Return template for dialog action type: Close
def close(session_attributes, fulfillment_state, message):
    response = {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Close',
            'fulfillmentState': fulfillment_state,
            'message': message
        }
    }

    return response


# Return template for dialog action type: Delegate
def delegate(session_attributes, slots):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Delegate',
            'slots': slots
        }
    }


# Function check invalid date
def check_invalid_date(date):
    try:
        input_date = dateutil.parser.parse(date).date()
        if (input_date < datetime.date.today()):
            return True
        else:
            return False
    except ValueError:
        return False


# Function check invalid time
def check_invalid_time(time, date):
    try:
        input_time = dateutil.parser.parse(time).timestamp()
        input_date = dateutil.parser.parse(date).date()
        if ((input_date == datetime.date.today()) and (input_time < datetime.datetime.now().timestamp())):
            return True
        else:
            return False

    except ValueError:
        return False


# Function check invalid email id
def check_invalid_email(email):
    regex = re.compile(r'([A-Za-z0-9]+[.-_])*[A-Za-z0-9]+@[A-Za-z0-9-]+(\.[A-Z|a-z]{2,})+')
    if re.fullmatch(regex, email):
        return False
    else:
        return True


# Function check invalid phone number
def check_invalid_phone(phone):
    phone_re = re.compile(r'\(?\d{3}\)?[. -]?\d{3}[. -]?\d{4}')
    res = re.findall(phone_re, phone)
    for r in res:
        print("find phone #", r)
    if res:
        return False
    else:
        return True


# Function check invalid cuisine
def check_invalid_cuisine(cuisine):
    cuisines = ['indian', 'italian', 'mexican', 'chinese', 'japanese', 'french', 'korean', 'thai', 'american',
                'viatnamese']
    if cuisine.lower() not in cuisines:
        return True
    else:
        return False


# Function check invalid location
def check_invalid_location(location):
    if location.lower() != 'manhattan':
        return True
    else:
        return False


# Function check invalid number of people
def check_invalid_people(numOfPeople):
    if (numOfPeople < 1 or numOfPeople > 20):
        return True
    else:
        return False


# Function that handles dining suggestions intent and passes value to SQS.
def get_dining_suggestions_intent(intent_request):
    slots = intent_request['currentIntent']['slots']
    cuisineType = slots['cuisineType']
    location = slots['location']
    diningDate = slots['diningDate']
    diningTime = slots['diningTime']
    numOfPeople = slots['numOfPeople']
    emailAddress = slots['emailAddress']
    phoneNumber = slots['phoneNumber']

    session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}

    if numOfPeople is not None:
        numOfPeople = int(numOfPeople)
    else:
        numOfPeople = None

    if intent_request['invocationSource'] == 'DialogCodeHook':
        invalid_slot = None
        invalid_message = None

        if cuisineType and check_invalid_cuisine(cuisineType):
            invalid_slot = 'cuisineType'
            invalid_message = 'This cuisine is not supported by the Dining Conceirge Bot. Please provide another cuisine. You can choose from the likes of chinese, indian, italian, thai, etc'

        elif location and check_invalid_location(location):
            invalid_slot = 'location'
            invalid_message = 'This location is not supported by the Dining Conceirge Bot. Please provide another city like Manhattan.'

        elif diningDate and check_invalid_date(diningDate):
            invalid_slot = 'diningDate'
            invalid_message = 'The entered date is invalid. Please make sure that your date is later than today\'s date. What date do you want suggestions for?'

        elif diningTime and check_invalid_time(diningTime, diningDate):
            invalid_slot = 'diningTime'
            invalid_message = 'The entered time is invalid. Please make sure that your time is later than current time. What time do you want suggestions for?'

        elif numOfPeople is not None and check_invalid_people(numOfPeople):
            invalid_slot = 'numOfPeople'
            invalid_message = 'You can only get suggestions for 1 - 20 people. Please provide correct number of people.'

        elif emailAddress and check_invalid_email(emailAddress):
            invalid_slot = 'emailAddress'
            invalid_message = 'The email is not in the right format. Please provide the correct email so that suggestions can be mailed.'

        elif phoneNumber and check_invalid_phone(phoneNumber):
            invalid_slot = 'phoneNumber'
            invalid_message = 'The phone number is not in the right format. Please provide the correct phone number.'

        if invalid_slot:
            slots[invalid_slot] = None
            return elicit_slot(session_attributes, intent_request['currentIntent']['name'], slots, invalid_slot,
                               {'contentType': 'PlainText', 'content': invalid_message})

        return delegate(session_attributes, slots)

    # Sending slot values using SQS for querying purposes
    sqs_client = boto3.client('sqs')

    response = sqs_client.send_message(
        QueueUrl=queue_url,
        DelaySeconds=10,
        MessageAttributes={
            'location': {
                'DataType': 'String',
                'StringValue': location
            },
            'cuisineType': {
                'DataType': 'String',
                'StringValue': cuisineType
            },
            'diningDate': {
                'DataType': 'String',
                'StringValue': diningDate
            },
            'numOfPeople': {
                'DataType': 'Number',
                'StringValue': "{}".format(numOfPeople)
            },
            'diningTime': {
                'DataType': 'String',
                'StringValue': diningTime
            },
            'emailAddress': {
                'DataType': 'String',
                'StringValue': emailAddress
            },
            'phoneNumber': {
                'DataType': 'String',
                'StringValue': phoneNumber
            }
        },
        MessageBody=(
            'Input from the user through Dining Conceirge Chatbot'
        )
    )
    logger.info(f"LF1: 1 MSG sent {response}")

    return close(session_attributes, 'Fulfilled', {'contentType': 'PlainText',
                                                   'content': 'Thanks for the info. You will soon receive the suggestions via {} !'.format(
                                                       emailAddress)})


# Function that routes different utterances according to the detected intent
def route_intent(intent_request):
    intent_name = intent_request['currentIntent']['name']

    if intent_name == 'GreetingIntent':
        return get_greeting_intent(intent_request)

    elif intent_name == 'DiningSuggestionsIntent':
        return get_dining_suggestions_intent(intent_request)

    elif intent_name == 'ThankYouIntent':
        return get_thankyou_intent(intent_request)


# Main Lambda Function that receives input
def lambda_handler(event, context):
    os.environ["TZ"] = 'America/New_York'
    time.tzset()

    return route_intent(event)