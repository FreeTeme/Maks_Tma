from flask import Blueprint, jsonify, request
from importlib import import_module
import logging
from app.config import PARSERS

staking_bp = Blueprint('staking', __name__)

logging.basicConfig(level=logging.DEBUG)

def load_parsers():
    parsers = []
    for parser_path in PARSERS:
        try:
            module_path, class_name = parser_path.rsplit('.', 1)
            module = import_module(module_path)
            parser_class = getattr(module, class_name)
            parsers.append(parser_class())
        except Exception as e:
            logging.error(f"Error loading parser {parser_path}: {str(e)}")
    return parsers

parsers = load_parsers()

def has_valid_staking_data(info: dict) -> bool:
    """Проверяет, содержит ли информация о стейкинге действительные данные"""
    return bool(info.get('holdPosList') or info.get('lockPosList'))

@staking_bp.route('/staking-info', methods=['GET'])
def get_staking_info():
    coin = request.args.get('coin')
    if not coin:
        return jsonify({'error': 'Missing coin parameter'}), 400
    
    results = []
    for parser in parsers:
        try:
            info = parser.get_staking_info(coin)
            if info and has_valid_staking_data(info):
                results.append(info)
        except Exception as e:
            logging.error(f"Error processing {parser.__class__.__name__}: {str(e)}")
    
    return jsonify({
        'coin': coin.upper(),
        'exchanges': results
    })