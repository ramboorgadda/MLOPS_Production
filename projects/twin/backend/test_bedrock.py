import boto3, time

client = boto3.client('bedrock-runtime', region_name='us-east-1')
models = [
    'us.amazon.nova-micro-v1:0',
    'us.anthropic.claude-haiku-4-5-20251001-v1:0',
    'mistral.ministral-3-14b-instruct',
    'google.gemma-3-12b-it',
    'deepseek.v3.2',
    'zai.glm-4.7-flash',
]

for model_id in models:
    try:
        r = client.converse(
            modelId=model_id,
            messages=[{'role': 'user', 'content': [{'text': 'hi'}]}]
        )
        text = r['output']['message']['content'][0]['text'][:60]
        print(f'OK: {model_id} -> {text}')
    except Exception as e:
        print(f'FAIL: {model_id} -> {type(e).__name__}: {str(e)[:80]}')
    time.sleep(3)
