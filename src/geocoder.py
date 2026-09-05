from typing import Optional, Tuple, Dict
import reverse_geocoder as rg

# ISO-3166-1 alpha-2 to English full country name mapping for common countries
COUNTRY_NAMES: Dict[str, str] = {
    "AD": "Andorra", "AE": "United Arab Emirates", "AF": "Afghanistan", "AG": "Antigua and Barbuda",
    "AL": "Albania", "AM": "Armenia", "AO": "Angola", "AR": "Argentina", "AT": "Austria",
    "AU": "Australia", "AZ": "Azerbaijan", "BA": "Bosnia and Herzegovina", "BB": "Barbados",
    "BD": "Bangladesh", "BE": "Belgium", "BF": "Burkina Faso", "BG": "Bulgaria", "BH": "Bahrain",
    "BI": "Burundi", "BJ": "Benin", "BO": "Bolivia", "BR": "Brazil", "BS": "Bahamas",
    "BT": "Bhutan", "BW": "Botswana", "BY": "Belarus", "BZ": "Belize", "CA": "Canada",
    "CH": "Switzerland", "CI": "Ivory Coast", "CL": "Chile", "CM": "Cameroon", "CN": "China",
    "CO": "Colombia", "CR": "Costa Rica", "CU": "Cuba", "CY": "Cyprus", "CZ": "Czech Republic",
    "DE": "Germany", "DK": "Denmark", "DO": "Dominican Republic", "DZ": "Algeria", "EC": "Ecuador",
    "EE": "Estonia", "EG": "Egypt", "ES": "Spain", "ET": "Ethiopia", "FI": "Finland",
    "FJ": "Fiji", "FR": "France", "GA": "Gabon", "GB": "United Kingdom", "GE": "Georgia",
    "GH": "Ghana", "GR": "Greece", "GT": "Guatemala", "HR": "Croatia", "HU": "Hungary",
    "ID": "Indonesia", "IE": "Ireland", "IL": "Israel", "IN": "India", "IQ": "Iraq",
    "IR": "Iran", "IS": "Iceland", "IT": "Italy", "JM": "Jamaica", "JO": "Jordan",
    "JP": "Japan", "KE": "Kenya", "KR": "South Korea", "KW": "Kuwait", "KZ": "Kazakhstan",
    "LB": "Lebanon", "LI": "Liechtenstein", "LK": "Sri Lanka", "LT": "Lithuania", "LU": "Luxembourg",
    "LV": "Latvia", "MA": "Morocco", "MC": "Monaco", "MD": "Moldova", "ME": "Montenegro",
    "MG": "Madagascar", "MK": "North Macedonia", "MT": "Malta", "MU": "Mauritius", "MX": "Mexico",
    "MY": "Malaysia", "NA": "Namibia", "NG": "Nigeria", "NL": "Netherlands", "NO": "Norway",
    "NP": "Nepal", "NZ": "New Zealand", "OM": "Oman", "PA": "Panama", "PE": "Peru",
    "PH": "Philippines", "PK": "Pakistan", "PL": "Poland", "PT": "Portugal", "PY": "Paraguay",
    "QA": "Qatar", "RO": "Romania", "RS": "Serbia", "RU": "Russia", "RW": "Rwanda",
    "SA": "Saudi Arabia", "SE": "Sweden", "SG": "Singapore", "SI": "Slovenia", "SK": "Slovakia",
    "SM": "San Marino", "SN": "Senegal", "TH": "Thailand", "TN": "Tunisia", "TR": "Turkey",
    "TT": "Trinidad and Tobago", "TW": "Taiwan", "TZ": "Tanzania", "UA": "Ukraine", "UG": "Uganda",
    "US": "United States", "UY": "Uruguay", "UZ": "Uzbekistan", "VA": "Vatican City", "VE": "Venezuela",
    "VN": "Vietnam", "ZA": "South Africa", "ZM": "Zambia", "ZW": "Zimbabwe"
}

_GEO_CACHE: Dict[Tuple[float, float], str] = {}


def reverse_geocode(lat: Optional[float], lon: Optional[float]) -> str:
    """Reverse-geocodes (lat, lon) coordinates to 'City, Country' with offline caching."""
    if lat is None or lon is None:
        return ""
    
    # Round coordinates to 3 decimals (~110m precision) for cache hits
    coord_key = (round(lat, 3), round(lon, 3))
    if coord_key in _GEO_CACHE:
        return _GEO_CACHE[coord_key]
    
    try:
        results = rg.search((lat, lon), mode=1)
        if not results:
            _GEO_CACHE[coord_key] = ""
            return ""
        
        info = results[0]
        city = info.get("name", "").strip()
        cc = info.get("cc", "").strip().upper()
        country = COUNTRY_NAMES.get(cc, cc)
        
        if city and country:
            formatted = f"{city}, {country}"
        elif city:
            formatted = city
        elif country:
            formatted = country
        else:
            formatted = ""
            
        _GEO_CACHE[coord_key] = formatted
        return formatted
    except Exception:
        _GEO_CACHE[coord_key] = ""
        return ""
