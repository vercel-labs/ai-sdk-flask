[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2Fvercel-labs%2Fai-sdk-flask&project-name=ai-sdk-flask&repository-name=ai-sdk-flask&demo-title=AI%20SDK%20and%20Flask%20API&demo-description=Use%20Flask%20API%20and%20AI%20SDK%20on%20Vercel%20with%20Serverless%20Functions%20using%20the%20Python%20Runtime.&demo-url=https%3A%2F%2Fai-sdk-preview-flask.vercel.app&demo-image=https%3A%2F%2Fassets.vercel.com%2Fimage%2Fupload%2Fv1669994600%2Frandom%2Fpython.png)

# Flask + Vercel

This example shows how to use Flask and AI SDK on Vercel with Serverless Functions using the [Python Runtime](https://vercel.com/docs/concepts/functions/serverless-functions/runtimes/python).

## Demo

https://ai-sdk-preview-flask.vercel.app/api/generate?prompt="hey!"

## How it Works

This example uses the Web Server Gateway Interface (WSGI) with Flask to handle requests on Vercel with Serverless Functions.

## Running Locally

```bash
npm i -g vercel
python -m venv .venv
source .venv/bin/activate
uv sync  # or alternatively pip install flask gunicorn
gunicorn main:app
```

Your Flask application is now available at `http://localhost:3000`.
