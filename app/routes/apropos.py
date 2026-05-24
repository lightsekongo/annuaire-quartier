"""
Route de la page "À propos".
"""
from flask import Blueprint, render_template

apropos_bp = Blueprint('apropos_bp', __name__)


@apropos_bp.route('/a-propos')
def index():
    return render_template('apropos.html')