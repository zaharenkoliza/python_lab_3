FROM python:3.12.6-slim
RUN pip install --no-cache-dir aiohttp==3.10.5
COPY loadgen.py /loadgen.py
ENTRYPOINT ["python", "/loadgen.py"]
