import os

def get_google_maps_api_key():
    return os.getenv('GOOGLE_MAPS_API_KEY', 'YOUR_API_KEY_HERE')

def get_static_map_url(lat, lng):
    api_key = get_google_maps_api_key()
    return f"https://maps.googleapis.com/maps/api/staticmap?center={lat},{lng}&zoom=15&size=600x300&markers=color:red%7C{lat},{lng}&key={api_key}"

def ai_triage_suggestion(issue_description):
    """
    Simulated AI logic to suggest common fixes or prioritize jobs.
    """
    desc = issue_description.lower()
    if 'leak' in desc:
        return "Priority: High. Suggestion: Inspect mounting brackets and roofing seals immediately."
    elif 'no power' in desc or 'off' in desc:
        return "Priority: Medium. Suggestion: Check inverter status lights and circuit breakers."
    elif 'cleaning' in desc or 'dirty' in desc:
        return "Priority: Low. Suggestion: Schedule routine cleaning. Most likely dust accumulation."
    else:
        return "Common Issue. Suggestion: Verify panel connections and check for shading."
