import json

config = {}
propCol = config.get('proportion') if config else 'สถานการณ์'
print(f"propCol in python would be: {propCol}")
# In JS: let propCol = config ? config.proportion : 'สถานการณ์';
# In JS, if config is {}, config is truthy, so config.proportion is undefined.
