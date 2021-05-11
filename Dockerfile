# Our base container is python, frozen at v3.9.5 for the time being.
FROM python:3.9.5-buster

# Set the working directory, which is the current directory inside the container
WORKDIR /app

# Copy all our source code into the container. Bind mount makes it not work.
COPY . .

# Create the database file, if it doesn't exist.
RUN mkdir /app/db
RUN test -f /app/db/games.json || echo "[]" > /app/db/games.json

# Get dependencies, maybe use poetry export in a git action, and install from requirements.txt?????
RUN python -m pip install poetry --user
RUN python -m poetry install

# Start python using poetry (using python) 
CMD ["python3", "-m", "poetry", "run", "python3", "src/yuzu-compat-bot.py"]