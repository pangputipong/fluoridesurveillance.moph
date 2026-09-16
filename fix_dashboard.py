import re

with open('static/js/dashboard.js', 'r', encoding='utf-8') as f:
    content = f.read()

old_logic = '''            let apiToDbRefMap = {
                'ชนิดน้ำ': 'water_type',
                'ปริมาณฟลูออไรด์': 'fluoride_level'
            };

            schemaKeys.forEach(k => {
                let colName = k.name;
                let dbRef = k.db_ref;
                let val = null;

                if (apiToDbRefMap[colName]) {
                    val = d[colName];
                } else if (apiToDbRefMap[dbRef]) {
                    val = d[apiToDbRefMap[dbRef]];
                } else if (d[colName] !== undefined) {
                    val = d[colName];
                } else {
                    val = d[dbRef];
                }'''

new_logic = '''            // Map the API output keys to the DB column references used by the chart logic
            let apiToDbRefMap = {
                'ชนิดน้ำ': 'water_type',
                'ปริมาณฟลูออไรด์': 'fluoride_level'
            };
            
            let dbRefToApiMap = {
                'water_type': 'ชนิดน้ำ',
                'fluoride_level': 'ปริมาณฟลูออไรด์',
                'location_name': 'สถานที่เก็บ',
                '[water_type]': 'ชนิดน้ำ'
            };

            schemaKeys.forEach(k => {
                let colName = k.name;
                let dbRef = k.db_ref;
                let val = null;

                if (dbRefToApiMap[dbRef] && d[dbRefToApiMap[dbRef]] !== undefined) {
                    val = d[dbRefToApiMap[dbRef]];
                } else if (apiToDbRefMap[colName] && d[colName] !== undefined) {
                    val = d[colName];
                } else if (d[colName] !== undefined) {
                    val = d[colName];
                } else {
                    val = d[dbRef];
                }'''

if old_logic in content:
    content = content.replace(old_logic, new_logic)
    print("Replaced logic successfully!")
else:
    print("Could not find old_logic")

with open('static/js/dashboard.js', 'w', encoding='utf-8') as f:
    f.write(content)
