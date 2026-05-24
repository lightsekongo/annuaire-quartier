from flask import Flask
from datetime import date
from .models import close_db
from .routes.menages import menages_bp
from .routes.membres import membres_bp
from .routes.dashboard import dashboard_bp
from .routes.comparer import comparer_bp
from .routes.territoires import territoires_bp
from .routes.apropos import apropos_bp
from .routes.fiche import fiche_bp
from .routes.explorer import explorer_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')

    app.teardown_appcontext(close_db)

    app.register_blueprint(menages_bp)
    app.register_blueprint(fiche_bp)
    app.register_blueprint(explorer_bp)
    app.register_blueprint(membres_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(comparer_bp)
    app.register_blueprint(territoires_bp)
    app.register_blueprint(apropos_bp)

    # Injecte la date du jour dans tous les templates
    @app.context_processor
    def inject_now():
        return {'now': date.today()}

    return app