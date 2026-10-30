# Cognimap

## Local services

The API and Python LangGraph runtime use Postgres. The API produces learning jobs directly to BullMQ in Redis, and a separate Python BullMQ worker consumes them. BullMQ queue data is persisted with Redis AOF and `noeviction`.

Start the stack with `docker compose up --build`. Redis is configured with AOF persistence and `noeviction` because it stores queue state as well as cache data.

The default agent uses Gemini. To select a Hugging Face model, install the optional provider with `pip install 'agent[huggingface]'`.

# Architecture

<img width="613" height="275" alt="image" src="https://github.com/user-attachments/assets/579f227d-1ec6-447b-9406-622c678220cb" />



# Flow Diagram



<img width="862" height="529" alt="Screenshot 2026-08-02 at 4 04 16 PM" src="https://github.com/user-attachments/assets/1b5c04e0-ee06-4095-a6c6-4d672a1ae4d1" />





# UI

<img width="1438" height="822" alt="Screenshot 2026-08-02 at 4 17 39 PM" src="https://github.com/user-attachments/assets/a4db53a1-bc0a-4a54-9f9d-05f2ee30695d" />


<img width="1440" height="812" alt="Screenshot 2026-08-02 at 4 18 51 PM" src="https://github.com/user-attachments/assets/cfd2f163-9ca9-4714-a652-8a4528c7c261" />


<img width="1440" height="815" alt="Screenshot 2026-08-02 at 3 37 51 PM" src="https://github.com/user-attachments/assets/ddff67a1-d7a4-47f6-b477-7fd18752d931" />

