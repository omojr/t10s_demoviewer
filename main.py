import operator
import os
import sqlite3

from flask import Flask, render_template, send_file, url_for

from config import config, BASE_DIR
from db import get_conn


app = Flask(__name__)


@app.route('/')
def main():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute('select demo_id, filepath, server, map, datetime from demos;')
    demos = cursor.fetchall()
    conn.close()
    demos.sort(key=operator.itemgetter('datetime'), reverse=True)
    for demo in demos:
        path = demo.pop('filepath')
        size = os.stat(path).st_size/1024**2
        demo['size'] = f'{round(size, 1)} MB'
    return render_template('index.html', demos=demos)


@app.route('/get/<demo_id>')
def download_demo(demo_id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute('select filepath from demos where demo_id=?', (demo_id,))
    result = cursor.fetchone()
    if not result:
        return "<h2>Demo with such id doesn't exist</h2>", 404
    filepath = result['filepath']
    filename = filepath.rsplit('/', 1)[1]
    conn.close()
    return send_file(filepath, as_attachment=True, attachment_filename=filename)


@app.context_processor
def override_url_for():
    return dict(url_for=dated_url_for)


def dated_url_for(endpoint, **values):
    if endpoint == 'static':
        filename = values.get('filename', None)
        if filename:
            file_path = os.path.join(app.root_path, endpoint, filename)
            values['q'] = int(os.stat(file_path).st_mtime)
    return url_for(endpoint, **values)


if __name__ == '__main__':
    app.run()
