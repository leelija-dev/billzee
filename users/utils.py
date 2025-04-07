from django.core.cache import cache
import requests

def get_country_choices():
    """
    Fetch country choices from an API and cache the results for 24 hours.
    Always show 'India' as the first choice.
    """
    choices = cache.get('country_choices')

    if choices is None:
        try:
            url = "https://countriesnow.space/api/v0.1/countries/iso"
            response = requests.get(url, timeout=5)  # Set timeout to avoid long waits

            if response.status_code == 200:
                data = response.json()

                if 'data' in data:
                    countries = data['data']

                    # Extract country codes correctly (handling uppercase keys)
                    choices = [(country.get('Iso2', ''), country.get('name', '')) for country in countries]

                    # Ensure valid choices
                    choices = [(code, name) for code, name in choices if code and name]

                    # Sort by country name
                    choices.sort(key=lambda x: x[1])
                else:
                    raise ValueError("Unexpected API response format")
            else:
                raise Exception(f"API response error: {response.status_code}")

        except Exception as e:
            print(f"Error fetching countries: {e}")
            choices = []

        # Always ensure India is the first choice
        choices.insert(0, ('IN', 'India'))

        # Cache results for 24 hours
        cache.set('country_choices', choices, timeout=86400)

    return choices
