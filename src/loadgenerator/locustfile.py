#!/usr/bin/python
#
# Copyright 2018 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import random
from locust import HttpUser, TaskSet, between

products = [
    '0PUK6V6EV0',
    '1YMWWN1N4O',
    '1YMWWN1N4O',
    '2ZYFJ3GM2N',
    '66VCHSJNUP',
    '6E92ZMYYFZ',
    '9SIQT8TOJO',
    'L9ECAV7KIM',
    'LS4PSXUNUM',
    'OLJCESPC7Z']

def index(l):
    l.client.get("/")

def setCurrency(l):
    currencies = ['EUR', 'USD', 'JPY', 'CAD']
    l.client.post("/setCurrency",
        {'currency_code': random.choice(currencies)})

def browseProduct(l):
    l.client.get("/product/" + random.choice(products))

def viewCart(l):
    l.client.get("/cart")

def addToCart(l):
    product = random.choice(products)
    l.client.get("/product/" + product)
    l.client.post("/cart", {
        'product_id': product,
        'quantity': random.choice([1,2,3,4,5,10])})

users = [
    {
        'email': 'pokemonmaster@example.com',
        'street_address': '1600 Amphitheatre Parkway',
        'zip_code': '94043',
        'city': 'Mountain View',
        'state': 'CA',
        'country': 'United States',
        'credit_card_number': '4432-8015-6152-0454',
        'credit_card_expiration_month': '1',
        'credit_card_expiration_year': '2039',
        'credit_card_cvv': '672',
    },
    {
        'email': 'bob.smith@example.com',
        'street_address': '1 Infinite Loop',
        'zip_code': '95014',
        'city': 'Cupertino',
        'state': 'CA',
        'country': 'United States',
        'credit_card_number': '4111-1111-1111-1111',
        'credit_card_expiration_month': '6',
        'credit_card_expiration_year': '2028',
        'credit_card_cvv': '737',
    },
    {
        'email': 'carol.white@example.com',
        'street_address': '350 Fifth Avenue',
        'zip_code': '10118',
        'city': 'New York',
        'state': 'NY',
        'country': 'United States',
        'credit_card_number': '4539-1488-0343-6467',
        'credit_card_expiration_month': '9',
        'credit_card_expiration_year': '2027',
        'credit_card_cvv': '284',
    },
    {
        'email': 'david.lee@example.com',
        'street_address': '233 S Wacker Dr',
        'zip_code': '60606',
        'city': 'Chicago',
        'state': 'IL',
        'country': 'United States',
        'credit_card_number': '4916-3383-0477-2894',
        'credit_card_expiration_month': '3',
        'credit_card_expiration_year': '2030',
        'credit_card_cvv': '519',
    },
    {
        'email': 'pokemonmaster@example.com',
        'street_address': '1301 Fannin St',
        'zip_code': '77002',
        'city': 'Houston',
        'state': 'TX',
        'country': 'United States',
        'credit_card_number': '4556-7375-8689-9855',
        'credit_card_expiration_month': '11',
        'credit_card_expiration_year': '2031',
        'credit_card_cvv': '963',
    },
    {
        'email': 'eve.martinez@example.com',
        'street_address': '500 W Madison St',
        'zip_code': '60661',
        'city': 'Chicago',
        'state': 'IL',
        'country': 'United States',
        'credit_card_number': '4532-0151-1283-0366',
        'credit_card_expiration_month': '8',
        'credit_card_expiration_year': '2025',  # triggers SpecificYearCreditCardError (#15-17)
        'credit_card_cvv': '412',
    },
]

def checkout(l):
    addToCart(l)
    user = random.choice(users)
    l.client.post("/cart/checkout", user)

class UserBehavior(TaskSet):

    def on_start(self):
        index(self)

    tasks = {index: 1,
        setCurrency: 2,
        browseProduct: 10,
        addToCart: 2,
        viewCart: 3,
        checkout: 1}

class WebsiteUser(HttpUser):
    tasks = [UserBehavior]
    wait_time = between(1, 10)
