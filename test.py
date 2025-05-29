from flask import Flask, jsonify, request, abort
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from collections import OrderedDict
import requests
import os

# Initialize Flask application
app = Flask(__name__)
CORS(app)

# Configure database (SQLite local)
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'conversions.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Conversion rates dictionary
conversions = {
    "mass": {
        "kg": 1,
        "g": 1000,
        "mg": 1000000,
        "pound": 2.20462,
        "ounce": 35.274,
        "ton": 0.001,
        "stone": 0.157473
    },
    "length": {
        "km": 1,
        "m": 1000,
        "cm": 100000,
        "mm": 1000000,
        "mile": 0.621371,
        "yard": 1093.61,
        "foot": 3280.84,
        "inch": 39370.1,
        "nautical_mile": 0.539957
    },
    "energy": {
        "kW": 1,
        "W": 1000,
        "MW": 0.001,
        "J": 3600000,
        "Wh": 1000,
        "kcal": 859.845,
        "cal": 859845.2279,
        "BTU": 3412.14
    },
    "temperature": {
        "celsius": 1,
        "kelvin": 274.15,
        "fahrenheit": "special"
    },
    "area": {
        "sqm": 1,
        "sqkm": 0.000001,
        "sqft": 10.7639,
        "sqinch": 1550,
        "acre": 0.000247105,
        "hectare": 0.0001
    },
    "volume": {
        "liter": 1,
        "ml": 1000,
        "gallon": 0.264172,
        "cubic_meter": 0.001,
        "cubic_cm": 1000,
        "pint": 2.11338
    },
    "speed": {
        "kmh": 1,
        "mph": 0.621371,
        "ms": 0.277778,
        "knot": 0.539957
    },
    "time": {
        "second": 1,
        "minute": 1/60,
        "hour": 1/3600,
        "day": 1/86400,
        "week": 1/604800,
        "year": 1/31536000
    }
}

# Database model for a conversion record
class Conversion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    unit_type = db.Column(db.String(50), nullable=False)
    from_unit = db.Column(db.String(20), nullable=False)
    to_unit = db.Column(db.String(20), nullable=False)
    original_value = db.Column(db.Float, nullable=False)
    converted_value = db.Column(db.Float, nullable=False)

    def to_dict(self):
        return OrderedDict([
            ("id", self.id),
            ("original", {"value": self.original_value, "unit": self.from_unit}),
            ("converted", {"value": self.converted_value, "unit": self.to_unit})
        ])

# Home route
@app.route('/')
def home():
    return "Bun venit la API-ul de conversii de unități!"

# Helper to calculate conversion values
def calculate(unit_type, from_u, to_u, val):
    return round(val * (conversions[unit_type][to_u] / conversions[unit_type][from_u]), 6)

# GET all conversions
@app.route('/convert', methods=['GET'])
def get_conversions():
    all_convs = Conversion.query.all()
    return jsonify([c.to_dict() for c in all_convs])

# GET a conversion by ID
@app.route('/convert/<int:conversion_id>', methods=['GET'])
def get_conversion_by_id(conversion_id):
    conv = Conversion.query.get(conversion_id)
    if not conv:
        abort(404, description="Conversia nu a fost găsită")
    return jsonify(conv.to_dict())

# POST a new conversion
@app.route('/convert', methods=['POST'])
def add_conversion():
    if not request.is_json:
        abort(415, description="Content-Type must be application/json")
    data = request.get_json()
    unit_type = data.get('type')
    from_u = data.get('from')
    to_u = data.get('to')
    val = data.get('value')
    if not all([unit_type, from_u, to_u]) or val is None:
        abort(400, description="Lipsesc parametrii necesari: type, from, to, value")
    if unit_type not in conversions or from_u not in conversions[unit_type] or to_u not in conversions[unit_type]:
        abort(400, description="Tip de unitate sau unități invalide")
    result = calculate(unit_type, from_u, to_u, val)
    conv = Conversion(unit_type=unit_type, from_unit=from_u, to_unit=to_u,
                      original_value=val, converted_value=result)
    db.session.add(conv)
    db.session.commit()
    return jsonify(conv.to_dict()), 201

# PUT update entire conversion
@app.route('/convert/<int:conversion_id>', methods=['PUT'])
def update_conversion(conversion_id):
    if not request.is_json:
        abort(415, description="Content-Type must be application/json")
    conv = Conversion.query.get(conversion_id)
    if not conv:
        abort(404, description="Conversia nu a fost găsită")
    data = request.get_json()
    unit_type = data.get('type', conv.unit_type)
    from_u = data.get('from', conv.from_unit)
    to_u = data.get('to', conv.to_unit)
    val = data.get('value', conv.original_value)
    if unit_type not in conversions or from_u not in conversions[unit_type] or to_u not in conversions[unit_type]:
        abort(400, description="Unități invalide pentru tipul specificat")
    conv.unit_type = unit_type
    conv.from_unit = from_u
    conv.to_unit = to_u
    conv.original_value = val
    conv.converted_value = calculate(unit_type, from_u, to_u, val)
    db.session.commit()
    return jsonify(conv.to_dict())

# PATCH partial update
@app.route('/convert/<int:conversion_id>', methods=['PATCH'])
def partial_update_conversion(conversion_id):
    if not request.is_json:
        abort(415, description="Content-Type must be application/json")
    conv = Conversion.query.get(conversion_id)
    if not conv:
        abort(404, description="Conversia nu a fost găsită")
    data = request.get_json()
    unit_type = conv.unit_type
    from_u = data.get('from', conv.from_unit)
    to_u = data.get('to', conv.to_unit)
    val = data.get('value', conv.original_value)
    if unit_type not in conversions or from_u not in conversions[unit_type] or to_u not in conversions[unit_type]:
        abort(400, description="Unitate invalidă pentru tipul de conversie")
    conv.from_unit = from_u
    conv.to_unit = to_u
    conv.original_value = val
    conv.converted_value = calculate(unit_type, from_u, to_u, val)
    db.session.commit()
    return jsonify(conv.to_dict())

# DELETE a conversion
@app.route('/convert/<int:conversion_id>', methods=['DELETE'])
def delete_conversion(conversion_id):
    conv = Conversion.query.get(conversion_id)
    if not conv:
        abort(404, description="Conversia nu a fost găsită")
    db.session.delete(conv)
    db.session.commit()
    return jsonify({"message": f"Conversia cu ID {conversion_id} a fost ștearsă"})

# HEAD check existence
@app.route('/convert/<int:conversion_id>', methods=['HEAD'])
def head_conversion(conversion_id):
    conv = Conversion.query.get(conversion_id)
    if not conv:
        abort(404, description="Conversia nu a fost găsită")
    return '', 200

# OPTIONS allowed methods
@app.route('/convert', methods=['OPTIONS'])
def options_convert():
    return '', 200, {
        'Allow': 'GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS',
        'Access-Control-Allow-Methods': 'GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type'
    }

@app.route('/cities/<country_code>', methods=['GET'])
def get_top_cities(country_code):
    url = f"https://countries-cities.p.rapidapi.com/location/country/{country_code}/city/list"
    querystring = {
        "page": "1",
        "per_page": "10",
        "format": "json",
        "population": "1000"
    }

    headers = {
        "x-rapidapi-key": "bbb74778a0msh68508213e2e802ep10a33djsnc2d1ba2ee9e7",
        "x-rapidapi-host": "countries-cities.p.rapidapi.com"
    }

    try:
        response = requests.get(url, headers=headers, params=querystring, timeout=10)
        response.raise_for_status()
        data = response.json()

        # Pune Cahul primul dacă este Moldova
        if country_code.upper() == "MD":
            cities = data.get("cities", [])
            if not any(city.get("name", "").lower() == "cahul" for city in cities):
                cities.insert(0, {
                    "name": "Cahul",
                    "latitude": 45.9026,
                    "longitude": 28.1943
                })
            data["cities"] = cities

        return jsonify(data)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/energy', methods=['GET'])
def get_energy_data():
    lat = 47.16  # Iași
    lon = 27.58
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}&current=temperature_2m,windspeed_10m"
    )
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        current = data.get("current", {})

        return jsonify({
            "temperature_C": current.get("temperature_2m"),
            "windspeed_m_s": current.get("windspeed_10m")
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500    


if __name__ == '__main__':
    # Create database tables within application context
    with app.app_context():
        db.create_all()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
