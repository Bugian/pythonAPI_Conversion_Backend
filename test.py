from flask import Flask, jsonify, request, abort

app = Flask(__name__)

# Conversii disponibile
conversions = {
    "mass": {"kg": 1, "g": 1000, "mg": 1000000, "pound": 2.20462},
    "length": {"km": 1, "m": 1000, "cm": 100000, "mile": 0.621371},
    "energy": {"kW": 1, "W": 1000, "MW": 0.001}
}

# Stocare temporară a conversiilor efectuate
history = []

def calculcate_conversion(unit_type, from_unit, to_unit, value):
    result = value * (conversions[unit_type][to_unit] / conversions[unit_type][from_unit])
    return round(result, 6)

@app.route('/')
def home():
    return "Bun venit la API-ul de conversii de unități!"

# GET Obținerea tuturor conversiilor efectuate
@app.route('/convert', methods=['GET'])
def get_conversions():
    return jsonify(history)

# GET Obținerea unei conversii după index
@app.route('/convert/<int:conversion_id>', methods=['GET'])
def get_conversion_by_id(conversion_id):
    conversion = next((c for c in history if c["id"] == conversion_id), None)
    if conversion is None:
        abort(404, description="Conversia nu a fost găsită")
    return jsonify(conversion)

# POST Adăugarea unei noi conversii
@app.route('/convert', methods=['POST'])
def add_conversion():
    data = request.get_json()
    unit_type = data.get('type')
    from_unit = data.get('from')
    to_unit = data.get('to')
    value = data.get('value')
    
    if not unit_type or not from_unit or not to_unit or value is None:
        abort(400, description="Lipsesc parametrii necesari: type, from, to, value")
    
    if unit_type not in conversions or from_unit not in conversions[unit_type] or to_unit not in conversions[unit_type]:
        abort(400, description="Tip de unitate sau unități invalide")
    
    converted_value = value * (conversions[unit_type][to_unit] / conversions[unit_type][from_unit])
    
    conversion = {
        "id": len(history) + 1,
        "original": {"value": value, "unit": from_unit},
        "converted": {"value": converted_value, "unit": to_unit}
    }
    history.append(conversion)
    
    return jsonify(conversion), 201

# PUT Actualizarea unei conversii existente
@app.route('/convert/<int:conversion_id>', methods=['PUT'])
def update_conversion(conversion_id):
    if not request.is_json:
        abort(415, description="Cererea trebuie să fie de tip JSON")

    conversion = next((c for c in history if c["id"] == conversion_id), None)
    if conversion is None:
        abort(404, description="Conversia nu a fost găsită")
    
    data = request.get_json()
    unit_type = data.get('type', conversion.get('type'))
    from_unit = data.get('from', conversion['original']['unit'])
    to_unit = data.get('to', conversion['converted']['unit'])
    value = data.get('value', conversion['original']['value'])
    #Recalculeaza valoarea convertita
    converted_value = value * (conversions[unit_type][to_unit] / conversions[unit_type][from_unit])
    conversion.update({
        "original": {"value": value, "unit": from_unit},
        "converted": {"value": converted_value, "unit": to_unit}
    })
    return jsonify(conversion)


# PATCH Actualizare parțială 
@app.route('/convert/<int:conversion_id>', methods=['PATCH'])
def partial_update_conversion(conversion_id):
    if not request.is_json:
        abort(415, description="Content-Type must be application/json")
        
    conversion = next((c for c in history if c["id"] == conversion_id), None)
    if conversion is None:
        abort(404, description="Conversia nu a fost găsită")
    
    data = request.get_json()
    
    # Determină unit_type din conversia originală
    unit_type = None
    for key in conversions:
        if conversion['original']['unit'] in conversions[key]:
            unit_type = key
            break
    
    if unit_type is None:
        abort(400, description="Tipul de conversie nu poate fi determinat")
    
    # Folosește valorile existente ca fallback
    from_unit = data.get('from', conversion['original']['unit'])
    to_unit = data.get('to', conversion['converted']['unit'])
    value = data.get('value', conversion['original']['value'])
    
    # Verifică unitățile în dicționar
    if from_unit not in conversions[unit_type] or to_unit not in conversions[unit_type]:
        abort(400, description="Unitate invalidă pentru tipul de conversie")
    
    # Recalculează valoarea convertită cu rotunjire
    converted_value = round(value * (conversions[unit_type][to_unit] / conversions[unit_type][from_unit]), 6)
    
    # Actualizează doar câmpurile furnizate
    if 'value' in data:
        conversion['original']['value'] = value
    if 'from' in data:
        conversion['original']['unit'] = from_unit
    if 'to' in data:
        conversion['converted']['unit'] = to_unit
    
    conversion['converted']['value'] = converted_value
    
    return jsonify(conversion)

# DELETE Ștergerea unei conversii
@app.route('/convert/<int:conversion_id>', methods=['DELETE'])
def delete_conversion(conversion_id):
    global history
    history = [c for c in history if c["id"] != conversion_id]
    return jsonify({"message": f"Conversia cu ID {conversion_id} a fost stearsa"})

# HEAD pentru a verifica existența unei conversii
@app.route('/convert/<int:conversion_id>', methods=['HEAD'])
def head_conversion(conversion_id):
    conversion = next((c for c in history if c["id"] == conversion_id), None)
    if conversion is None:
        abort(404, description="Conversia nu a fost găsită")
    return '', 200

# OPTIONS pentru a vedea metodele disponibile
@app.route('/convert', methods=['OPTIONS'])
def options_convert():
    return '', 200, {
        'Allow': 'GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS',
        'Access-Control-Allow-Methods': 'GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type'
    }

if __name__ == '__main__':
    app.run(debug=True)