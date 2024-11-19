import http.client

conn = http.client.HTTPSConnection("apis.aisensy.com")

headers = {
    'Accept': "application/json",
    'X-AiSensy-Partner-API-Key': ""
}

conn.request("GET", "/project-apis/v1/project/{project_id}/messages/{message_id}", headers=headers)

res = conn.getresponse()
data = res.read()

print(data.decode("utf-8"))