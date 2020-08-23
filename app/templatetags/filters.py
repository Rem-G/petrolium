from django.template.defaulttags import register
@register.filter
def get_item(dictionary, key):
    print(dictionary, key)
    return dictionary.get(key)

@register.filter
def get_ferme(dictionary, key):
    key = key.lower()
    if dictionary.get(key):
        return dictionary.get(key).get('ferme')
    return None

@register.filter
def get_ouverture(dictionary, key):
    key = key.lower()
    if dictionary.get(key):
        return dictionary.get(key).get('ouverture')
    return None

@register.filter
def get_fermeture(dictionary, key):
    key = key.lower()
    if dictionary.get(key):
        return dictionary.get(key).get('fermeture')
    return None

@register.filter
def get_infos_available(dictionary, key):
    if get_fermeture(dictionary, key) or get_ouverture(dictionary, key) or get_ferme(dictionary, key):
        return True
    return False

@register.filter
def get_automate(dictionary):
    if dictionary and dictionary.get('automate'):
        return dictionary.get('automate')
    return False
