#!/usr/bin/env python
# coding: utf-8

import requests
import json
import os
import datetime
import boto3
from decimal import Decimal
from requests_aws4auth import AWS4Auth
from opensearchpy import OpenSearch, RequestsHttpConnection

# from requests_aws4auth import AWS4Auth
# from opensearchpy import OpenSearch, RequestsHttpConnection

# Dictionary for checking for duplicate restaurants
restaurant_dict = {}


def check_for_none(value):
    try:
        if value is None or len(str(value)) == 0:
            return True
        return False
    except:
        return True


def format_restaurants(restaurant, location, cuisine_type):
    """
    This Function is used to Restaurant Dictionary

    Parameters:
    restaurant (dictionary): Dictionary containing restaurant information

    location(string): The location of the restaurants

    cuisine_type(String): cuisine type of the restaurant

    Returns:
    restaurant_format(Dictionary): Formatted Dictionary  of restaurants

    """
    restaurant_format = {}
    restaurant_dict[restaurant['id']] = 1
    restaurant_format['id'] = restaurant['id']
    restaurant_format['insertedAtTimestamp'] = str(datetime.datetime.now())
    if cuisine_type == 'indpak':
        cuisine_type = 'indian'
    restaurant_format['cuisine_type'] = cuisine_type
    restaurant_format['name'] = restaurant['name']
    restaurant_format['url'] = restaurant['url']
    if not check_for_none(restaurant.get("rating", None)):
        restaurant_format["rating"] = Decimal(restaurant["rating"])
    if not check_for_none(restaurant.get("coordinates", None)):
        restaurant_format["latitude"] = Decimal(str(restaurant["coordinates"]["latitude"]))
        restaurant_format["longitude"] = Decimal(str(restaurant["coordinates"]["longitude"]))
    if not check_for_none(restaurant.get("phone", None)):
        restaurant_format["contact"] = restaurant["phone"]
    if not check_for_none(restaurant.get("review_count", None)):
        restaurant_format["review_count"] = restaurant["review_count"]
    if not check_for_none(restaurant.get("price", None)):
        restaurant_format["price"] = restaurant["price"]
    if restaurant.get('location', None) is not None:
        address = ""
        for i in restaurant['location']['display_address']:
            address += i
        restaurant_format['address'] = address
        restaurant_format["zip_code"] = restaurant['location']['zip_code']
    return restaurant_format


def get_yelp_data(api, api_key):
    """
    This Function is used to scrap data from Yelp API

    Parameters:
    api (string): API of yelp

    api_key(string): API key for using Yelp API

    Returns:
    restaurant_list(list): returns list of restaurants

    """
    headers = {"Authorization": "Bearer " + api_key}
    cuisine_list = ['indpak', 'italian', 'mexican', 'chinese', 'japanese', 'french', 'thai', 'korean']
    # cuisine_list = ['indpak']
    location = 'manhattan'
    # list to store all the restaurant dictionaries
    restaurant_list = []
    for cuisine in cuisine_list:
        responses_total = 1000
        offset = 0
        query = "?location={}".format(location) + "&categories={}".format(cuisine) + "&limit=50&offset=" + str(offset)
        response = requests.get(api + query, headers=headers).json()
        print("GET YELP DATA: 1")
        while responses_total > 0:
            if response.get("businesses", None) is not None:
                restaurants_in_current_page = response["businesses"]
                responses_in_current_page = len(restaurants_in_current_page)
                for restaurant in restaurants_in_current_page:
                    if restaurant['id'] in restaurant_dict:
                        # Checking for duplicate restaurants
                        continue
                    # formating restaurent dictionary
                    formatted_restaurant = format_restaurants(restaurant, location, cuisine)
                    restaurant_list.append(formatted_restaurant)
                responses_total = responses_total - responses_in_current_page
                # checking if there are no restaurants in current page or the responses scraped is enough
                if responses_in_current_page == 0 or responses_total <= 0:
                    break
                # updating offset to go to another page
                offset += responses_in_current_page
                query = "?location={}".format(location) + "&categories={}".format(cuisine) + "&limit=50&offset=" + str(
                    offset)
                # going to another page
                response = requests.get(api + query, headers=headers).json()
                print("GET YELP DATA: 2")
            else:
                break

    return restaurant_list


def send_to_dynamodb(aws_access_key_id, aws_secret_access_key, region_name, restaurant_list):
    dynamodb = boto3.resource('dynamodb', aws_access_key_id=aws_access_key_id,
                              aws_secret_access_key=aws_secret_access_key, region_name=region_name)
    table = dynamodb.Table('yelp-restaurants')
    for restaurant in restaurant_list:
        # sending the restaurant dictionaries to dynamodb
        table.put_item(Item=restaurant)
    print("INSERT TO DYNAMODB DONE")


def send_to_es(restaurant_list, es_host, es_port, es_http_auth):
    index_name = 'restaurants'
    index_body = {
        'settings': {
            'index': {
                'number_of_shards': 4
            }
        }
    }
    # Create an Open Search Client
    client = OpenSearch(
        hosts=[{'host': es_host, 'port': es_port}],
        http_auth=es_http_auth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection
    )
    # Creating an index
    client.indices.create(index_name, body=index_body)
    for restaurant in restaurant_list:
        # Sending restaurant information to index
        client.index(index='restaurants', id=restaurant["id"], body={
            "cuisine": restaurant["cuisine_type"],
        })
    print("INSERT TO ES DONE")


if __name__ == '__main__':
    # credentials definition
    # yelp api key
    api_key = '[YELP_API_KEY]'
    api = 'https://api.yelp.com/v3/businesses/search'
    # your aws access key id and secret access key
    aws_access_key_id = '[YOUR_AWS_ACCESS_KEY_ID]'
    aws_secret_access_key = '[YOUR_AWS_SECRET_ACCESS_KEY]'
    region_name = 'us-east-1'

    # Open search username and password
    es_username = "huiminzhang"
    es_password = "[OPEN_SEARCH_PASSWORD]"
    es_host = 'search-search-yelp-kl4detfhabfrbcdqltkinliak4.us-east-1.es.amazonaws.com'
    es_port = 443
    es_http_auth = (es_username, es_password)

    # get yelp data
    restaurant_list = get_yelp_data(api, api_key)
    restaurant_len = len(restaurant_list)
    print("Num of restaurants get: ", restaurant_len)
    print("DONE WITH GETTING RESTAURANT LIST")

    send_to_dynamodb(aws_access_key_id, aws_secret_access_key, region_name, restaurant_list)

    send_to_es(restaurant_list, es_host, es_port, es_http_auth)
    print("SUCCESS DONE ")
    """
    ###  TEST INSERT DYNAMODB
    dynamodb = boto3.resource('dynamodb', aws_access_key_id=aws_access_key_id,
                              aws_secret_access_key=aws_secret_access_key, region_name=region_name)
    table = dynamodb.Table('yelp-restaurants')
    table.put_item(Item={
        "id": "TEST FROM MY COMP",
        "insertedAtTimestamp": str(datetime.datetime.now())
    })
    print("INSERT DONE")
    """