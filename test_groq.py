import os
client = groq.Groq(api_key=os.environ.get('GROQ_API_KEY'))
try:
    res = client.chat.completions.create(
        model='llama-3.1-8b-instant',
        messages=[{'role':'system', 'content':'Return JSON only. {"skill": "yes"}'}, {'role':'user', 'content':'test JSON'}],
        response_format={'type':'json_object'}
    )
    print("SUCCESS")
except Exception as e:
    print("ERROR MSG:", str(e))
