import os
import sqlite3
from datetime import datetime

from flask import (
    Flask,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

DB_PATH = os.environ.get("TAVERN_DB", "tavern.db")


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret")
    app.config["ADMIN_USERNAME"] = os.environ.get("ADMIN_USERNAME", "admin")
    admin_password = os.environ.get("ADMIN_PASSWORD", "changeme")
    app.config["ADMIN_PASSWORD_HASH"] = generate_password_hash(admin_password)

    def get_db():
        if "db" not in g:
            g.db = sqlite3.connect(DB_PATH)
            g.db.row_factory = sqlite3.Row
        return g.db

    def init_db():
        db = get_db()
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS beers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                style TEXT NOT NULL,
                abv REAL,
                description TEXT,
                tavern TEXT,
                rating INTEGER,
                image_url TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        db.commit()

    @app.before_request
    def before_request():
        init_db()

    @app.teardown_appcontext
    def close_db(exception):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    def is_admin():
        return session.get("is_admin") is True

    @app.route("/")
    def index():
        db = get_db()
        beers = db.execute(
            "SELECT * FROM beers ORDER BY datetime(created_at) DESC"
        ).fetchall()
        return render_template("index.html", beers=beers)

    @app.route("/beer/<int:beer_id>")
    def beer_detail(beer_id):
        db = get_db()
        beer = db.execute("SELECT * FROM beers WHERE id = ?", (beer_id,)).fetchone()
        if beer is None:
            return render_template("404.html"), 404
        return render_template("beer_detail.html", beer=beer)

    @app.route("/admin/login", methods=["GET", "POST"])
    def admin_login():
        if request.method == "POST":
            username = request.form.get("username", "")
            password = request.form.get("password", "")
            if username != app.config["ADMIN_USERNAME"]:
                flash("Wrong credentials.", "error")
            elif not check_password_hash(app.config["ADMIN_PASSWORD_HASH"], password):
                flash("Wrong credentials.", "error")
            else:
                session["is_admin"] = True
                return redirect(url_for("admin_dashboard"))
        return render_template("admin/login.html")

    @app.route("/admin/logout")
    def admin_logout():
        session.clear()
        return redirect(url_for("index"))

    @app.route("/admin", methods=["GET", "POST"])
    def admin_dashboard():
        if not is_admin():
            return redirect(url_for("admin_login"))

        db = get_db()
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            style = request.form.get("style", "").strip()
            abv = request.form.get("abv", "").strip()
            description = request.form.get("description", "").strip()
            tavern = request.form.get("tavern", "").strip()
            rating = request.form.get("rating", "").strip()
            image_url = request.form.get("image_url", "").strip()

            if not name or not style:
                flash("Name and style are required.", "error")
            else:
                db.execute(
                    """
                    INSERT INTO beers
                        (name, style, abv, description, tavern, rating, image_url, created_at)
                    VALUES
                        (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        name,
                        style,
                        float(abv) if abv else None,
                        description or None,
                        tavern or None,
                        int(rating) if rating else None,
                        image_url or None,
                        datetime.utcnow().isoformat(),
                    ),
                )
                db.commit()
                flash("Beer added to the cellar!", "success")
                return redirect(url_for("admin_dashboard"))

        beers = db.execute(
            "SELECT * FROM beers ORDER BY datetime(created_at) DESC"
        ).fetchall()
        return render_template("admin/dashboard.html", beers=beers)

    @app.route("/admin/beers/<int:beer_id>/edit", methods=["GET", "POST"])
    def admin_edit_beer(beer_id):
        if not is_admin():
            return redirect(url_for("admin_login"))

        db = get_db()
        beer = db.execute("SELECT * FROM beers WHERE id = ?", (beer_id,)).fetchone()
        if beer is None:
            return render_template("404.html"), 404

        if request.method == "POST":
            name = request.form.get("name", "").strip()
            style = request.form.get("style", "").strip()
            abv = request.form.get("abv", "").strip()
            description = request.form.get("description", "").strip()
            tavern = request.form.get("tavern", "").strip()
            rating = request.form.get("rating", "").strip()
            image_url = request.form.get("image_url", "").strip()

            if not name or not style:
                flash("Name and style are required.", "error")
            else:
                db.execute(
                    """
                    UPDATE beers
                    SET name = ?, style = ?, abv = ?, description = ?, tavern = ?, rating = ?, image_url = ?
                    WHERE id = ?
                    """,
                    (
                        name,
                        style,
                        float(abv) if abv else None,
                        description or None,
                        tavern or None,
                        int(rating) if rating else None,
                        image_url or None,
                        beer_id,
                    ),
                )
                db.commit()
                flash("Beer updated.", "success")
                return redirect(url_for("admin_dashboard"))

        return render_template("admin/edit.html", beer=beer)

    @app.route("/admin/beers/<int:beer_id>/delete", methods=["POST"])
    def admin_delete_beer(beer_id):
        if not is_admin():
            return redirect(url_for("admin_login"))

        db = get_db()
        db.execute("DELETE FROM beers WHERE id = ?", (beer_id,))
        db.commit()
        flash("Beer banished from the taps.", "success")
        return redirect(url_for("admin_dashboard"))

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
