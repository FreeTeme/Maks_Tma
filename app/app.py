from flask import Flask, jsonify, request
from importlib import import_module
import logging
from config import PARSERS

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

def load_parsers():
    parsers = []
    for parser_path in PARSERS:
        try:
            module_path, class_name = parser_path.rsplit('.', 1)
            module = import_module(module_path)
            parser_class = getattr(module, class_name)
            parsers.append(parser_class())
        except Exception as e:
            app.logger.error(f"Error loading parser {parser_path}: {str(e)}")
    return parsers

parsers = load_parsers()

@app.route('/staking-info', methods=['GET'])
def get_staking_info():
    coin = request.args.get('coin')
    if not coin:
        return jsonify({'error': 'Missing coin parameter'}), 400
    
    results = []
    for parser in parsers:
        try:
            info = parser.get_staking_info(coin)
            if info:
                results.append(info)
        except Exception as e:
            app.logger.error(f"Error processing {parser.__class__.__name__}: {str(e)}")
    
    return jsonify({
        'coin': coin.upper(),
        'exchanges': results
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)