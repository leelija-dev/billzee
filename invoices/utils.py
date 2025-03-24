# utils.py (in your app directory)
import random
import string

def generate_custom_invoice_id():
    characters = string.ascii_uppercase + string.digits
    random_string = ''.join(random.choices(characters, k=16))
    formatted_id = '-'.join([random_string[i:i+4] for i in range(0, 16, 4)])
    return formatted_id