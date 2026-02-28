import pycountry

def get_country_name(country_code):
    try:
        # Find the country by its alpha-2 country code
        country = pycountry.countries.get(alpha_2=country_code.upper())
        if country:
            return country.name
        else:
            return "Country code not found"
    except Exception as e:
        return str(e)

# Example usage
print(get_country_name("US"))  # Output: United States
print(get_country_name("ET")) 