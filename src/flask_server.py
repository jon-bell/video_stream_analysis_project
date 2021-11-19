from flask import render_template, Flask, send_from_directory, jsonify
from flask.wrappers import Response
import os

app = Flask(__name__)

@app.after_request
def add_header(response) -> Response:
    response.headers['X-UA-Compatible'] = 'IE=Edge,chrome=1'
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route("/get_params")
def get_params() -> Response:
    """
    Returns params stored as environment variables
    """
    params = ["CPU", "MEMORY", "IMAGE_SIZE", "FPS", "VIDEO_TYPE", "ID"]
    result_dict = {}
    for param in params:
        if param in os.environ:
            result_dict[param] = os.environ[param]
    return jsonify(result_dict)

@app.route('/')
def index() -> str:
    return render_template('index.html')

@app.route("/ping")
def ping() -> Response:
    return jsonify({"message":"HELLO!"})


@app.route('/video/<string:file_name>')
def stream(file_name) -> Response:
    video_dir = f'{os.getcwd()}/video'
    return send_from_directory(directory=video_dir, path=file_name)


if __name__ == '__main__':
    app.run('0.0.0.0', port=5000)