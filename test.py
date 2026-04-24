# import requests

# headers = {
#     "Authorization": "865|n7d3TOQgYAp6lwemzAUrPQ3T37F66NvHkTsxW72S10b3c7cb",  # Replace with your actual Bearer token
# }
# params = {
#     "account_number": "8143220988",
#     "bank_code": "100004",
# }
# response = requests.get("https://nubapi.com/api/verify", headers=headers, params=params)

# print("Status Code:", response.status_code)
# print("Response Text:", response.text)

# if response.status_code == 200:
#     try:
#         data = response.json()

#         print(f"Account Name: {data.get('account_name')}")
#         print(f"First Name: {data.get('first_name')}")
#         print(f"Last Name: {data.get('last_name')}")
#         print(f"Other Name: {data.get('other_name')}")
#         print(f"Account Number: {data.get('account_number')}")
#         print(f"Bank Code: {data.get('bank_code')}")
#         print(f"Bank Name: {data.get('bank_name')}")
#     except requests.exceptions.JSONDecodeError:
#         print("Response is not valid JSON.")
# else:
#     print(f"Request failed: {response.status_code}")


import requests

API_KEY = "865|n7d3TOQgYAp6lwemzAUrPQ3T37F66NvHkTsxW72S10b3c7cb"

url = "https://nubapi.com/api/verify"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Accept": "application/json",
}

params = {
    "account_number": "8143220988",
    "bank_code": "100004",
}

response = requests.get(url, headers=headers, params=params)

print("Status:", response.status_code)
print("Content-Type:", response.headers.get("Content-Type"))
print("Response:", response.text)

data = response.json()

print(f"Account Name: {data.get('account_name')}")
print(f"First Name: {data.get('first_name')}")
print(f"Last Name: {data.get('last_name')}")
print(f"Other Name: {data.get('other_name')}")
print(f"Account Number: {data.get('account_number')}")
print(f"Bank Code: {data.get('bank_code')}")
print(f"Bank Name: {data.get('bank_name')}")
