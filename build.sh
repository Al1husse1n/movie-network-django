#!/bin/bash
pip install -r requirements.txt
cd movie_network
python manage.py collectstatic --noinput
python manage.py migrate
