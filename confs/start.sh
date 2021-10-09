service nginx start &
gunicorn --conf /app/config/gunicorn_conf.py --bind 0.0.0.0:8080 main:app