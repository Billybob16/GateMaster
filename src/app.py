# ================================================
# BLUE RTU5025 PAGES - ALL LINKS NOW WORK
# ================================================
@app.route('/relay')
def relay_page():
    return render_template('relay.html')

@app.route('/users')
def users_page():
    return render_template('users.html')

@app.route('/advanced')
def advanced_page():
    return render_template('advanced.html')

@app.route('/logs')
def logs_page():
    return render_template('logs.html')

# Fallback for old RTU routes (keeps everything working)
@app.route('/rtu/<path:path>')
def old_rtu_fallback(path):
    return redirect(url_for('dashboard_page'))