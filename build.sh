#!/bin/bash
cd movie_network
python manage.py collectstatic --noinput
python manage.py migrate
