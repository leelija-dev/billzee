# utils.py (in your app directory)
import random
import string
import io
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa

def generate_custom_invoice_id():
    characters = string.ascii_uppercase + string.digits
    random_string = ''.join(random.choices(characters, k=16))
    formatted_id = '-'.join([random_string[i:i+4] for i in range(0, 16, 4)])
    return formatted_id


def render_to_pdf(template_src, context_dict={}):
    template = get_template(template_src)
    html  = template.render(context_dict)
    result = io.BytesIO()
    pdf = pisa.pisaDocument(io.BytesIO(html.encode("UTF-8")), result)
    if not pdf.err:
        return result.getvalue()
    return None