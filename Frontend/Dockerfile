FROM python:3.9.13

# Pull the base docker image of python with tag 3.9.13

WORKDIR /app
# Change the working dir inside the container - cd /app

# COPY .env main.py menu.py service.py config.yaml requirements.txt ./
# COPY .env main.py menu.py config.yaml requirements.txt ./

COPY .env Welcome.py auth.py config.yaml requirements.txt ./
COPY pages /app/pages
# COPY UIenv /app/UIenv
# ########Copy main.py as source cod and req.txt as dependency

RUN pip install -r requirements.txt
# Install the dependency

### Container Env same as local at this point

EXPOSE 8501

CMD ["streamlit", "run", "Welcome.py", "--server.port", "8501"]
