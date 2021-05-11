FROM python:3.9.5-buster
RUN python -m pip install poetry --user
WORKDIR /app
COPY . .
RUN poetry install
CMD ["python3", "src/yuzu-compat-bot.py"]